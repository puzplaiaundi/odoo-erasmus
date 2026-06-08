# -*- coding: utf-8 -*-

from odoo import fields, models


class ErasmusCicloFormativo(models.Model):
    _name = 'erasmus.ciclo.formativo'
    _description = 'Ciclo Formativo'
    _order = 'nivel_formacion_id, sequence, name'

    sequence = fields.Integer(
        string='Secuencia',
        default=10
    )

    name = fields.Char(
        string='Nombre del Ciclo Formativo',
        required=True
    )

    descripcion = fields.Text(
        string='Descripción'
    )

    codigo = fields.Char(
        string='Código',
        required=True
    )

    nivel_formacion_id = fields.Many2one(
        'erasmus.nivel.formacion',
        string='Nivel de Formación',
        required=True,
        ondelete='restrict'
    )
    familia_profesional_id = fields.Many2one(
        'erasmus.familia.profesional',
        string='Familia Profesional',
        required=False,
        ondelete='restrict'
    )

    active = fields.Boolean(
        string='Activo',
        default=True
    )