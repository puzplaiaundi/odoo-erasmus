# -*- coding: utf-8 -*-

from odoo import fields, models


class ErasmusNivelIdioma(models.Model):
	_name = 'erasmus.nivel.idioma'
	_description = 'Nivel de idioma '
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
