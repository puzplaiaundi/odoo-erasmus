# -*- coding: utf-8 -*-

from odoo import api, fields, models


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

    familia_profesional_erasmus_id = fields.Many2one(
        comodel_name='erasmus.familia.profesional',
        string='Familia profesional',
    )

    nivel_formacion_erasmus_disponible_ids = fields.Many2many(
        comodel_name='erasmus.nivel.formacion',
        compute='_compute_niveles_formacion_disponibles',
        string='Niveles de formacion disponibles',
    )

    nivel_formacion_erasmus_id = fields.Many2one(
        comodel_name='erasmus.nivel.formacion',
        string='Nivel de formacion',
        domain="[('id', 'in', nivel_formacion_erasmus_disponible_ids)]",
    )

    ciclo_formativo_erasmus_id = fields.Many2one(
        comodel_name='erasmus.ciclo.formativo',
        string='Ciclo formativo',
        domain="[('nivel_formacion_id', '=', nivel_formacion_erasmus_id), ('familia_profesional_id', '=', familia_profesional_erasmus_id)]",
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

    @api.depends('familia_profesional_erasmus_id')
    def _compute_niveles_formacion_disponibles(self):
        Ciclo = self.env['erasmus.ciclo.formativo']
        for partner in self:
            if not partner.familia_profesional_erasmus_id:
                partner.nivel_formacion_erasmus_disponible_ids = [(5, 0, 0)]
                continue

            ciclos = Ciclo.search([
                ('familia_profesional_id', '=', partner.familia_profesional_erasmus_id.id),
                ('nivel_formacion_id', '!=', False),
            ])
            niveles = ciclos.mapped('nivel_formacion_id')
            partner.nivel_formacion_erasmus_disponible_ids = [(6, 0, niveles.ids)]

    @api.onchange('familia_profesional_erasmus_id')
    def _onchange_familia_profesional_erasmus(self):
        for partner in self:
            if not partner.familia_profesional_erasmus_id:
                partner.nivel_formacion_erasmus_id = False
                partner.ciclo_formativo_erasmus_id = False
                continue

            niveles_validos = partner.nivel_formacion_erasmus_disponible_ids
            if partner.nivel_formacion_erasmus_id not in niveles_validos:
                partner.nivel_formacion_erasmus_id = False
                partner.ciclo_formativo_erasmus_id = False
                continue

            if partner.ciclo_formativo_erasmus_id and (
                partner.ciclo_formativo_erasmus_id.familia_profesional_id != partner.familia_profesional_erasmus_id
                or partner.ciclo_formativo_erasmus_id.nivel_formacion_id != partner.nivel_formacion_erasmus_id
            ):
                partner.ciclo_formativo_erasmus_id = False

    @api.onchange('nivel_formacion_erasmus_id')
    def _onchange_nivel_formacion_erasmus(self):
        for partner in self:
            if not partner.nivel_formacion_erasmus_id:
                partner.ciclo_formativo_erasmus_id = False
                continue

            if partner.ciclo_formativo_erasmus_id and (
                partner.ciclo_formativo_erasmus_id.nivel_formacion_id != partner.nivel_formacion_erasmus_id
                or partner.ciclo_formativo_erasmus_id.familia_profesional_id != partner.familia_profesional_erasmus_id
            ):
                partner.ciclo_formativo_erasmus_id = False

    @api.model
    def _build_erasmus_full_name(self, nombre=None, apellido1=None, apellido2=None):
        nombre = (nombre or '').strip()
        apellido1 = (apellido1 or '').strip()
        apellido2 = (apellido2 or '').strip()

        apellidos = ' '.join(part for part in [apellido1, apellido2] if part)
        if apellidos and nombre:
            return '%s, %s' % (apellidos, nombre)
        return apellidos or nombre

    @api.onchange('erasmus_nombre', 'erasmus_apellido1', 'erasmus_apellido2')
    def _onchange_erasmus_name_parts(self):
        for partner in self:
            full_name = partner._build_erasmus_full_name(
                partner.erasmus_nombre,
                partner.erasmus_apellido1,
                partner.erasmus_apellido2,
            )
            partner.name = full_name or False

    @api.model_create_multi
    def create(self, vals_list):
        tracked_fields = ('erasmus_nombre', 'erasmus_apellido1', 'erasmus_apellido2')
        for vals in vals_list:
            is_erasmus = vals.get('es_erasmus')
            has_name_parts = any(vals.get(key) for key in tracked_fields)
            if is_erasmus or has_name_parts:
                full_name = self._build_erasmus_full_name(
                    vals.get('erasmus_nombre'),
                    vals.get('erasmus_apellido1'),
                    vals.get('erasmus_apellido2'),
                )
                if full_name:
                    vals['name'] = full_name
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)

        if self.env.context.get('skip_erasmus_name_sync'):
            return res

        tracked_fields = {'erasmus_nombre', 'erasmus_apellido1', 'erasmus_apellido2'}
        if not tracked_fields.intersection(vals):
            return res

        for partner in self:
            full_name = partner._build_erasmus_full_name(
                partner.erasmus_nombre,
                partner.erasmus_apellido1,
                partner.erasmus_apellido2,
            )
            if full_name and partner.name != full_name:
                super(ResPartner, partner.with_context(skip_erasmus_name_sync=True)).write({
                    'name': full_name,
                })

        return res


