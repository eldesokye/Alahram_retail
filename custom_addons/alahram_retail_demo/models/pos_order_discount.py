# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError

class PosOrder(models.Model):
    _inherit = 'pos.order'

    discount_approval_status = fields.Selection([
        ('none', 'لا يوجد خصم خاص'),
        ('auto_approved', 'خصم تلقائي (<= 5%)'),
        ('pending', 'بانتظار موافقة مدير الفرع (> 5%)'),
        ('approved', 'تمت الموافقة من مدير الفرع'),
        ('rejected', 'مرفوض من مدير الفرع'),
    ], string='حالة اعتماد الخصم', default='none', compute='_compute_discount_approval_status', store=True)

    max_discount_applied = fields.Float(
        string='أعلى نسبة خصم مطبقة %',
        compute='_compute_discount_approval_status',
        store=True
    )
    discount_approver_id = fields.Many2one('res.users', string='المعتمد (مدير الفرع)')
    discount_approval_note = fields.Char(string='سبب / ملاحظات الخصم')

    branch_reservation_id = fields.Many2one(
        'alahram.branch.reservation',
        string='Branch Reservation / حجز الفروع',
        ondelete='set null'
    )
    is_branch_reservation = fields.Boolean(
        string='Has Branch Reservation / حجز فروع',
        compute='_compute_is_branch_reservation',
        store=True
    )

    @api.depends('branch_reservation_id')
    def _compute_is_branch_reservation(self):
        for order in self:
            order.is_branch_reservation = bool(order.branch_reservation_id)

    @api.depends('lines.discount')
    def _compute_discount_approval_status(self):
        for order in self:
            discounts = order.lines.mapped('discount')
            max_disc = max(discounts) if discounts else 0.0
            order.max_discount_applied = max_disc
            if max_disc == 0:
                order.discount_approval_status = 'none'
            elif max_disc <= 5.0:
                order.discount_approval_status = 'auto_approved'
            else:
                if order.discount_approval_status not in ('approved', 'rejected'):
                    order.discount_approval_status = 'pending'

    def action_approve_special_discount(self):
        """Branch Manager or Owner approves discounts > 5%"""
        self.ensure_one()
        if not self.env.user.has_group('alahram_retail_demo.group_alahram_branch_manager') and not self.env.user.has_group('alahram_retail_demo.group_alahram_owner') and not self.env.user.has_group('base.group_system'):
            raise AccessError(_("عفواً، اعتماد الخصم الذي يتجاوز 5% يتطلب صلاحية 'مدير الفرع' (سيدي جابر) أو الإدارة العليا!"))
        
        self.write({
            'discount_approval_status': 'approved',
            'discount_approver_id': self.env.user.id,
        })
        self.message_post(body=_(
            "تم اعتماد الخصم الخاص بنسبة %.2f%% بنجاح بواسطة مدير الفرع: %s"
        ) % (self.max_discount_applied, self.env.user.name))
        return True

    def action_reject_special_discount(self):
        """Branch Manager or Owner rejects discounts > 5%"""
        self.ensure_one()
        if not self.env.user.has_group('alahram_retail_demo.group_alahram_branch_manager') and not self.env.user.has_group('alahram_retail_demo.group_alahram_owner') and not self.env.user.has_group('base.group_system'):
            raise AccessError(_("عفواً، رفض أو اعتماد الخصم يتطلب صلاحية 'مدير الفرع' أو الإدارة العليا!"))
        
        self.write({
            'discount_approval_status': 'rejected',
            'discount_approver_id': self.env.user.id,
        })
        self.message_post(body=_(
            "تم رفض الخصم الخاص بنسبة %.2f%% بواسطة مدير الفرع: %s"
        ) % (self.max_discount_applied, self.env.user.name))
        return True


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    requires_manager_approval = fields.Boolean(
        string='يتطلب موافقة المدير',
        compute='_compute_requires_manager_approval',
        store=True
    )

    branch_reservation_line_id = fields.Many2one(
        'alahram.branch.reservation.line',
        string='Reservation Line / صنف الحجز',
        ondelete='set null'
    )
    fulfillment_type = fields.Selection([
        ('store_stock', 'Current Store Stock / صرف من الفرع الحالي'),
        ('pickup', 'Source Branch Pickup / استلام مباشر من الفرع المصدري'),
        ('transfer', 'Internal Transfer / شحن وتحويل للفرع الحالي')
    ], string='Fulfillment Method / طريقة الاستلام', default='store_stock')

    def _get_qty_to_move(self):
        """Prevents double stock deduction in POS when line is fulfilled via external branch pickup."""
        self.ensure_one()
        if self.fulfillment_type == 'pickup':
            return 0.0
        return super()._get_qty_to_move()

    @api.depends('discount')
    def _compute_requires_manager_approval(self):
        for line in self:
            line.requires_manager_approval = (line.discount > 5.0)

