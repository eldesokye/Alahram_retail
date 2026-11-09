# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bridal_tolerance_below = fields.Float(
        string="Bridal Lower Budget Tolerance (EGP)",
        config_parameter="alahram.bridal_tolerance_below",
        default=2000.0,
        help="Maximum preferred amount below customer target budget (Default: 2,000 EGP)."
    )
    bridal_tolerance_above_pref = fields.Float(
        string="Bridal Preferred Upper Budget Tolerance (EGP)",
        config_parameter="alahram.bridal_tolerance_above_pref",
        default=2500.0,
        help="Maximum preferred amount above customer target budget (Default: 2,500 EGP)."
    )
    bridal_tolerance_above_abs = fields.Float(
        string="Bridal Absolute Upper Budget Tolerance (EGP)",
        config_parameter="alahram.bridal_tolerance_above_abs",
        default=3000.0,
        help="Absolute maximum amount above customer target budget (Default: 3,000 EGP)."
    )
    bridal_max_recommendations = fields.Integer(
        string="Max Recommended Packages",
        config_parameter="alahram.bridal_max_recommendations",
        default=3,
        help="Maximum number of recommended package variations to present (Default: 3)."
    )
    bridal_enable_extended_range = fields.Boolean(
        string="Enable Extended Budget Range",
        config_parameter="alahram.bridal_enable_extended_range",
        default=True,
        help="Allow recommendations in the extended range (up to absolute upper bound) when no preferred match exists."
    )
    bridal_consider_cross_branch = fields.Boolean(
        string="Consider Cross-Branch Stock in Recommendations",
        config_parameter="alahram.bridal_consider_cross_branch",
        default=True,
        help="Include products available in remote branches via internal transfer."
    )

    @api.constrains('bridal_tolerance_below', 'bridal_tolerance_above_pref', 'bridal_tolerance_above_abs', 'bridal_max_recommendations')
    def _check_bridal_budget_tolerances(self):
        for rec in self:
            if rec.bridal_tolerance_below < 0:
                raise ValidationError(_("Maximum amount below target budget cannot be negative."))
            if rec.bridal_tolerance_above_pref < 0:
                raise ValidationError(_("Preferred upper budget tolerance cannot be negative."))
            if rec.bridal_tolerance_above_abs < rec.bridal_tolerance_above_pref:
                raise ValidationError(_("Absolute upper tolerance must be greater than or equal to preferred upper tolerance."))
            if rec.bridal_max_recommendations < 1:
                raise ValidationError(_("Maximum recommendations count must be at least 1."))

