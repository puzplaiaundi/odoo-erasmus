# -*- coding: utf-8 -*-

from odoo import fields, models


class ErasmusPrograma(models.Model):
	_name = 'erasmus.programa'
	_description = 'Programa Erasmus'
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
