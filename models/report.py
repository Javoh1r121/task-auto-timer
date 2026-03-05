# -*- coding: utf-8 -*-
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class TatReport(models.TransientModel):
    _name = "tat.report"
    _description = "Task Timer Report"

    level = fields.Selection(
        [
            ("project", "Project"),
            ("task", "Task"),
        ],
        string="Level",
        readonly=True,
    )

    project_id = fields.Many2one("project.project", string="Project", readonly=True)
    user_id = fields.Many2one("res.users", string="Employee", readonly=True)
    task_id = fields.Many2one("project.task", string="Task", readonly=True)
    stage_id = fields.Many2one("project.task.type", string="Stage", readonly=True)
    total_hours = fields.Float(string="Hours Spent", digits=(10, 2), readonly=True)
    task_count = fields.Integer(string="Tasks", readonly=True)
    display_name_custom = fields.Char(string="Name", readonly=True)
    is_cto = fields.Boolean(string="CTO", default=False, readonly=True)

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    sale_price = fields.Monetary(
        string="Sale Price", currency_field="currency_id", readonly=True
    )
    cost_price = fields.Monetary(
        string="Cost Price", currency_field="currency_id", readonly=True
    )

    # ─────────────────────────────────────────────────────────
    @api.model
    def _get_cto_employee(self):
        """Sozlamadagi CTO lavozim nomiga qarab xodimni topadi."""
        try:
            job_title = self.env["ir.config_parameter"].sudo().get_param(
                "task_auto_timer.cto_job_title", "CTO"
            ) or "CTO"
            cto_emp = self.env["hr.employee"].search(
                [("job_id.name", "ilike", job_title), ("active", "=", True)],
                limit=1,
            )
            if cto_emp:
                _logger.info(
                    "TAT Report: CTO topildi — %s (user_id: %s)",
                    cto_emp.name,
                    cto_emp.user_id.id if cto_emp.user_id else "yo'q",
                )
                return cto_emp
        except Exception as e:
            _logger.warning("TAT Report: CTO topishda xato: %s", e)
        return None

    @api.model
    def _get_sale_price(self, project):
        for f in ("sale_price", "planned_revenue", "expected_revenue", "price"):
            val = getattr(project, f, None)
            if isinstance(val, (int, float)) and val:
                return float(val)
        return 0.0

    @api.model
    def _get_hourly_cost(self, user):
        """Xodimning soatlik ish haqini hr.employee → Hourly Cost field dan oladi.
        Tartibi: hourly_cost → timesheet_cost → hourly_wage
        wage (oylik maosh) ISHLATILMAYDI — bu soatlik emas.
        """
        if not user:
            return 0.0
        try:
            employee = self.env["hr.employee"].search(
                [("user_id", "=", user.id)], limit=1
            )
            if not employee:
                return 0.0
            # Faqat soatlik fieldlar — wage (oylik) o'tkazib yuboriladi
            for f in ("hourly_cost", "timesheet_cost", "hourly_wage"):
                val = getattr(employee, f, None)
                if isinstance(val, (int, float)) and val:
                    _logger.info(
                        "TAT Report: %s → %s = %.2f", employee.name, f, val
                    )
                    return float(val)
        except Exception:
            pass
        return 0.0

    # ─────────────────────────────────────────────────────────
    @api.model
    def _build_and_create(self):
        tasks = self.env["project.task"].search([("active", "=", True)])
        currency = self.env.company.currency_id.id

        # CTO ni bir marta aniqlab olamiz
        cto_emp = self._get_cto_employee()
        cto_user_id = cto_emp.user_id.id if (cto_emp and cto_emp.user_id) else None

        _logger.info("TAT Report: cto_user_id = %s", cto_user_id)

        cost_cache = {}

        def hourly_cost(user):
            if not user:
                return 0.0
            if user.id not in cost_cache:
                cost_cache[user.id] = self._get_hourly_cost(user)
            return cost_cache[user.id]

        sale_cache = {}

        def get_sale(project):
            if project.id not in sale_cache:
                sale_cache[project.id] = self._get_sale_price(project)
            return sale_cache[project.id]

        task_rows = []
        # sale_price faqat har loyihaning birinchi qatoriga yoziladi
        sale_written = set()

        def once_sale(pid, project):
            if pid not in sale_written:
                sale_written.add(pid)
                return get_sale(project)
            return 0.0

        def total_hours_from_sessions(task):
            """timer_sessions JSON dagi BARCHA sessiyalar yig'indisi."""
            try:
                sessions = json.loads(task.timer_sessions or "[]")
                return sum(float(s.get("duration", 0)) for s in sessions)
            except Exception:
                return task.total_duration or 0.0

        def total_test_hours_from_sessions(task):
            """test_timer_sessions JSON dagi BARCHA test sessiyalar yig'indisi."""
            try:
                sessions = json.loads(task.test_timer_sessions or "[]")
                return sum(float(s.get("duration", 0)) for s in sessions)
            except Exception:
                return task.test_timer_accumulated or 0.0

        def total_test_cost_from_sessions(task):
            """test_timer_sessions JSON dagi BARCHA test sessiyalar narxi yig'indisi."""
            try:
                sessions = json.loads(task.test_timer_sessions or "[]")
                return sum(float(s.get("cost", 0)) for s in sessions)
            except Exception:
                return task.test_labor_cost or 0.0

        for task in tasks:
            pid = task.project_id.id
            hours = total_hours_from_sessions(task)

            # CTO bu taskda assignee sifatida bormi?
            task_user_ids = task.user_ids.ids if task.user_ids else []

            # ── CTO qatori (test taymer asosida) ──────────────
            cto_in_task = cto_user_id and (cto_user_id in task_user_ids)
            has_test_time = total_test_hours_from_sessions(task) > 0.0

            if cto_in_task and has_test_time:
                cto_hours = round(total_test_hours_from_sessions(task), 2)
                cto_cost  = round(total_test_cost_from_sessions(task), 2)

                # Agar sessiyalarda narx yo'q bo'lsa hourly_cost dan hisoblaymiz
                if cto_cost <= 0 and cto_hours > 0:
                    cto_wage = hourly_cost(self.env["res.users"].browse(cto_user_id))
                    cto_cost = round(cto_hours * cto_wage, 2)

                task_rows.append({
                    "level": "task",
                    "project_id": pid,
                    "user_id": cto_user_id,
                    "task_id": task.id,
                    "stage_id": task.stage_id.id if task.stage_id else False,
                    "total_hours": cto_hours,
                    "cost_price": cto_cost,
                    "sale_price": once_sale(pid, task.project_id),
                    "task_count": 1,
                    "display_name_custom": task.name,
                    "currency_id": currency,
                    "is_cto": True,
                })

            # ── Oddiy xodimlar qatori (asosiy taymer) ─────────
            non_cto_users = [u for u in task.user_ids if u.id != cto_user_id]

            if non_cto_users:
                for user in non_cto_users:
                    labor = round(hours * hourly_cost(user), 2)
                    task_rows.append({
                        "level": "task",
                        "project_id": pid,
                        "user_id": user.id,
                        "task_id": task.id,
                        "stage_id": task.stage_id.id if task.stage_id else False,
                        "total_hours": round(hours, 2),
                        "cost_price": labor,
                        "sale_price": once_sale(pid, task.project_id),
                        "task_count": 1,
                        "display_name_custom": task.name,
                        "currency_id": currency,
                        "is_cto": False,
                    })
            elif not task_user_ids:
                # Umuman assignee yo'q task
                task_rows.append({
                    "level": "task",
                    "project_id": pid,
                    "task_id": task.id,
                    "stage_id": task.stage_id.id if task.stage_id else False,
                    "total_hours": round(hours, 2),
                    "cost_price": 0.0,
                    "sale_price": once_sale(pid, task.project_id),
                    "task_count": 1,
                    "display_name_custom": task.name,
                    "currency_id": currency,
                    "is_cto": False,
                })
            # else: faqat CTO assignee — CTO qatori yuqorida qo'shilgan

        for tr in sorted(task_rows, key=lambda r: -r["total_hours"]):
            self.create(tr)

    # ─────────────────────────────────────────────────────────
    @api.model
    def action_open_report(self):
        self.search([]).unlink()
        self._build_and_create()
        return {
            "type": "ir.actions.act_window",
            "name": "Task Timer Report",
            "res_model": self._name,
            "view_mode": "list",
            "views": [
                (
                    self.env.ref("task_auto_timer.view_tat_report_unified_list").id,
                    "list",
                )
            ],
            "search_view_id": [
                self.env.ref("task_auto_timer.view_tat_report_search").id
            ],
            "context": {"search_default_group_project": 1},
            "target": "current",
        }
