# -*- coding: utf-8 -*-
{
    'name': "Gestión Erasmus",

    'summary': "Gestión unificada de personas Erasmus (estudiantes, profesores, acompañantes)",

    'description': """
Módulo para gestionar personas vinculadas a Erasmus (Estudiantes, Profesores y Acompañantes) en un único modelo.
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '17.0.1.1.0',
    'license': 'LGPL-3',

    'depends': ['base', 'contacts'],

    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}