# -*- coding: utf-8 -*-
{
    'name': 'Property Management',
    'version': '1.0',
    'summary': 'This is a Company Property & Rental Management System',
    'description' : """ This module will manage commercial or residential properties, tenants, leases, maintenance requests, and payments""",
    'Category': 'Property Management',
    'Author': 'Moeed Nasir',
    'Website': 'https://moeed-portfolio.netlify.app/',
    'License': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'data/property_type.xml',
        'security/ir.model.access.csv',
        'views/property_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
}