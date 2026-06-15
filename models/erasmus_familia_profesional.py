# -*- coding: utf-8 -*-

from odoo import fields, models


class ErasmusFamiliaProfesional(models.Model):
    _name = 'erasmus.familia.profesional'
    _description = 'Familia Profesional'
    _order = 'sequence, name'

    sequence = fields.Integer(
        string='Secuencia',
        default=10
    )

    name = fields.Char(
        string='Nombre de la Familia Profesional',
        required=True,
        translate=True
    )
    active = fields.Boolean(
        string='Activo',
        default=True
    )