# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ErasmusMovilidad(models.Model):
    _name = 'erasmus.movilidad'
    _description = 'Movilidad Erasmus'
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        default='Nueva movilidad',
    )

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Contacto Erasmus',
        required=True,
        domain=[('es_erasmus', '=', True)],
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('in_progress', 'En curso'),
            ('done', 'Finalizada'),
            ('cancelled', 'Cancelada'),
        ],
        string='Estado',
        default='draft',
        required=True,
    )

    date_start = fields.Date(string='Fecha inicio')
    date_end = fields.Date(string='Fecha fin')
    academic_year = fields.Char(string='Curso academico')
    extra_information = fields.Text(string='Informacion extra')
    country_preference_1_id = fields.Many2one(comodel_name='res.country', string='Preferencia pais 1')
    country_preference_2_id = fields.Many2one(comodel_name='res.country', string='Preferencia pais 2')
    country_preference_3_id = fields.Many2one(comodel_name='res.country', string='Preferencia pais 3')
    recent_graduate = fields.Boolean(string='Recien titulado')
    country_id = fields.Many2one(comodel_name='res.country', string='Pais destino')
    city = fields.Char(string='Ciudad destino')
    organization_contact_id = fields.Many2one(
        comodel_name='res.partner',
        string='Organizacion destino',
        domain=[('is_company', '=', True)],
    )
    organization_name = fields.Char(
        related='organization_contact_id.name',
        string='Nombre organizacion destino',
        store=True,
        readonly=True,
    )
    notes = fields.Text(string='Observaciones')

    dni_image_a = fields.Binary(string='Imagen DNI A', attachment=True)
    dni_image_a_filename = fields.Char(string='Nombre archivo DNI A')
    dni_image_b = fields.Binary(string='Imagen DNI B', attachment=True)
    dni_image_b_filename = fields.Char(string='Nombre archivo DNI B')
    deposit_payment_proof = fields.Binary(string='Justificante pago fianza alumnado', attachment=True)
    deposit_payment_proof_filename = fields.Char(string='Nombre archivo fianza alumnado')
    eu_scholarship_payment_proof = fields.Binary(string='Justificante pago beca UE Erasmus', attachment=True)
    eu_scholarship_payment_proof_filename = fields.Char(string='Nombre archivo beca UE Erasmus')
    gv_scholarship_payment_proof = fields.Binary(string='Justificante pago beca GV Erasmus', attachment=True)
    gv_scholarship_payment_proof_filename = fields.Char(string='Nombre archivo beca GV Erasmus')

    # Campos extraidos del contacto
    partner_name = fields.Char(related='partner_id.name', string='Nombre contacto', store=True, readonly=True)
    partner_email = fields.Char(related='partner_id.email', string='Email contacto', store=True, readonly=True)
    partner_phone = fields.Char(related='partner_id.phone', string='Telefono contacto', store=True, readonly=True)
    partner_mobile = fields.Char(related='partner_id.mobile', string='Movil contacto', store=True, readonly=True)
    partner_vat = fields.Char(related='partner_id.vat', string='NIF contacto', store=True, readonly=True)
    tipo_contacto_erasmus_id = fields.Many2one(
        related='partner_id.tipo_contacto_erasmus_id',
        comodel_name='erasmus.tipo.contacto',
        string='Tipo de contacto Erasmus',
        store=True,
        readonly=True,
    )

    tipo_contacto_code = fields.Char(
        string='Clave tipo contacto',
        compute='_compute_tipo_contacto_code',
        store=True,
    )

    tipo_movilidad_id = fields.Many2one(
        comodel_name='erasmus.tipo.movilidad',
        string='Tipo de movilidad',
        domain="[('tipo_contacto_ids', 'in', tipo_contacto_erasmus_id)]",
    )

    # Campos propios para estudiante
    centro_estudios_destino = fields.Char(string='Centro de estudios destino')
    tutor_empresa = fields.Char(string='Tutor en empresa/centro')
    beca_ue = fields.Boolean(string='Recibe beca UE')
    student_less_opportunity = fields.Boolean(string='Alumno con menos oportunidad')
    less_opportunity_reason = fields.Char(string='Motivo menor oportunidad')
    student_large_family = fields.Boolean(string='Familia numerosa')
    student_erasmus_type = fields.Char(string='Tipo de Erasmus')
    cv_english = fields.Binary(string='CV en ingles', attachment=True)
    cv_english_filename = fields.Char(string='Nombre archivo CV en ingles')
    cover_letter = fields.Binary(string='Carta de presentacion', attachment=True)
    cover_letter_filename = fields.Char(string='Nombre archivo carta de presentacion')

    # Campos propios para profesor
    asignatura_docencia = fields.Char(string='Asignatura de docencia')
    horas_docencia = fields.Float(string='Horas de docencia')
    plan_formacion = fields.Text(string='Plan de formacion')

    # Campos propios para acompaniante
    grupo_acompanado = fields.Char(string='Grupo acompanado')
    numero_participantes = fields.Integer(string='Numero de participantes')
    responsable_logistica = fields.Boolean(string='Responsable de logistica')

    @api.depends('tipo_contacto_erasmus_id.code', 'tipo_contacto_erasmus_id.name')
    def _compute_tipo_contacto_code(self):
        for rec in self:
            base = rec.tipo_contacto_erasmus_id.code or rec.tipo_contacto_erasmus_id.name or ''
            rec.tipo_contacto_code = base.strip().lower().replace(' ', '_')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self:
            if not rec.partner_id:
                rec.tipo_movilidad_id = False
                continue

            if rec.partner_id.tipo_movilidad_erasmus_id and not rec.tipo_movilidad_id:
                rec.tipo_movilidad_id = rec.partner_id.tipo_movilidad_erasmus_id

            valid_mov_types = rec.partner_id.tipo_contacto_erasmus_id.tipo_movilidad_ids
            if rec.tipo_movilidad_id and rec.tipo_movilidad_id not in valid_mov_types:
                rec.tipo_movilidad_id = False

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError('La fecha fin no puede ser anterior a la fecha inicio.')
