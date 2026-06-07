# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'
    erasmus_nombre = fields.Char(string='Nombre')
    erasmus_apellido1 = fields.Char(string='Primer apellido')
    erasmus_apellido2 = fields.Char(string='Segundo apellido')
    es_erasmus = fields.Boolean(string='Es Erasmus')
    tipo_contacto_erasmus_id = fields.Many2one(
        comodel_name='erasmus.tipo.contacto',
        string='Tipo de contacto',
    )
