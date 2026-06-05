# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    primer_apellido = fields.Char(string='Primer apellido')
    segundo_apellido = fields.Char(string='Segundo apellido')
    es_erasmus = fields.Boolean(string='Es Erasmus')
    tipo_contacto_erasmus = fields.Selection(
        selection=[
            ('estudiante', 'Estudiante'),
            ('profesor', 'Profesor'),
            ('acompaniante', 'Acompañante'),
            ('otro', 'Otro'),
        ],
        string='Tipo de contacto Erasmus',
    )
