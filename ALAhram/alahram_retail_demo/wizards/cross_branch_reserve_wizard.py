# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AlahramCrossBranchReserveWizard(models.TransientModel):
    _name = 'alahram.cross.branch.reserve.wizard'
    _description = 'معالج طلب الحجز والتحويل السريع بين الفروع'

    product_id = fields.Many2one('product.product', string='الصنف المطلوب', required=True)
    product_code = fields.Char(related='product_id.default_code', string='كود الصنف')
    product_barcode = fields.Char(related='product_id.barcode', string='الباركود')
    quantity = fields.Float(string='الكمية المراد حجزها وتحويلها', default=1.0, required=True)

    dest_warehouse_id = fields.Many2one(
        'stock.warehouse', string='فرع الاستلام (سيدي جابر)',
        required=True,
        default=lambda self: self.env['stock.warehouse'].search([('code', '=', 'WH-SG')], limit=1)
    )
    src_warehouse_id = fields.Many2one(
        'stock.warehouse', string='الفرع المحول منه (المتوفر لديه)',
        required=True,
        default=lambda self: self.env['stock.warehouse'].search([('code', '=', 'WH-ROSHDY')], limit=1)
    )
    notes = fields.Text(string='ملاحظات الطلب', default='طلب حجز عاجل لصالح عميل صالة العرض')

    def action_confirm_and_create_transfer(self):
        self.ensure_one()
        reserve = self.env['alahram.cross.branch.reserve'].create({
            'product_id': self.product_id.id,
            'quantity': self.quantity,
            'dest_warehouse_id': self.dest_warehouse_id.id,
            'src_warehouse_id': self.src_warehouse_id.id,
            'notes': self.notes,
        })
        reserve.action_confirm_reservation()
        reserve.action_ship_to_transit()

        return {
            'name': _('طلب الحجز والتحويل المنشأ'),
            'type': 'ir.actions.act_window',
            'res_model': 'alahram.cross.branch.reserve',
            'res_id': reserve.id,
            'view_mode': 'form',
            'target': 'current',
        }

