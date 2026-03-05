# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    project_id = fields.Many2one(
        "project.project", string="Linked Project", readonly=True
    )
    project_created = fields.Boolean(
        string="Project Created", default=False, readonly=True, copy=False
    )

    def action_create_project(self):
        """Won bo'lganda Project yaratish - faqat bir marta"""
        self.ensure_one()
        if self.project_created:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Info",
                    "message": "Project already created for this lead!",
                    "sticky": False,
                },
            }

        new_project = self.env["project.project"].create(
            {
                "name": self.name,
                "partner_id": self.partner_id.id if self.partner_id else False,
                "expected_revenue": self.expected_revenue,
                "crm_lead_id": self.id,
            }
        )

        stages = [
            ("To Do",       False),
            ("In Progress", False),
            ("Waiting",     False),
            ("Test",        False),
            ("Validation",  False),
            ("Done",        True),   # fold=True — Kanban da yashiriladi
        ]
        for index, (stage_name, folded) in enumerate(stages):
            self.env["project.task.type"].create(
                {
                    "name": stage_name,
                    "project_ids": [(4, new_project.id)],
                    "sequence": index + 1,
                    "fold": folded,
                }
            )

        self.write(
            {
                "project_id": new_project.id,
                "project_created": True,
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "res_id": new_project.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.onchange("expected_revenue")
    def _onchange_expected_revenue(self):
        """Lead narxi o'zgarganda Project narxini yangilash"""
        if self.project_id:
            self.project_id.expected_revenue = self.expected_revenue
