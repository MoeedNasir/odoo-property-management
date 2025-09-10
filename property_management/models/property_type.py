from odoo import models,fields, api

class PropertyType(models.Model):
    _name= "property.type"
    _description= "property Type"

    name = fields.Char(required=True)
    property_ids = fields.One2many("property.property","property_type_id", string="Properties")
    property_kind = fields.Selection([
        ('house', 'House'),
        ('apartment', 'Apartment'),
        ('office', 'Office'),
        ('warehouse', 'Warehouse'),
        ('commercial', 'Commercial'),
        ('land', 'Land'),
    ], string="Category", required=True, index=True)