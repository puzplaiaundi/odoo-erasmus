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
        # Bump de versión para forzar que Odoo detecte actualización y recargue vistas/plantillas
    'version': '17.0.1.0.18',
    'license': 'LGPL-3',

    'depends': ['base', 'web', 'mail', 'portal'],

    'data': [
        'security/groups.xml',
        'security/rules.xml',
        'security/ir.model.access.csv',
        'data/ciclos.xml',
        'data/codigos.xml',
        'data/paises.xml',
        'report/erasmus_persona_contract_report.xml',
        'views/movilidad/form_views.xml',
        'views/persona/kanban_views.xml',
        'views/persona/tree_views.xml',
        'views/persona/search_views.xml',
        'views/persona/form_views.xml',
        'views/persona/action_views.xml',
        'views/persona/server_action_views.xml',
        'views/catalog/codigo_views.xml',
        'views/catalog/pais_views.xml',
        'views/partner/form_inherit_views.xml',
        'views/menu/menuitem_views.xml',
        'views/templates.xml',
        'views/users.xml',
    ],
    # App icon/screenshots for Apps view and App Store
    # Preferred: static/description/icon.png (512x512)
    # We'll also point to the JPG name you prefer for convenience
    'images': [
        'static/description/icon.png',
        'static/description/iconoplaiaundi.jpg',
    ],
    # Explicit icon path used by the Apps view; standard expected icon is icon.png
    'icon': '/gestion_erasmus/static/description/icon.png',
    'assets': {
        'web.assets_backend': [
            '/gestion_erasmus/static/src/js/direccion_autocomplete.js',
            '/gestion_erasmus/static/src/scss/form_readonly_labels.scss',
            '/gestion_erasmus/static/src/css/backend.css',
        ],
        'web.assets_frontend': [
            '/gestion_erasmus/static/src/css/portal.css',
        ],
    },
    'external_dependencies': {
        'python': ['pdfrw'],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'demo': [
        'demo/demo.xml',
    ],
    'post_init_hook': 'post_init_hook',
}