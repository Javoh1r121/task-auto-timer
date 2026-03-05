# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TatSettings(models.TransientModel):
    """Task Auto Timer uchun sozlamalar — res.config.settings ga qo'shimcha."""
    _inherit = "res.config.settings"

    # ── Ish vaqti ─────────────────────────────────────────────
    tat_work_start = fields.Integer(
        string="Ish boshlanish soati",
        default=9,
        config_parameter="task_auto_timer.work_start",
        help="Masalan: 9 → 09:00",
    )
    tat_work_end = fields.Integer(
        string="Ish tugash soati",
        default=19,
        config_parameter="task_auto_timer.work_end",
        help="Masalan: 19 → 19:00",
    )
    tat_work_days = fields.Char(
        string="Ish kunlari (0=Dushanba … 6=Yakshanba)",
        default="0,1,2,3,4,5",
        config_parameter="task_auto_timer.work_days",
        help="Vergul bilan ajrating. 0=Du, 1=Se, 2=Ch, 3=Pa, 4=Ju, 5=Sh, 6=Ya",
    )

    # ── Stage nomlari ─────────────────────────────────────────
    tat_stage_in_progress = fields.Char(
        string="'In Progress' stage nomi",
        default="In Progress",
        config_parameter="task_auto_timer.stage_in_progress",
        help="Taymer avtomatik yonishi uchun stage nomi",
    )
    tat_stage_waiting = fields.Char(
        string="'Waiting' stage nomi",
        default="Waiting",
        config_parameter="task_auto_timer.stage_waiting",
        help="Taymer pause bo'lishi uchun stage nomi",
    )
    tat_stage_test = fields.Char(
        string="'Test' stage nomi",
        default="Test",
        config_parameter="task_auto_timer.stage_test",
        help="CTO taymer va test jarayoni boshlanadigan stage",
    )
    tat_stage_todo = fields.Char(
        string="'To Do' stage nomi",
        default="To Do",
        config_parameter="task_auto_timer.stage_todo",
        help="Qaytarish uchun stage nomi",
    )
    tat_stage_validation = fields.Char(
        string="'Validation' stage nomi",
        default="Validation",
        config_parameter="task_auto_timer.stage_validation",
        help="Tasdiqlash uchun stage nomi",
    )
    tat_stage_done = fields.Char(
        string="'Done' stage nomi",
        default="Done",
        config_parameter="task_auto_timer.stage_done",
        help="Tugatish uchun stage nomi",
    )

    # ── CTO sozlamasi ─────────────────────────────────────────
    tat_cto_job_title = fields.Char(
        string="CTO lavozim nomi (Job Position)",
        default="CTO",
        config_parameter="task_auto_timer.cto_job_title",
        help="Employees → Job Position da ko'rsatilgan lavozim nomi",
    )
