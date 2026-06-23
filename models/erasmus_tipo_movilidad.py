# -*- coding: utf-8 -*-

from odoo import fields, models


class ErasmusTipoMovilidad(models.Model):
    _name = 'erasmus.tipo.movilidad'
    _description = 'Tipo de movilidad Erasmus'
    _order = 'sequence, name'

    name = fields.Char(
        string='Descripcion',
        required=True,
    )

    code = fields.Char(
        string='Codigo',
    )

    sequence = fields.Integer(
        string='Secuencia',
        default=10,
    )

    tipo_contacto_ids = fields.Many2many(
        comodel_name='erasmus.tipo.contacto',
        relation='erasmus_tipo_movilidad_tipo_contacto_rel',
        column1='tipo_movilidad_id',
        column2='tipo_contacto_id',
        string='Tipos de contacto asociados',
    )

    active = fields.Boolean(
        string='Activo',
        default=True,
    )
