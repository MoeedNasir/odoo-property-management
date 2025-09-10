from odoo import models, fields, api


class PropertyTenant(models.Model):
    _name = 'property.tenant'
    _description = 'Tenant'

    name = fields.Char(string='Tenant Name', required=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    # This is the CRITICAL Many2one link back to the property
    property_id = fields.Many2one('property.property', string='Leased Property')
    # Added payment relationship
    payment_ids = fields.One2many('property.payment', 'tenant_id', string='Payments')

    # Computed fields for financial overview
    total_paid = fields.Float(string='Total Paid', compute='_compute_payment_totals', store=True)
    total_due = fields.Float(string='Total Due', compute='_compute_payment_totals', store=True)
    overdue_amount = fields.Float(string='Overdue Amount', compute='_compute_payment_totals', store=True)

    # Add user relationship
    user_id = fields.Many2one('res.users',string='System User',help="Link to system user account for portal access")

    @api.depends('payment_ids', 'payment_ids.amount', 'payment_ids.state')
    def _compute_payment_totals(self):
        for tenant in self:
            paid_payments = tenant.payment_ids.filtered(lambda p: p.state == 'paid')
            pending_payments = tenant.payment_ids.filtered(lambda p: p.state in ['pending', 'overdue'])
            overdue_payments = tenant.payment_ids.filtered(lambda p: p.state == 'overdue')

            tenant.total_paid = sum(paid_payments.mapped('amount'))
            tenant.total_due = sum(pending_payments.mapped('amount'))
            tenant.overdue_amount = sum(overdue_payments.mapped('amount'))

    def action_create_user_account(self):
        """Create a user account for the tenant"""
        self.ensure_one()
        if not self.user_id:
            # Create user with tenant access
            user_group = self.env.ref('property_management.group_tenant_user')
            user = self.env['res.users'].create({
                'name': self.name,
                'login': self.email or f"{self.name.lower().replace(' ', '.')}@tenant.com",
                'groups_id': [(4, user_group.id)],
                'partner_id': self.env['res.partner'].create({
                    'name': self.name,
                    'email': self.email,
                    'phone': self.phone
                }).id
            })
            self.user_id = user.id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'res_id': self.user_id.id,
            'view_mode': 'form',
            'target': 'current',
        }