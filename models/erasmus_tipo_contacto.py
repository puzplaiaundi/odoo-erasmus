# -*- coding: utf-8 -*-

from odoo import fields, models


class ErasmusTipoContacto(models.Model):
    _name = 'erasmus.tipo.contacto'
    _description = 'Tipo de contacto Erasmus'
    _order = 'sequence, name'

    name = fields.Char(
        string='Nombre',
        required=True,
    )

    code = fields.Char(
        string='Código',
    )

    sequence = fields.Integer(
        string='Secuencia',
        default=10,
    )

    active = fields.Boolean(
        string='Activo',
        default=True,
    )