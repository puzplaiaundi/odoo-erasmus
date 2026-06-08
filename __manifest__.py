# -*- coding: utf-8 -*-
{
    'name': "Gestión Erasmus",

    'summary': "Gestión unificada de personas Erasmus (estudiantes, profesores, acompañantes)",

    'description': """
Módulo para gestionar personas vinculadas a Erasmus (Estudiantes, Profesores y Acompañantes) en un único modelo.
    """,

    'author': "Pablo uzquiano",
    'website': "https://www.plaiaundi.com",

    'category': 'Uncategorized',
    'version': '17.0.1.0.0',
    'license': 'LGPL-3',

    'depends': [
        'base', 
        'contacts',
        'mail'
        ],

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/erasmus_tipo_contacto_views.xml',
        'views/erasmus_nivel_formacion_views.xml',
        'views/menu_views.xml',
        'views/res_partner_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}