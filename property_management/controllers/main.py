from odoo import http
from odoo.http import request

class PropertyWebsiteController(http.Controller):

    # This defines the URL route
    @http.route('/properties', type='http', auth="public", website=True)
    def property_listing(self, **kwargs):
        # Fetch all properties that are available
        properties = request.env['property.property'].search([('is_available', '=', True)])
        # Render the template and pass the properties to it
        return request.render('property_management.property_website_template', {
            'properties': properties
        })