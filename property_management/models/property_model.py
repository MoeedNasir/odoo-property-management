from email.policy import default

from pkg_resources import require

from odoo import models, fields, api

class PropertyProperty(models.Model):
    _name = 'property.property'
    _description = 'Property'

    name = fields.Char(string="Property Name",required=True)
    description= fields.Text(string="Description")
    address = fields.Text(string="Address",required=True)
    postcode= fields.Char(string="PostCode")
    date_availability = fields.Date(string="Date",default=fields.date.today())
    expected_price = fields.Float(string="Expected Price", required=True)
    selling_price = fields.Float(string="Selling Price", required=True)
    property_kind = fields.Selection(
        [
            ('house', 'House'),
            ('apartment', 'Apartment'),
            ('office', 'Office'),
            ('warehouse', 'Warehouse'),
            ('commercial', 'Commercial'),
            ('land', 'Land'),
        ],
    )
    size = fields.Integer(string="Size in Sq Fts")
    monthly_rate = fields.Float(string="Monthly Price")
    garage = fields.Boolean(string="Garage")
    garden = fields.Boolean(string="Garden")
    is_available = fields.Boolean(string ="Currently Available" ,default= True)
    reference_code= fields.Char(string=" Reference", compute='compute_reference_code', store= True)
    property_type_id = fields.Many2one("property.type", string="Property Type", index=True)

    @api.depends('name')  # This means the computation triggers if the 'name' field changes
    def compute_reference_code(self):
        for prop in self:
            # self.id is only available after the record is created in the database.
            if prop.id:
                prop.reference_code = f"PROP{prop.id:04d}_{prop.name}"  # e.g., "PROP0005_Office Building A"
            else:
                prop.reference_code = "New Property"  # Default value before saving
    

