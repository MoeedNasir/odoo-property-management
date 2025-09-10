from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class PropertyPayment(models.Model):
    _name = 'property.payment'
    _description = 'Rent Payment'
    _order = 'due_date desc'

    name = fields.Char(string='Payment Reference', readonly=True, default='New')
    property_id = fields.Many2one('property.property', string='Property', required=True)
    tenant_id = fields.Many2one('property.tenant', string='Tenant', required=True)
    amount = fields.Float(string='Amount', required=True, tracking=True)
    due_date = fields.Date(string='Due Date', required=True, tracking=True)
    payment_date = fields.Date(string='Payment Date')
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
        ('online', 'Online Payment'),
    ], string='Payment Method')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    notes = fields.Text(string='Notes')
    is_overdue = fields.Boolean(string='Is Overdue', compute='_compute_is_overdue', store=True)
    days_overdue = fields.Integer(string='Days Overdue', compute='_compute_days_overdue', store=True)

    # Related fields for easy access
    property_name = fields.Char(related='property_id.name', string='Property Name', store=True)
    tenant_name = fields.Char(related='tenant_id.name', string='Tenant Name', store=True)
    monthly_rent = fields.Float(related='property_id.monthly_rate', string='Monthly Rent', store=True)

    @api.depends('due_date', 'state', 'payment_date')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for payment in self:
            if payment.state == 'pending' and payment.due_date and payment.due_date < today:
                payment.is_overdue = True
            else:
                payment.is_overdue = False

    @api.depends('due_date', 'state', 'payment_date')
    def _compute_days_overdue(self):
        today = fields.Date.today()
        for payment in self:
            if payment.state == 'pending' and payment.due_date and payment.due_date < today:
                payment.days_overdue = (today - payment.due_date).days
            else:
                payment.days_overdue = 0

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('property.payment') or 'New'
        return super(PropertyPayment, self).create(vals)

    def action_mark_paid(self):
        self.ensure_one()
        if self.state in ['draft', 'pending', 'overdue']:
            self.write({
                'state': 'paid',
                'payment_date': fields.Date.today()
            })

    def action_mark_pending(self):
        self.ensure_one()
        if self.state in ['draft', 'overdue']:
            self.state = 'pending'

    def action_mark_overdue(self):
        self.ensure_one()
        if self.state == 'pending':
            self.state = 'overdue'

    def action_cancel(self):
        self.ensure_one()
        if self.state != 'paid':
            self.state = 'cancelled'

    @api.constrains('due_date', 'payment_date')
    def _check_dates(self):
        for record in self:
            if record.payment_date and record.due_date and record.payment_date < record.due_date:
                raise ValidationError("Payment date cannot be before due date.")

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError("Payment amount must be positive.")

    def _cron_update_overdue_payments(self):
        """Cron job to update payment status to overdue"""
        today = fields.Date.today()
        overdue_payments = self.search([
            ('state', '=', 'pending'),
            ('due_date', '<', today)
        ])
        overdue_payments.write({'state': 'overdue'})

    def generate_monthly_payments(self):
        """Method to generate monthly payments for all rented properties"""
        today = fields.Date.today()
        rented_properties = self.env['property.property'].search([
            ('state', '=', 'available'),
            ('tenant_ids', '!=', False)
        ])

        for property in rented_properties:
            for tenant in property.tenant_ids:
                # Create payment for next month
                next_month = today + timedelta(days=30)
                self.create({
                    'property_id': property.id,
                    'tenant_id': tenant.id,
                    'amount': property.monthly_rate,
                    'due_date': next_month,
                    'state': 'draft'
                })