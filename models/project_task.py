# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, timedelta

import pytz

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _get_param(env, key, default):
    val = env["ir.config_parameter"].sudo().get_param(key)
    return val if val else default


def _work_start(env):
    return int(_get_param(env, "task_auto_timer.work_start", 9))

def _work_end(env):
    return int(_get_param(env, "task_auto_timer.work_end", 19))

def _work_days(env):
    raw = _get_param(env, "task_auto_timer.work_days", "0,1,2,3,4,5")
    try:
        return {int(d.strip()) for d in raw.split(",") if d.strip()}
    except Exception:
        return {0, 1, 2, 3, 4, 5}

def _stage(env, key, default):
    return (_get_param(env, f"task_auto_timer.{key}", default) or default).lower().strip()

def _cto_job(env):
    return _get_param(env, "task_auto_timer.cto_job_title", "CTO") or "CTO"


def work_seconds_between(start_utc, end_utc, tz_name, work_start, work_end, work_days):
    try:
        tz = pytz.timezone(tz_name or "UTC")
    except Exception:
        tz = pytz.UTC
    if start_utc.tzinfo is None:
        start_utc = pytz.UTC.localize(start_utc)
    if end_utc.tzinfo is None:
        end_utc = pytz.UTC.localize(end_utc)
    if start_utc >= end_utc:
        return 0.0
    total = 0.0
    cur = start_utc
    while cur < end_utc:
        local_cur = cur.astimezone(tz)
        day_start = local_cur.replace(hour=work_start, minute=0, second=0, microsecond=0)
        day_end   = local_cur.replace(hour=work_end,   minute=0, second=0, microsecond=0)
        next_day  = (local_cur + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        if local_cur.weekday() in work_days:
            seg_start = max(cur.astimezone(tz), day_start)
            seg_end   = min(end_utc.astimezone(tz), day_end)
            if seg_start < seg_end:
                total += (seg_end - seg_start).total_seconds()
        cur = tz.localize(next_day.replace(tzinfo=None)).astimezone(pytz.UTC)
    return max(0.0, total)


class ProjectTask(models.Model):
    _inherit = "project.task"

    timer_start            = fields.Datetime(string="Timer Start", readonly=True)
    timer_running          = fields.Boolean(string="Timer Running", default=False)
    timer_paused           = fields.Boolean(string="Timer Paused", default=False)
    timer_accumulated      = fields.Float(string="Accumulated (soat)", default=0.0)
    total_duration         = fields.Float(string="Oxirgi sessiya (soat)", default=0.0)
    timer_sessions         = fields.Text(string="Timer Sessions", default="[]")
    awaiting_test_decision = fields.Boolean(string="Awaiting Test Decision", default=False)

    test_timer_start       = fields.Datetime(string="Test Timer Start", readonly=True)
    test_timer_running     = fields.Boolean(string="Test Timer Running", default=False)
    test_timer_accumulated = fields.Float(string="Test Accumulated (soat)", default=0.0)
    test_labor_cost        = fields.Float(string="Test Labor Cost", default=0.0, digits=(10, 2))
    test_timer_sessions    = fields.Text(string="Test Timer Sessions", default="[]")
    cto_hourly_wage        = fields.Float(string="CTO Hourly Wage", compute="_compute_cto_wage", store=False)

    # ── Helpers ───────────────────────────────────────────────
    def _get_sessions(self):
        try:
            return json.loads(self.timer_sessions or "[]")
        except Exception:
            return []

    def _get_test_sessions(self):
        try:
            return json.loads(self.test_timer_sessions or "[]")
        except Exception:
            return []

    def _compute_cto_wage(self):
        for task in self:
            task.cto_hourly_wage = task._get_cto_hourly_wage()

    def _get_cto_hourly_wage(self):
        try:
            job_title = _cto_job(self.env)
            cto_emp = self.env["hr.employee"].search(
                [("job_id.name", "ilike", job_title), ("active", "=", True)], limit=1
            )
            if not cto_emp:
                _logger.warning("CTO employee topilmadi! (job_title=%s)", job_title)
                return 0.0
            for f in ("hourly_cost", "timesheet_cost", "hourly_wage"):
                wage = getattr(cto_emp, f, 0.0) or 0.0
                if wage > 0:
                    _logger.info("CTO: %s, field: %s, wage: %.2f", cto_emp.name, f, wage)
                    return float(wage)
            _logger.warning("CTO %s da soatlik maosh topilmadi", cto_emp.name)
        except Exception as e:
            _logger.warning("CTO wage xatosi: %s", e)
        return 0.0

    def _find_stage(self, keyword):
        if self.project_id:
            stage = self.env["project.task.type"].search(
                [("name", "ilike", keyword), ("project_ids", "in", self.project_id.ids)], limit=1
            )
            if stage:
                return stage
        return self.env["project.task.type"].search([("name", "ilike", keyword)], limit=1)

    def _stage_name(self, stage_id):
        stage = self.env["project.task.type"].browse(stage_id)
        return (stage.name or "").lower()

    def _elapsed_work_hours(self):
        if not self.timer_start:
            return 0.0
        tz_name   = self.env.user.tz or "UTC"
        start     = self.timer_start
        if start.tzinfo is None:
            start = pytz.UTC.localize(start)
        return work_seconds_between(
            start, datetime.now(pytz.UTC), tz_name,
            _work_start(self.env), _work_end(self.env), _work_days(self.env)
        ) / 3600.0

    def _elapsed_test_work_hours(self):
        if not self.test_timer_start:
            return 0.0
        start = self.test_timer_start
        if isinstance(start, str):
            start = datetime.fromisoformat(start.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = pytz.UTC.localize(start)
        return (datetime.now(pytz.UTC) - start).total_seconds() / 3600.0

    def _save_session(self, stage_label, reset_total=False):
        elapsed  = self._elapsed_work_hours() if self.timer_running else 0.0
        total    = self.timer_accumulated + elapsed
        sessions = self._get_sessions()
        sessions.append({
            "stage"     : stage_label,
            "duration"  : round(total, 6),
            "stopped_at": datetime.now().isoformat(),
        })
        return {
            "timer_sessions"   : json.dumps(sessions),
            "total_duration"   : 0.0 if reset_total else round(total, 6),
            "timer_accumulated": 0.0,
            "timer_start"      : False,
            "timer_running"    : False,
            "timer_paused"     : False,
        }

    # ── Stage o'zgarganda taymer logikasi ─────────────────────
    def write(self, vals):
        if "stage_id" not in vals:
            return super().write(vals)

        name = self._stage_name(vals["stage_id"])

        # Sozlamalardan stage nomlarini olish
        s_progress   = _stage(self.env, "stage_in_progress", "in progress")
        s_waiting    = _stage(self.env, "stage_waiting",     "waiting")
        s_test       = _stage(self.env, "stage_test",        "test")
        s_todo       = _stage(self.env, "stage_todo",        "to do")
        s_validation = _stage(self.env, "stage_validation",  "validation")
        s_done       = _stage(self.env, "stage_done",        "done")

        for task in self:
            extra = {}

            if s_progress in name:
                if task.timer_paused:
                    extra = {
                        "timer_start": fields.Datetime.now(),
                        "timer_running": True,
                        "timer_paused": False,
                        "awaiting_test_decision": False,
                    }
                elif not task.timer_running:
                    extra = {
                        "timer_start": fields.Datetime.now(),
                        "timer_running": True,
                        "timer_paused": False,
                        "timer_accumulated": 0.0,
                        "awaiting_test_decision": False,
                    }

            elif s_waiting in name:
                if task.timer_running:
                    elapsed = task._elapsed_work_hours()
                    extra = {
                        "timer_accumulated": task.timer_accumulated + elapsed,
                        "timer_start": False,
                        "timer_running": False,
                        "timer_paused": True,
                    }

            elif s_test in name:
                stop_vals = {}
                if task.timer_running or task.timer_paused:
                    stop_vals = task._save_session(s_test.title(), reset_total=False)
                extra = {
                    **stop_vals,
                    "awaiting_test_decision": True,
                    "test_timer_start": False,
                    "test_timer_running": False,
                    "test_timer_accumulated": 0.0,
                    "test_labor_cost": 0.0,
                }
                # CTO ni assigneesga qo'shish
                job_title = _cto_job(self.env)
                cto_emp = self.env["hr.employee"].search(
                    [("job_id.name", "ilike", job_title), ("active", "=", True)], limit=1
                )
                if cto_emp and cto_emp.user_id:
                    current = task.user_ids.ids or []
                    if cto_emp.user_id.id not in current:
                        current = current + [cto_emp.user_id.id]
                    extra["user_ids"] = [(6, 0, current)]

            elif s_todo in name or name.strip() == "todo":
                extra = {}
                if task.timer_running or task.timer_paused:
                    extra = task._save_session(s_todo.title() + " (qaytarildi)", reset_total=True)
                extra.update({
                    "awaiting_test_decision": False,
                    "total_duration": 0.0,
                    "test_timer_running": False,
                    "test_timer_start": False,
                    "test_timer_accumulated": 0.0,
                    "test_labor_cost": 0.0,
                })

            elif s_validation in name:
                extra = {"awaiting_test_decision": False}
                if task.timer_running or task.timer_paused:
                    extra.update(task._save_session(s_validation.title(), reset_total=False))

            elif s_done in name:
                extra = {"awaiting_test_decision": False}
                if task.timer_running or task.timer_paused:
                    extra.update(task._save_session(s_done.title(), reset_total=False))

            else:
                if task.timer_running or task.timer_paused:
                    extra = task._save_session(name.title(), reset_total=False)

            super(ProjectTask, task).write({**vals, **extra})

        return True

    # ── Tugma actionlar ───────────────────────────────────────
    def action_test_confirm(self):
        self.ensure_one()
        keyword = _get_param(self.env, "task_auto_timer.stage_validation", "Validation")
        stage = self._find_stage(keyword)
        if not stage:
            raise models.ValidationError(
                f"'{keyword}' nomli stage topilmadi!\n"
                "Iltimos Project Settings da ushbu stage mavjudligini tekshiring."
            )
        super(ProjectTask, self).write({"stage_id": stage.id, "awaiting_test_decision": False})

    def action_test_reject(self):
        self.ensure_one()
        keyword = _get_param(self.env, "task_auto_timer.stage_todo", "To Do")
        stage = self._find_stage(keyword)
        if not stage:
            raise models.ValidationError(
                f"'{keyword}' nomli stage topilmadi!\n"
                "Iltimos Project Settings da ushbu stage mavjudligini tekshiring."
            )
        self.write({"stage_id": stage.id})

    def action_test_start(self):
        self.ensure_one()
        self.write({
            "test_timer_start"  : fields.Datetime.now(),
            "test_timer_running": True,
        })

    def action_test_stop(self):
        self.ensure_one()
        if not self.test_timer_start:
            return
        elapsed      = self._elapsed_test_work_hours()
        total_test   = self.test_timer_accumulated + elapsed
        cto_wage     = self._get_cto_hourly_wage()
        labor_cost   = round(total_test * cto_wage, 2)
        test_sessions = self._get_test_sessions()
        test_sessions.append({
            "duration"  : round(total_test, 6),
            "cost"      : labor_cost,
            "wage"      : round(cto_wage, 2),
            "stopped_at": datetime.now().isoformat(),
        })
        self.write({
            "test_timer_running"    : False,
            "test_timer_start"      : False,
            "test_timer_accumulated": round(total_test, 6),
            "test_labor_cost"       : labor_cost,
            "test_timer_sessions"   : json.dumps(test_sessions),
        })
