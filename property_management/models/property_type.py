from odoo import models,fields, api

class PropertyType(models.Model):
    _name= "property.type"
    _description= "property Type"

    name = fields.Char(required=True)
    property_ids = fields.One2many("property.property","property_type_id", string="Properties")

