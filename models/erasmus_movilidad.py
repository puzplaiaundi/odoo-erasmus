# -*- coding: utf-8 -*-
from odoo import models, fields, api
import mimetypes


class ErasmusMovilidad(models.Model):
    _name = 'erasmus.movilidad'
    _description = 'Movilidad Erasmus'
    _order = 'id desc'

    # Enlace y tipo
    persona_id = fields.Many2one('erasmus.persona', string='Contacto', required=True, ondelete='cascade', index=True)
    tipo_interno = fields.Selection([
        ('estudiante', 'Estudiante'),
        ('profesor', 'Profesor'),
        ('acompaniante', 'Acompañante')
    ], string='Tipo interno de estudiante', default=lambda self: self.env.context.get('default_tipo_interno'), required=True, index=True)

    # Datos principales
    curso_academico = fields.Char(string='Curso académico')
    cuenta_bancaria = fields.Char(string='Cuenta bancaria')
    num_adjuntos_dni = fields.Selection([
        ('1', '1 adjunto'),
        ('2', '2 adjuntos'),
    ], string='Número adjuntos DNI', default='1', required=True, help='Si eliges 1 adjunto, sube ambas caras en un único archivo. Si eliges 2 adjuntos, sube anverso y reverso por separado.')
    dni = fields.Binary(string='DNI (anverso o archivo único)', attachment=True)
    dni_filename = fields.Char(string='Nombre archivo DNI')
    dni2 = fields.Binary(string='DNI 2', attachment=True)
    dni2_filename = fields.Char(string='Nombre archivo DNI 2')
    cert_titularidad_bancaria = fields.Binary(string='Certificado de titularidad bancaria', attachment=True)
    cert_titularidad_bancaria_filename = fields.Char(string='Nombre archivo Certificado titularidad')
    tipo_movilidad = fields.Char(string='Tipo movilidad')
    es_formacion = fields.Boolean(string='Es formación')

    # Datos empresa / viaje
    fecha_ida = fields.Date(string='Fecha de ida')
    fecha_vuelta = fields.Date(string='Fecha de vuelta')
    duracion_actividad_dias = fields.Integer(string='Duración actividad (días)', compute='_compute_duracion', store=True)
    que_dias = fields.Char(string='Qué días')
    pais_destino = fields.Many2one('res.country', string='País de destino')
    nombre_empresa = fields.Char(string='Nombre empresa')
    direccion_empresa = fields.Char(string='Dirección empresa')
    ciudad_empresa = fields.Char(string='Ciudad empresa')
    persona_contacto_empresa = fields.Char(string='Nombre y apellido de la persona de contacto')
    cargo_empresa = fields.Char(string='Cargo en la empresa')
    email_empresa = fields.Char(string='Correo-e empresa')
    telefono_empresa = fields.Char(string='Teléfono empresa')

    # Datos profesor / acompañante
    obj_generales = fields.Text(string='Objetivos generales de la movilidad')
    actividades_realizar = fields.Text(string='Actividades a realizar')
    resultados_impacto = fields.Text(string='Resultados e impacto previstos')
    informacion_extra_prof = fields.Text(string='Información extra')
    digital_skill = fields.Char(string='Digital skill')
    medio_transporte = fields.Char(string='Medio de transporte')

    # Datos estudiantes (nueva lógica de países Erasmus)
    # Campos antiguos conservados por compatibilidad (invisibles en vistas)
    pref_destino_1 = fields.Many2one('res.country', string='Preferencia país de destino 1', help='[LEGACY] No usar, sustituido por pref_pais_1_id')
    pref_destino_2 = fields.Many2one('res.country', string='Preferencia país de destino 2', help='[LEGACY] No usar, sustituido por pref_pais_2_id')
    pref_destino_3 = fields.Many2one('res.country', string='Preferencia país de destino 3', help='[LEGACY] No usar, sustituido por pref_pais_3_id')
    # Almacenamiento real en res.country (requerimiento)
    pref_pais_1_id = fields.Many2one('res.country', string='Preferencia país 1')
    pref_pais_2_id = fields.Many2one('res.country', string='Preferencia país 2')
    pref_pais_3_id = fields.Many2one('res.country', string='Preferencia país 3')
    # Ayuda para dominios cuando el selector UI usa erasmus.pais
    allowed_country_ids = fields.Many2many('res.country', string='Países permitidos', compute='_compute_allowed_countries', store=False)
    allowed_pais_ids = fields.Many2many('erasmus.pais', string='Países permitidos (UI)', compute='_compute_allowed_paises', store=False)
    # Campos UI (no almacenan, abren 'Search More' sobre erasmus.pais y se sincronizan con pref_pais_* res.country)
    ui_pref_pais_1_id = fields.Many2one('erasmus.pais', string='Preferencia país 1', compute='_compute_ui_pref_pais_1', inverse='_inverse_ui_pref_pais_1', store=False)
    ui_pref_pais_2_id = fields.Many2one('erasmus.pais', string='Preferencia país 2', compute='_compute_ui_pref_pais_2', inverse='_inverse_ui_pref_pais_2', store=False)
    ui_pref_pais_3_id = fields.Many2one('erasmus.pais', string='Preferencia país 3', compute='_compute_ui_pref_pais_3', inverse='_inverse_ui_pref_pais_3', store=False)
    informacion_extra_est = fields.Text(string='Información extra/peticiones')
    alumno_menos_oportunidad = fields.Boolean(string='¿Alumno con menos oportunidad?')
    motivo_menos_oportunidad = fields.Text(string='Motivo menor oportunidad')
    contacto_origen = fields.Char(string='Contacto en Origen')
    parentesco = fields.Char(string='Parentesco')
    telefono_contacto = fields.Char(string='Teléfono del Contacto')
    recien_titulado = fields.Boolean(string='Recién titulado')
    curriculum_ingles = fields.Binary(string='Curriculum en inglés', attachment=True)
    curriculum_ingles_filename = fields.Char(string='Nombre archivo CV inglés')
    carta_presentacion_ingles = fields.Binary(string='Carta de presentación en inglés', attachment=True)
    carta_presentacion_ingles_filename = fields.Char(string='Nombre archivo Carta presentación')
    certificado_1 = fields.Binary(string='Certificado 1', attachment=True)
    certificado_1_filename = fields.Char(string='Nombre archivo Certificado 1')
    certificado_2 = fields.Binary(string='Certificado 2', attachment=True)
    certificado_2_filename = fields.Char(string='Nombre archivo Certificado 2')
    certificado_3 = fields.Binary(string='Certificado 3', attachment=True)
    certificado_3_filename = fields.Char(string='Nombre archivo Certificado 3')

    # Estado
    estado_datos = fields.Selection([
        ('borrador', 'Borrador'),
        ('pendiente', 'Pendiente'),
        ('completo', 'Completo'),
    ], string='Estado datos', default='borrador', index=True)

    @api.depends('fecha_ida', 'fecha_vuelta')
    def _compute_duracion(self):
        for rec in self:
            if rec.fecha_ida and rec.fecha_vuelta and rec.fecha_vuelta >= rec.fecha_ida:
                rec.duracion_actividad_dias = (rec.fecha_vuelta - rec.fecha_ida).days
            else:
                rec.duracion_actividad_dias = 0

    @api.onchange('num_adjuntos_dni')
    def _onchange_num_adjuntos_dni(self):
        for rec in self:
            # Si no son 2 adjuntos, limpiamos el campo del reverso
            if rec.num_adjuntos_dni != '2':
                rec.dni2 = False

    @api.onchange('persona_id')
    def _onchange_persona_id(self):
        for rec in self:
            if rec.persona_id:
                # Sincroniza automáticamente el tipo con el de la persona
                rec.tipo_interno = rec.persona_id.tipo_interno or rec.tipo_interno

    def _get_country_scope_sets(self):
        Pais = self.env['erasmus.pais'].sudo()
        ambos_ids = Pais.search([('selection_scope', '=', 'ambos'), ('active', '=', True)]).mapped('country_id').ids
        estu_ids = Pais.search([('selection_scope', '=', 'estudiante'), ('active', '=', True)]).mapped('country_id').ids
        return set(ambos_ids), set(estu_ids)

    @api.depends('pref_pais_1_id', 'pref_pais_2_id', 'pref_pais_3_id')
    def _compute_allowed_countries(self):
        ambos_set, estu_set = self._get_country_scope_sets()
        for rec in self:
            selected_list = [rec.pref_pais_1_id, rec.pref_pais_2_id, rec.pref_pais_3_id]
            selected = {c.id for c in selected_list if c}
            all_three_set = all(selected_list)
            has_student_only = any(cid in estu_set for cid in selected)
            if has_student_only or not all_three_set:
                allowed = ambos_set | estu_set
            else:
                allowed = ambos_set
            rec.allowed_country_ids = [(6, 0, list(allowed))]

    @api.depends('pref_pais_1_id', 'pref_pais_2_id', 'pref_pais_3_id')
    def _compute_allowed_paises(self):
        """Igual que allowed_country_ids, pero devolviendo ids de erasmus.pais para usar en los campos UI."""
        Pais = self.env['erasmus.pais'].sudo()
        ambos_set_c, estu_set_c = self._get_country_scope_sets()
        # Mapear countries permitidos -> paises (erasmus.pais)
        ambos_pais = set(Pais.search([('country_id', 'in', list(ambos_set_c)), ('active', '=', True)]).ids)
        estu_pais = set(Pais.search([('country_id', 'in', list(estu_set_c)), ('active', '=', True)]).ids)
        for rec in self:
            selected_list = [rec.pref_pais_1_id, rec.pref_pais_2_id, rec.pref_pais_3_id]
            selected = {c.id for c in selected_list if c}
            all_three_set = all(selected_list)
            has_student_only = any(cid in estu_set_c for cid in selected)
            if has_student_only or not all_three_set:
                allowed = ambos_pais | estu_pais
            else:
                allowed = ambos_pais
            rec.allowed_pais_ids = [(6, 0, list(allowed))]

    @api.onchange('pref_pais_1_id', 'pref_pais_2_id', 'pref_pais_3_id')
    def _onchange_pref_paises(self):
        ambos_set, estu_set = self._get_country_scope_sets()
        for rec in self:
            selected_list = [rec.pref_pais_1_id, rec.pref_pais_2_id, rec.pref_pais_3_id]
            selected = {c.id for c in selected_list if c}
            all_three_set = all(selected_list)
            has_student_only = any(cid in estu_set for cid in selected)
            if has_student_only or not all_three_set:
                allowed = list(ambos_set | estu_set)
            else:
                allowed = list(ambos_set)
            domain = [('id', 'in', allowed)]
            return {'domain': {'pref_pais_1_id': domain, 'pref_pais_2_id': domain, 'pref_pais_3_id': domain}}

    # Cálculo y sincronización de campos UI (erasmus.pais <-> res.country)
    def _map_country_to_pais(self, country):
        if not country:
            return False
        return self.env['erasmus.pais'].sudo().search([('country_id', '=', country.id), ('active', '=', True)], limit=1)

    @api.depends('pref_pais_1_id')
    def _compute_ui_pref_pais_1(self):
        for rec in self:
            rec.ui_pref_pais_1_id = rec._map_country_to_pais(rec.pref_pais_1_id)

    @api.depends('pref_pais_2_id')
    def _compute_ui_pref_pais_2(self):
        for rec in self:
            rec.ui_pref_pais_2_id = rec._map_country_to_pais(rec.pref_pais_2_id)

    @api.depends('pref_pais_3_id')
    def _compute_ui_pref_pais_3(self):
        for rec in self:
            rec.ui_pref_pais_3_id = rec._map_country_to_pais(rec.pref_pais_3_id)

    def _inverse_ui_pref_pais_1(self):
        for rec in self:
            rec.pref_pais_1_id = rec.ui_pref_pais_1_id.country_id if rec.ui_pref_pais_1_id else False

    def _inverse_ui_pref_pais_2(self):
        for rec in self:
            rec.pref_pais_2_id = rec.ui_pref_pais_2_id.country_id if rec.ui_pref_pais_2_id else False

    def _inverse_ui_pref_pais_3(self):
        for rec in self:
            rec.pref_pais_3_id = rec.ui_pref_pais_3_id.country_id if rec.ui_pref_pais_3_id else False

    @api.onchange('ui_pref_pais_1_id')
    def _onchange_ui_pref_pais_1(self):
        for rec in self:
            rec.pref_pais_1_id = rec.ui_pref_pais_1_id.country_id if rec.ui_pref_pais_1_id else False

    @api.onchange('ui_pref_pais_2_id')
    def _onchange_ui_pref_pais_2(self):
        for rec in self:
            rec.pref_pais_2_id = rec.ui_pref_pais_2_id.country_id if rec.ui_pref_pais_2_id else False

    @api.onchange('ui_pref_pais_3_id')
    def _onchange_ui_pref_pais_3(self):
        for rec in self:
            rec.pref_pais_3_id = rec.ui_pref_pais_3_id.country_id if rec.ui_pref_pais_3_id else False

    @api.model_create_multi
    def create(self, vals_list):
        # Asegurar tipo_interno desde contexto o persona
        for vals in vals_list:
            if not vals.get('tipo_interno'):
                pid = vals.get('persona_id') or self.env.context.get('default_persona_id')
                if pid:
                    persona = self.env['erasmus.persona'].browse(pid)
                    vals['tipo_interno'] = persona.tipo_interno or self.env.context.get('default_tipo_interno') or 'estudiante'
                else:
                    vals['tipo_interno'] = self.env.context.get('default_tipo_interno') or 'estudiante'
        return super().create(vals_list)

    def write(self, vals):
        # Si cambia la persona y no se indicó tipo, sincronizar con el tipo de la nueva persona
        if 'persona_id' in vals and 'tipo_interno' not in vals and vals.get('persona_id'):
            persona = self.env['erasmus.persona'].browse(vals['persona_id'])
            vals = dict(vals, tipo_interno=persona.tipo_interno or 'estudiante')
        return super().write(vals)

    def action_download_binary(self):
        self.ensure_one()
        field = self.env.context.get('binary_field')
        if not field:
            raise ValueError('No se indicó el campo binario a descargar (binary_field).')
        value = getattr(self, field, False)
        if not value:
            raise ValueError('No hay archivo cargado para descargar.')
        # Determinar nombre de archivo preferido
        filename_field = f"{field}_filename"
        filename = getattr(self, filename_field, None)
        if not filename:
            # Intentar recuperar el adjunto para obtener 'name' o inferir extensión desde mimetype
            att = self.env['ir.attachment'].search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('res_field', '=', field),
            ], order='id desc', limit=1)
            if att:
                filename = att.name or None
                # Si no tiene extensión pero hay mimetype, intentar adivinar
                if filename and '.' not in filename and att.mimetype:
                    ext = mimetypes.guess_extension(att.mimetype) or ''
                    # Corrección común: image/jpeg suele devolver .jpe
                    if ext == '.jpe':
                        ext = '.jpg'
                    filename = f"{filename}{ext}"
        # Fallback final
        if not filename:
            # Intentar una extensión genérica a partir del contenido si existe mimetype en attachments previos
            filename = f"{field}.bin"
        url = f"/web/content/{self._name}/{self.id}/{field}/{filename}?download=true"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }


