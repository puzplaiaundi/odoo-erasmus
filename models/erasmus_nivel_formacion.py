# -*- coding: utf-8 -*-

from odoo import fields, models


class ErasmusNivelFormacion(models.Model):
	_name = 'erasmus.nivel.formacion'
	_description = 'Nivel de formacion Erasmus'
	_order = 'sequence, name'

	name = fields.Char(
		string='Nombre',
		required=True,
	)

	sequence = fields.Integer(
		string='Secuencia',
		default=10,
	)

	active = fields.Boolean(
		string='Activo',
		default=True,
	)
