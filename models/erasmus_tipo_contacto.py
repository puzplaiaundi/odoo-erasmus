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

    tipo_movilidad_ids = fields.Many2many(
        comodel_name='erasmus.tipo.movilidad',
        relation='erasmus_tipo_movilidad_tipo_contacto_rel',
        column1='tipo_contacto_id',
        column2='tipo_movilidad_id',
        string='Tipos de movilidad',
    )