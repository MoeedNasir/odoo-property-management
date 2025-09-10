from odoo.exceptions import ValidationError
from datetime import date
from odoo import models, fields, api


class PropertyProperty(models.Model):
    _name = 'property.property'
    _description = 'Property'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    _sql_constraints = [
        ('unique_property_name', 'UNIQUE(name)', 'Property name must be unique!'),
    ]

    name = fields.Char(string="Property Name", required=True, index=True, tracking=True)
    description = fields.Text(string="Description")
    address = fields.Text(string="Address", required=True, tracking=True)
    postcode = fields.Char(string="PostCode")
    date_availability = fields.Date(string="Date", default=fields.date.today(), index=True)
    expected_price = fields.Float(string="Expected Price", required=True, tracking=True)
    selling_price = fields.Float(string="Selling Price", required=True, tracking=True)
    property_kind = fields.Selection(
        [
            ('house', 'House'),
            ('apartment', 'Apartment'),
            ('office', 'Office'),
            ('warehouse', 'Warehouse'),
            ('commercial', 'Commercial'),
            ('land', 'Land'),
        ], string="Category", required=True, index=True, tracking=True
    )
    size = fields.Integer(string="Size in Sq Fts", tracking=True)
    monthly_rate = fields.Float(string="Monthly Price", index=True, tracking=True)
    garage = fields.Boolean(string="Garage")
    garden = fields.Boolean(string="Garden")
    garden_area = fields.Integer(string="Garden Area (sq m)")
    garden_orientation = fields.Selection(
        [
            ('north', 'North'),
            ('south', 'South'),
            ('east', 'East'),
            ('west', 'West'),
        ],
        string="Garden Orientation"
    )
    # computed field to avoid conflicts
    is_available = fields.Boolean(
        string="Currently Available",
        compute='_compute_is_available',
        store=True,
        index=True
    )
    reference_code = fields.Char(string="Reference", compute='compute_reference_code', store=True)
    property_type_id = fields.Many2one("property.type", string="Property Type", index=True,
                                       domain="[('property_kind', '=', property_kind)]")
    tenant_ids = fields.One2many('property.tenant', 'property_id', string='Tenants')
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('available', 'Available'),
            ('sold', 'Sold'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        copy=False,
        index=True,
        tracking=True
    )
    payment_ids = fields.One2many('property.payment', 'property_id', string='Payments')

    # Added computed fields for financial overview
    total_revenue = fields.Float(string='Total Revenue', compute='_compute_financial_totals', store=True)
    pending_payments = fields.Float(string='Pending Payments', compute='_compute_financial_totals', store=True)
    overdue_payments = fields.Float(string='Overdue Payments', compute='_compute_financial_totals', store=True)

    @api.depends('state')
    def _compute_is_available(self):
        """Compute is_available based on state"""
        for record in self:
            record.is_available = (record.state == 'available')

    @api.depends('name')
    def compute_reference_code(self):
        for prop in self:
            if prop.id:
                prop.reference_code = f"PROP{prop.id:04d}_{prop.name}"
            else:
                prop.reference_code = "New Property"

    @api.constrains('expected_price', 'selling_price')
    def _check_prices(self):
        for record in self:
            if record.expected_price < 0:
                raise ValidationError("The Expected Price must be a positive number.")
            if record.selling_price < 0:
                raise ValidationError("The Selling Price must be a positive number.")
            if record.selling_price and record.expected_price and record.selling_price > record.expected_price:
                raise ValidationError("Selling Price cannot exceed the Expected Price.")

    @api.constrains('size')
    def _check_size(self):
        for record in self:
            if record.size and record.size <= 0:
                raise ValidationError("The property size must be greater than zero.")

    @api.constrains('date_availability')
    def _check_date_availability(self):
        for record in self:
            if record.date_availability and record.date_availability < date.today():
                raise ValidationError("The availability date cannot be in the past.")

    @api.constrains('state', 'selling_price')
    def _check_sold_needs_price(self):
        for record in self:
            if record.state == 'sold' and record.selling_price <= 0:
                raise ValidationError("A sold property must have a Selling Price greater than zero.")

    @api.constrains('is_available', 'tenant_ids')
    def _check_tenant_if_rented(self):
        for record in self:
            # If property is NOT available (rented), it must have tenants
            if not record.is_available and not record.tenant_ids:
                raise ValidationError("A rented property must have at least one tenant assigned.")

            # If property has tenants, it should NOT be available
            if record.tenant_ids and record.is_available:
                raise ValidationError("A property with tenants should not be marked as available.")

    def _validate_state_transition(self, target_state):
        """Validate if state transition is allowed with current data"""
        self.ensure_one()

        if target_state == 'available':
            if not self.address:
                raise ValidationError("Address is required to make property available.")
            if self.monthly_rate <= 0:
                raise ValidationError("Monthly rate must be set to make property available.")

        elif target_state == 'sold':
            if self.expected_price <= 0:
                raise ValidationError("Cannot mark as sold without an expected price.")
            if self.selling_price <= 0:
                raise ValidationError("Selling price must be set to mark as sold.")

    def action_mark_available(self):
        """Mark property as available"""
        self.ensure_one()
        if self.state == 'draft':
            self._validate_state_transition('available')
            self.state = 'available'
            self.message_post(
                body="Property is now available for rent/sale.",
                subject="Property Available",
                message_type="comment"
            )

    def action_mark_sold(self):
        """Mark property as sold"""
        self.ensure_one()
        if self.state in ['draft', 'available']:
            self._validate_state_transition('sold')
            self.state = 'sold'
            self.message_post(
                body=f"Property marked as sold. Selling price: ${self.selling_price}",
                subject="Property Sold",
                message_type="comment"
            )

    def action_mark_cancelled(self):
        """Mark property as cancelled"""
        self.ensure_one()
        if self.state in ['draft', 'available']:
            self.state = 'cancelled'
            self.message_post(
                body="Property listing cancelled.",
                subject="Property Cancelled",
                message_type="comment"
            )

    def action_reopen(self):
        """Reopen a sold or cancelled property (back to draft)"""
        self.ensure_one()
        if self.state in ['sold', 'cancelled']:
            self.state = 'draft'
            self.message_post(
                body="Property reopened for editing.",
                subject="Property Reopened",
                message_type="comment"
            )

    @api.constrains('state')
    def _check_state_transitions(self):
        """Ensure valid state transitions and data consistency"""
        for record in self:
            if record.state == 'sold':
                if record.expected_price <= 0:
                    raise ValidationError("Cannot mark as sold without an expected price.")
                if record.selling_price <= 0:
                    raise ValidationError("Selling price must be set for sold properties.")

            elif record.state == 'available':
                if not record.address:
                    raise ValidationError("Address is required for available properties.")
                if record.monthly_rate <= 0:
                    raise ValidationError("Monthly rate must be set for available properties.")

    def get_available_properties(self):
        """Optimized method to get available properties with prefetching"""
        available_props = self.search([('state', '=', 'available')])

        # Prefetch related data for better performance
        if available_props:
            available_props.mapped('property_type_id.name')
            available_props.mapped('tenant_ids.name')

        return available_props

    @api.onchange('garden')
    def _onchange_garden(self):
        """When garden is checked, set default garden area and orientation"""
        for record in self:
            if record.garden:
                record.garden_area = 100
                record.garden_orientation = 'north'
            else:
                record.garden_area = 0
                record.garden_orientation = False

    @api.onchange('property_kind')
    def _onchange_property_kind(self):
        """When category changes, clear the specific type"""
        for record in self:
            record.property_type_id = False

    @api.depends('payment_ids', 'payment_ids.amount', 'payment_ids.state')
    def _compute_financial_totals(self):
        for property in self:
            paid_payments = property.payment_ids.filtered(lambda p: p.state == 'paid')
            pending_payments = property.payment_ids.filtered(lambda p: p.state in ['pending', 'overdue'])
            overdue_payments = property.payment_ids.filtered(lambda p: p.state == 'overdue')

            property.total_revenue = sum(paid_payments.mapped('amount'))
            property.pending_payments = sum(pending_payments.mapped('amount'))
            property.overdue_payments = sum(overdue_payments.mapped('amount'))