# -*- coding: utf-8 -*-
from odoo import models, fields


class ErasmusCodigo(models.Model):
    _name = 'erasmus.codigo'
    _description = 'Catálogo de Códigos (Programa, Código Erasmus, ISCED-F)'
    _order = 'key, ciclo_id, id'

    key = fields.Selection([
        ('programa', 'Programa'),
        ('codigo_erasmus', 'Código Erasmus'),
        ('codigo_iscedf', 'Código ISCED-F'),
    ], required=True, index=True)
    ciclo_id = fields.Many2one('erasmus.ciclo', string='Ciclo', index=True, help='Opcional: específica por ciclo. Si está vacío, actúa como valor global por defecto.')
    valor = fields.Char(string='Valor', required=True)
    active = fields.Boolean(default=True)
    note = fields.Char(string='Descripción', help='Notas u observaciones del código')

    _sql_constraints = [
        ('uniq_key_ciclo', 'unique(key, ciclo_id)', 'Ya existe un código para esa clave y ciclo.'),
    ]

 
