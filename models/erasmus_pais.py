# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ErasmusPais(models.Model):
    _name = 'erasmus.pais'
    _description = 'País Erasmus (preferencias)'
    _rec_name = 'name'
    _order = 'name_es'

    name = fields.Char(string='Nombre (EU - ES)', compute='_compute_name', store=True, index=True)
    name_eu = fields.Char(string='Nombre es Euskera', required=True)
    name_es = fields.Char(string='Nombre en Castellano', required=True, index=True)
    country_id = fields.Many2one('res.country', string='País de Odoo', required=True, index=True)
    selection_scope = fields.Selection([
        ('ambos', 'Ambos'),
        ('estudiante', 'Estudiante'),
    ], string='Lo pueden seleccionar', default='ambos', required=True, index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('uniq_country_scope', 'unique(country_id)', 'Cada país de Odoo solo puede estar una vez en la tabla de países Erasmus.'),
    ]

    @api.depends('name_eu', 'name_es')
    def _compute_name(self):
        for rec in self:
            eu = rec.name_eu or ''
            es = rec.name_es or ''
            rec.name = f"{eu} - {es}" if eu and es else (eu or es)

    def name_get(self):
        """Usar el nombre compuesto almacenado para asegurar consistencia en cualquier parte (dropdowns, search more, etc.)."""
        return [(rec.id, rec.name or '') for rec in self]


