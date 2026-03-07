# -*- coding: utf-8 -*-
from odoo import models, fields


class ErasmusCiclo(models.Model):
    _name = 'erasmus.ciclo'
    _description = 'Ciclo Formativo Erasmus'
    _order = 'familia_profesional, name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, index=True)
    familia_profesional = fields.Selection([
        ('informatica', 'Informática y Comunicaciones'),
        ('administracion', 'Administración y Gestión'),
        ('comercio', 'Comercio y Marketing'),
        ('transporte', 'Transporte y Mantenimiento de Vehículos'),
        ('sanidad', 'Sanidad'),
        ('servicios', 'Servicios Socioculturales y a la Comunidad'),
        # ('otros', 'Otros / Formación complementaria'),
    ], required=True, index=True)

    # Nivel del ciclo (para filtrar por nivel de impartición)
    nivel = fields.Selection([
        ('fpb', 'FP Básica'),
        ('cfgm', 'Grado Medio'),
        ('cfgs', 'Grado Superior'),
        ('egm', 'Especialización Grado Medio'),
        ('egs', 'Especialización Grado Superior'),
    ], index=True)

    _sql_constraints = [
        ('uniq_code', 'unique(code)', 'El código del ciclo debe ser único.')
    ]


