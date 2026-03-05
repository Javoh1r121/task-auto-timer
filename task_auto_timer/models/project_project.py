from odoo import api, fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    crm_lead_id = fields.Many2one("crm.lead", string="Linked CRM Lead", readonly=True)

    expected_revenue = fields.Float(
        string="Expected Revenue",
        digits=(10, 2),
        help="Expected revenue from this project, linked to CRM Lead.",
    )

    @api.onchange("expected_revenue")
    def _onchange_expected_revenue(self):
        """Project narxi o'zgarganda Lead narxini yangilash"""
        if self.crm_lead_id:
            self.crm_lead_id.expected_revenue = self.expected_revenue
