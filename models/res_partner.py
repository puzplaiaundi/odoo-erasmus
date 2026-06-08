# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    erasmus_nombre = fields.Char(string='Nombre')
    erasmus_apellido1 = fields.Char(string='Primer apellido')
    erasmus_apellido2 = fields.Char(string='Segundo apellido')
    es_erasmus = fields.Boolean(string='Es Erasmus')
    erasmus_becado = fields.Boolean(string='Es becado')
    erasmus_familia_numerosa = fields.Boolean(string='Familia numerosa')
    erasmus_discapacitado = fields.Boolean(string='Discapacitado')
    dni_anverso = fields.Binary(string='DNI anverso', attachment=True)
    dni_anverso_filename = fields.Char(string='Nombre archivo DNI anverso')
    dni_reverso = fields.Binary(string='DNI reverso', attachment=True)
    dni_reverso_filename = fields.Char(string='Nombre archivo DNI reverso')
    tipo_contacto_erasmus_id = fields.Many2one(
        comodel_name='erasmus.tipo.contacto',
        string='Tipo de contacto',
    )

    nivel_formacion_erasmus_id = fields.Many2one(
        comodel_name='erasmus.nivel.formacion',
        string='Nivel de formacion',
    )

    idioma_1_id = fields.Many2one(
        comodel_name='res.lang',
        string='Idioma 1',
    )
    nivel_idioma_1_id = fields.Many2one(
        comodel_name='erasmus.nivel.idioma',
        string='Nivel idioma 1',
    )
    idioma_1_acreditado = fields.Boolean(
        string='Certificado idioma 1',
    )

    idioma_2_id = fields.Many2one(
        comodel_name='res.lang',
        string='Idioma 2',
    )
    nivel_idioma_2_id = fields.Many2one(
        comodel_name='erasmus.nivel.idioma',
        string='Nivel idioma 2',
    )
    idioma_2_acreditado = fields.Boolean(
        string='Certificado idioma 2',
    )

    idioma_3_id = fields.Many2one(
        comodel_name='res.lang',
        string='Idioma 3',
    )
    nivel_idioma_3_id = fields.Many2one(
        comodel_name='erasmus.nivel.idioma',
        string='Nivel idioma 3',
    )
    idioma_3_acreditado = fields.Boolean(
        string='Certificado idioma 3',
    )
