# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
import unicodedata


class ErasmusPersona(models.Model):
    _name = 'erasmus.persona'
    _description = 'Persona Erasmus (Estudiante / Profesor / Acompañante)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'nombre_completo'
    _order = 'apellido1, apellido2, nombre'
    # Debug logging to trace street persistence
    _logger = logging.getLogger(__name__)
     # Archivado
    active = fields.Boolean(default=True, tracking=True)

    # Tipo
    tipo_interno = fields.Selection([
        ('no_asignado', 'No asignado'),
        ('estudiante', 'Estudiante'),
        ('profesor', 'Profesor'),
        ('acompaniante', 'Acompañante')
    ], string='Tipo', required=True, default='estudiante', index=True)

    estado_documentacion = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En proceso'),
        ('completo', 'Completo')
    ], string='Estado de Documentación', default='pendiente', tracking=True)

    @api.onchange('tipo_interno')
    def _onchange_tipo_interno_estado_doc(self):
        for rec in self:
            if rec.tipo_interno != 'estudiante':
                rec.estado_documentacion = False
    # Relación profesor-alumnos
    profesor_id = fields.Many2one(
        'erasmus.persona',
        string='Profesor asignado',
        domain="[('tipo_interno', '=', 'profesor')]",
        help='Profesor responsable de este estudiante',
        tracking=True
    )
    alumno_ids = fields.One2many(
        'erasmus.persona',
        'profesor_id',
        string='Alumnos a cargo',
        help='Estudiantes asignados a este profesor',
        tracking=True
    )
    # Relacionados auxiliares para filtros de seguridad / menús
    profesor_user_id = fields.Many2one('res.users', string='Usuario Profesor', related='profesor_id.user_id', store=True, index=True, compute_sudo=True)
    profesor_partner_id = fields.Many2one('res.partner', string='Contacto Profesor', related='profesor_id.partner_id', store=True, index=True, compute_sudo=True)

    # Progreso de documentación (0-100) para tarjetas "Mis Alumnos"
    # No almacenado: se recalcula al vuelo para reflejar cambios inmediatamente
    progreso_documentacion = fields.Integer(string='Progreso', compute='_compute_progreso_documentacion', store=False)

    # Flujo de revisión profesor/admin
    revision_estado = fields.Selection([
        ('no_enviado', 'No enviado'),
        ('enviado', 'Enviado'),
        ('en_revision', 'En revisión'),
        ('revisado', 'Revisado'),
        ('devuelto', 'Devuelto'),
    ], string='Estado de revisión', default='no_enviado', tracking=True, index=True)
    fecha_envio_revision = fields.Datetime(string='Fecha envío a revisión')
    fecha_revision = fields.Datetime(string='Fecha revisión')
    fecha_devolucion = fields.Datetime(string='Fecha devolución')
    # Columna de Kanban para profesores: Pendiente / En proceso / Listo / Enviados
    kanban_col_profesor = fields.Selection([
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En proceso'),
        ('listo', 'Listo'),
        ('enviados', 'Enviados'),
    ], compute='_compute_kanban_col_profesor', string='Columna (Profesor)', store=True, index=True)

    @api.depends(
        'tipo_interno', 'revision_estado', 'estado_documentacion',
        'nombre', 'apellido1', 'apellido2', 'nif', 'email', 'movil', 'centro_formacion',
        'fecha_nacimiento', 'genero', 'nacionalidad',
        'street', 'city', 'zip', 'state_id', 'country_id'
    )
    def _compute_kanban_col_profesor(self):
        for rec in self:
            col = False
            if rec.tipo_interno == 'estudiante':
                if rec.revision_estado in ('enviado', 'en_revision'):
                    col = 'enviados'
                elif rec.estado_documentacion == 'completo' or (rec.progreso_documentacion or 0) >= 100:
                    col = 'listo'
                elif rec.estado_documentacion == 'en_proceso' or (rec.progreso_documentacion or 0) > 0:
                    col = 'en_proceso'
                else:
                    col = 'pendiente'
            rec.kanban_col_profesor = col

    # --- Acciones profesor/admin ---
    def _ensure_profesor_scope(self):
        """Profesores solo sobre sus alumnos."""
        if self.env.user.has_group('gestion_erasmus.group_erasmus_profesor') and not self.env.user.has_group('gestion_erasmus.group_erasmus_admin'):
            invalid = self.filtered(lambda r: r.profesor_user_id.id != self.env.user.id)
            if invalid:
                raise ValidationError('No puedes operar sobre alumnos que no están a tu cargo.')

    def _ensure_admin(self):
        if not self.env.user.has_group('gestion_erasmus.group_erasmus_admin'):
            raise ValidationError('Acción reservada para administradores.')

    def action_enviar_borradores(self):
        """Profesor: enviar a revisión los alumnos listos.
        Reglas:
        - Solo estudiantes del profesor
        - Solo estado_documentacion = completo (o progreso 100)
        - Solo si revision_estado in (no_enviado, devuelto)
        """
        self._ensure_profesor_scope()
        candidates = self.filtered(lambda r: r.tipo_interno == 'estudiante' and (r.estado_documentacion == 'completo' or (r.progreso_documentacion or 0) >= 100) and r.revision_estado in ('no_enviado', 'devuelto'))
        if not candidates:
            raise ValidationError('No hay alumnos aptos para enviar (deben estar Listo y no haber sido ya enviados).')
        now = fields.Datetime.now()
        candidates.write({'revision_estado': 'enviado', 'fecha_envio_revision': now})
        for rec in candidates:
            rec.message_post(body='Borrador enviado para revisión por el profesor.')
        return {'type': 'ir.actions.act_window_close'}

    def action_marcar_en_revision(self):
        self._ensure_admin()
        targets = self.filtered(lambda r: r.revision_estado in ('enviado',))
        if not targets:
            raise ValidationError('Solo puedes marcar "En revisión" los que están Enviados.')
        targets.write({'revision_estado': 'en_revision'})
        for rec in targets:
            rec.message_post(body='El administrador ha marcado el alumno como En revisión.')
        return {'type': 'ir.actions.act_window_close'}

    def action_marcar_revisado(self):
        self._ensure_admin()
        targets = self.filtered(lambda r: r.revision_estado in ('en_revision', 'enviado'))
        if not targets:
            raise ValidationError('Solo puedes marcar como Revisado los que están En revisión o Enviados.')
        now = fields.Datetime.now()
        targets.write({'revision_estado': 'revisado', 'fecha_revision': now})
        for rec in targets:
            rec.message_post(body='Revisión completada por administración.')
        return {'type': 'ir.actions.act_window_close'}

    def action_devolver_al_profesor(self):
        self._ensure_admin()
        targets = self.filtered(lambda r: r.revision_estado in ('enviado', 'en_revision'))
        if not targets:
            raise ValidationError('Solo puedes devolver alumnos que están Enviados o En revisión.')
        now = fields.Datetime.now()
        targets.write({'revision_estado': 'devuelto', 'fecha_devolucion': now})
        for rec in targets:
            rec.message_post(body='Devolución al profesor para corrección.')
        return {'type': 'ir.actions.act_window_close'}

    def action_contrato_pdf(self):
        """Abrir el contrato PDF (rellenado vía ruta HTTP)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f"/gestion_erasmus/contrato_pdf/{self.id}",
            'target': 'new',
        }

    def action_contrato_qweb(self):
        """Generar el contrato mediante el informe QWeb del módulo.

        Este método es invocado por un botón type="object" en la vista para evitar
        problemas de resolución de XMLID en botones type="action" editados desde la BD.
        """
        self.ensure_one()
        # Referencia segura al XMLID de la acción de informe y ejecución sobre el registro
        report = self.env.ref('gestion_erasmus.report_gestion_erasmus_contrato_persona')
        return report.report_action(self)

    @api.onchange('tipo_interno')
    def _onchange_tipo_interno_profesor_alumno(self):
        # Si no es estudiante, limpiar profesor_id
        for rec in self:
            if rec.tipo_interno != 'estudiante':
                rec.profesor_id = False
            # Si no es profesor, limpiar alumno_ids (solo visual, no borra estudiantes)
            if rec.tipo_interno != 'profesor':
                rec.alumno_ids = [(5, 0, 0)]


   
    

    # Campos comunes de identificación
    partner_id = fields.Many2one('res.partner', string='Contacto vinculado', tracking=True, help='Contacto de Odoo asociado a esta persona para usar el chat y correo.')
    # Alias manual (no usamos mail.alias.mixin para evitar creación automática en install/import)
    alias_id = fields.Many2one('mail.alias', string='Alias', readonly=True)
    user_id = fields.Many2one('res.users', string='Usuario Vinculado', readonly=True, help='Usuario de Odoo asociado para acceso al sistema.')
    nombre = fields.Char(tracking=True)
    apellido1 = fields.Char(string='Primer Apellido', tracking=True)
    apellido2 = fields.Char(string='Segundo Apellido', tracking=True)
    nif = fields.Char(string='NIF', related='partner_id.vat', store=True, readonly=False, index=True, tracking=True, compute_sudo=True)
    # Campos que coinciden con res.partner como relacionados para unificar fuente de verdad
    email = fields.Char(string='Email', related='partner_id.email', store=True, readonly=False, tracking=True, compute_sudo=True)
    movil = fields.Char(string='Móvil', related='partner_id.mobile', store=True, readonly=False, tracking=True, compute_sudo=True)
    centro_formacion = fields.Char(string='Centro de Formación', tracking=True)

    # Dirección (estilo res.partner para autocompletar)
    street = fields.Char(string='Dirección', related='partner_id.street', store=True, readonly=False, compute_sudo=True)
    street2 = fields.Char(string='Dirección (2)', related='partner_id.street2', store=True, readonly=False, compute_sudo=True)
    zip = fields.Char(string='C.P.', related='partner_id.zip', store=True, readonly=False, compute_sudo=True)
    city = fields.Char(string='Ciudad', related='partner_id.city', store=True, readonly=False, compute_sudo=True)
    state_id = fields.Many2one('res.country.state', string='Provincia / Estado', related='partner_id.state_id', store=True, readonly=False, compute_sudo=True)
    country_id = fields.Many2one('res.country', string='País', related='partner_id.country_id', store=True, readonly=False, compute_sudo=True)
    # Detalles adicionales de la dirección
    portal = fields.Char(string='Portal')
    puerta = fields.Char(string='Puerta')
    # (Eliminado) Campo de autocompletado tipo Maps, se usa el widget directamente en 'street'

    # Datos personales
    fecha_nacimiento = fields.Date(string='Fecha de Nacimiento')
    genero = fields.Selection([
        ('masculino', 'Masculino'),
        ('femenino', 'Femenino'),
        ('otro', 'Otro')
    ], string='Género')
    nacionalidad = fields.Many2one('res.country', string='Nacionalidad')

    # Imagen (para Kanban / futura foto)
    image_1920 = fields.Image(string='Foto')

    # UI visibility flags (computed from tipo_interno for reliable dynamic behavior)
    show_nacionalidad = fields.Boolean(string='Mostrar Nacionalidad', compute='_compute_ui_visibility_flags')
    show_antiguedad = fields.Boolean(string='Mostrar Antigüedad', compute='_compute_ui_visibility_flags')
    show_idiomas = fields.Boolean(string='Mostrar Idiomas', compute='_compute_ui_visibility_flags')
    show_profesor_coord = fields.Boolean(string='Mostrar Profesor Coord.', compute='_compute_ui_visibility_flags')

    # Niveles de impartición (etiquetas adaptadas al formato mostrado en los selects de las capturas)
    nivel_imparticion = fields.Selection([
        ('fpb', 'HASIERAKO LANBIDE HEZIKETA - FORMACIÓN PROFESIONAL INICIAL'),
        ('cfgm', 'ERDI MAILAKO ZIKLOA - CICLO FORMATIVO DE GRADO MEDIO'),
        ('cfgs', 'GOI MAILAKO ZIKLOA - CICLO FORMATIVO DE GRADO SUPERIOR'),
        ('egm', 'ERDI MAILAKO EZPEZIALIZAZIO IKASTAROA - CURSO DE ESPECIALIZACIÓN DE GRADO MEDIO'),
        ('egs', 'GOI MAILAKO EZPEZIALIZAZIO IKASTAROA - CURSO DE ESPECIALIZACIÓN DE GRADO SUPERIOR')
    ], string='Nivel de Impartición / Estudios')

    # Familias profesionales (etiquetas adaptadas al formato mostrado en los selects de las capturas)
    familia_profesional = fields.Selection([
        ('informatica', 'INFORMATIKA ETA KOMUNIKAZIOA - INFORMÁTICA Y COMUNICACIÓN - COMPUTING AND COMMUNICATION'),
        ('administracion', 'ADMINISTRAZIOA ETA KUDEAKETA - ADMINISTRACIÓN Y GESTIÓN - BUSINESS AND MANAGEMENT'),
        ('comercio', 'MERKATARITZA ETA MARKETINGA - COMERCIO Y MÁRKETING - TRADE AND MARKETING'),
        ('sanidad', 'OSASUNA - SANIDAD - HEALTH'),
        ('servicios', 'GIZARTE ETA KULTUR ZERBITZUAK - SERVICIOS SOCIOCULTURALES Y A LA COMUNIDAD - SOCIO-CULTURAL AND COMMUNITY SERVICES'),
        ('transporte', 'GARRAIOA ETA IBILGAIUEN MANTENTZE LANAK - TRANSPORTE Y MANTENIMIENTO DE VEHÍCULOS - TRANSPORT AND VEHICLE MAINTENANCE')
    ], string='Familia Profesional')

    # Ciclos formativos oficiales (según familias profesionales impartidas en Plaiaundi)
    ciclo_formativo = fields.Selection([
        # Informática y Comunicaciones
        ('smr', 'SM R - MIKROINFORMATIKA SISTEMAK ETA SAREAK - SISTEMAS MICROINFORMÁTICOS Y REDES - MICROCOMPUTER SYSTEMS AND NETWORKS'),
        ('asir', 'ASIR - SARE-INFORMATIKA SISTEMEN ADMINISTRAZIOA - ADMINISTRACIÓN DE SISTEMAS INFORMÁTICOS EN RED - COMPUTER NETWORK SYSTEMS MANAGEMENT'),
        ('dam', 'DAM - PLATAFORMA ANITZEKO APLIKAZIOEN GARAPENA - DESARROLLO DE APLICACIONES MULTIPLATAFORMA - MULTI-PLATFORM APPLICATIONS DEVELOPMENT'),
        ('daw', 'DAW - WEB APLIKAZIOEN GARAPENA - DESARROLLO DE APLICACIONES WEB - DEVELOPMENT OF WEB APPLICATIONS'),

        # Administración y Gestión
        ('gestion_admin', 'GESTION ADMIN - ADMINISTRAZIO KUDEAKETA - GESTIÓN ADMINISTRATIVA - ADMINISTRATIVE MANAGEMENT'),
        ('admin_finanzas', 'ADMIN FINANZAS - ADMINISTRAZIOA ETA FINANTZAK - ADMINISTRACIÓN Y FINANZAS - ADMINISTRATION AND FINANCE'),

        # Comercio y Marketing / Transporte y Logística
        ('conduccion_transportes', 'CONDUCCION - ERREPIDE GARRAIOARAKO IBILGAILUAK GIDATZEA - CONDUCCIÓN DE VEHÍCULOS DE TRANSPORTE POR CARRETERA - DRIVING ROAD TRANSPORT VEHICLES'),
        ('comercio_internacional', 'COMERCIO INT - NAZIOARTEKO MERKATARITZA - COMERCIO INTERNACIONAL - INTERNATIONAL TRADE'),
        ('transporte_logistica', 'TRANSPORTE LOG - GARRAIOA ETA LOGISTIKA - TRANSPORTE Y LOGÍSTICA - TRANSPORTS AND LOGISTICS'),

        # Sanidad
        ('aux_enfermeria', 'AUX ENFERMERIA - ERIZAINTZAREN LAGUNTZA OSAGARRIAK - CUIDADOS AUXILIARES DE ENFERMERÍA - AUXILIARY NURSERY CARE'),
        ('farmacia', 'FARMACIA - FARMAZIA ETA PARAFARMAZIA - FARMACIA Y PARAFARMACIA - PHARMACY AND PARAPHARMACY'),
        ('dependencia', 'DEPENDENCIA - MENDEKOTASUN-EGOERAN DAUDEN PERTSONENTZAKO ARRETA - ATENCIÓN A PERSONAS EN SITUACIÓN DE DEPENDENCIA - ASSISTANCE TO PEOPLE IN NEED OF CARE'),
        ('laboratorio', 'LABORATORIO - LABORATEGI KLINIKO ETA BIOMEDIKOA - LABORATORIO CLÍNICO Y BIOMÉDICO - CLINICAL AND BIOMEDICAL LABORATORY'),
        ('dietetica', 'DIETETICA - DIETETIKA - DIETÉTICA - DIETETICS'),

        # Servicios Socioculturales y a la Comunidad
        ('integracion', 'INTEGRACION - GIZARTERATZEA - INTEGRACIÓN SOCIAL - SOCIAL INTEGRATION'),
        ('educacion_infantil', 'EDUC INF - HAUR HEZKUNTZA - EDUCACIÓN INFANTIL - PRE-PRIMARY EDUCATION')
    ], string='Ciclo Formativo')

    # Nuevo: referencia Many2one a catálogo de Ciclos para permitir dominio dinámico en la vista
    ciclo_formativo_id = fields.Many2one(
        'erasmus.ciclo',
        string='Ciclo Formativo',
        domain="[('familia_profesional', '=', familia_profesional), ('nivel', '=', nivel_imparticion)]"
    )

    requiere_explicacion = fields.Boolean(string='Requiere Explicación', compute='_compute_requiere_explicacion', store=True, readonly=True)
    explicacion_especializacion = fields.Text(string='Explicación (especialización)')

    @api.depends('nivel_imparticion')
    def _compute_requiere_explicacion(self):
        for rec in self:
            rec.requiere_explicacion = rec.nivel_imparticion in ('egm', 'egs')

    # Idiomas (comunes en estudiante y profesor)
    nivel_ingles = fields.Selection([
        ('a1', 'A1'), ('a2', 'A2'), ('b1', 'B1'), ('b2', 'B2'), ('c1', 'C1'), ('c2', 'C2'), ('nativo', 'Nativo')
    ], string='Nivel Inglés')
    nivel_frances = fields.Selection([
        ('a1', 'A1'), ('a2', 'A2'), ('b1', 'B1'), ('b2', 'B2'), ('c1', 'C1'), ('c2', 'C2'), ('nativo', 'Nativo')
    ], string='Nivel Francés')
    nivel_aleman = fields.Selection([
        ('a1', 'A1'), ('a2', 'A2'), ('b1', 'B1'), ('b2', 'B2'), ('c1', 'C1'), ('c2', 'C2'), ('nativo', 'Nativo')
    ], string='Nivel Alemán')

    # Preferencias de país (Erasmus) en la ficha de la persona
    pref_pais_1_id = fields.Many2one('erasmus.pais', string='Preferencia país 1')
    pref_pais_2_id = fields.Many2one('erasmus.pais', string='Preferencia país 2')
    pref_pais_3_id = fields.Many2one('erasmus.pais', string='Preferencia país 3')
    show_student_only_paises = fields.Boolean(string='Mostrar países solo estudiante', compute='_compute_show_student_only_paises', store=False)

    @api.depends('pref_pais_1_id.selection_scope', 'pref_pais_2_id.selection_scope', 'pref_pais_3_id.selection_scope')
    def _compute_show_student_only_paises(self):
        for rec in self:
            rec.show_student_only_paises = any(p.selection_scope == 'estudiante' for p in [rec.pref_pais_1_id, rec.pref_pais_2_id, rec.pref_pais_3_id] if p)

    @api.onchange('pref_pais_1_id', 'pref_pais_2_id', 'pref_pais_3_id')
    def _onchange_pref_paises_persona(self):
        """Dominio de erasmus.pais en ficha Persona, respetando regla:
        - Mientras no estén las 3 preferencias cubiertas, mostrar TODOS (ambos + estudiante).
        - Si entre las 3 hay al menos un país 'solo estudiante', seguir mostrando TODOS.
        - Si están las 3 y ninguna es 'solo estudiante', mostrar solo 'ambos'.
        """
        Pais = self.env['erasmus.pais'].sudo()
        ambos_ids = set(Pais.search([('selection_scope', '=', 'ambos'), ('active', '=', True)]).ids)
        estu_ids = set(Pais.search([('selection_scope', '=', 'estudiante'), ('active', '=', True)]).ids)
        for rec in self:
            selected_list = [rec.pref_pais_1_id, rec.pref_pais_2_id, rec.pref_pais_3_id]
            selected = {p.id for p in selected_list if p}
            all_three_set = all(selected_list)
            has_student_only = any(pid in estu_ids for pid in selected)
            if has_student_only or not all_three_set:
                allowed = list(ambos_ids | estu_ids)
            else:
                allowed = list(ambos_ids)
            domain = [('id', 'in', allowed)]
            return {'domain': {'pref_pais_1_id': domain, 'pref_pais_2_id': domain, 'pref_pais_3_id': domain}}

    # Códigos (ahora controlados por catálogo y de solo lectura)
    codigo_erasmus = fields.Char(string='Código Erasmus', help='Código para identificar al estudiante en el programa Erasmus', compute='_compute_codigos', store=True, readonly=True)
    programa = fields.Char(string='Programa', compute='_compute_codigos', store=True, readonly=True)
    codigo_iscedf = fields.Char(string='Código ISCED-F', compute='_compute_codigos', store=True, readonly=True)

    profesor_coordinador_nombre = fields.Char(string='Nombre Profesor Coordinador')
    profesor_coordinador_apellido1 = fields.Char(string='Primer Apellido Profesor Coordinador')
    profesor_coordinador_apellido2 = fields.Char(string='Segundo Apellido Profesor Coordinador')
    profesor_coordinador_email = fields.Char(string='Email Profesor Coordinador')
    profesor_coordinador_telefono = fields.Char(string='Teléfono Profesor Coordinador')

    # Campo solo Profesor
    antiguedad_educacion = fields.Integer(string='Años Experiencia Educación')

    # Computed full name
    nombre_completo = fields.Char(string='Nombre Completo', compute='_compute_nombre_completo', store=True)
    # Alias estándar para compatibilidad con componentes que esperan un campo 'name'
    name = fields.Char(string='Nombre', related='nombre_completo', store=True, readonly=True)

    # Sincronización básica con contacto (campos comunes)
    partner_name = fields.Char(string='Nombre contacto', related='partner_id.name', readonly=True)
    partner_email = fields.Char(string='Email contacto', related='partner_id.email', readonly=True)

    _sql_constraints = [
        ('uniq_nif', 'unique(nif)', 'El NIF debe ser único.'),
    ]

 
    @api.depends(
        'tipo_interno',
        'nombre', 'apellido1', 'apellido2', 'nif', 'email', 'movil', 'centro_formacion',
        'fecha_nacimiento', 'genero', 'nacionalidad',
        'street', 'city', 'zip', 'state_id', 'country_id'
    )
    def _compute_progreso_documentacion(self):
        """Cálculo de progreso basado SOLO en datos personales y dirección.
        Campos considerados (15 en total):
        - Personales: nombre, apellido1, apellido2, nif, email, movil, centro_formacion,
          fecha_nacimiento, genero, nacionalidad
        - Dirección: street, city, zip, state_id, country_id
        Cada campo aporta el mismo peso. 100% cuando todos están informados.
        Solo aplica a estudiantes; otros tipos quedan en 0.
        """
        for rec in self:
            if rec.tipo_interno != 'estudiante':
                rec.progreso_documentacion = 0
                continue
            fields_ok = [
                bool((rec.nombre or '').strip()),
                bool((rec.apellido1 or '').strip()),
                bool((rec.apellido2 or '').strip()),
                bool((rec.nif or '').strip()),
                bool((rec.email or '').strip()),
                bool((rec.movil or '').strip()),
                bool((rec.centro_formacion or '').strip()),
                bool(rec.fecha_nacimiento),
                bool(rec.genero),
                bool(rec.nacionalidad),
                bool((rec.street or '').strip()),
                bool((rec.city or '').strip()),
                bool((rec.zip or '').strip()),
                bool(rec.state_id),
                bool(rec.country_id),
            ]
            total = len(fields_ok) or 1
            present = sum(1 for v in fields_ok if v)
            rec.progreso_documentacion = int(round((present / total) * 100))

    

    @api.constrains('tipo_interno', 'nombre', 'apellido1', 'email', 'movil', 'nif')
    def _check_required_when_assigned(self):
        """Exigir datos básicos cuando tipo_interno no es 'no_asignado'."""
        for rec in self:
            if rec.tipo_interno and rec.tipo_interno != 'no_asignado':
                missing = []
                if not (rec.nombre or '').strip():
                    missing.append('Nombre')
                if not (rec.apellido1 or '').strip():
                    missing.append('Primer Apellido')
                if not (rec.email or '').strip():
                    missing.append('Email')
                if not (rec.movil or '').strip():
                    missing.append('Móvil')
                if not (rec.nif or '').strip():
                    missing.append('NIF')
                if missing:
                    raise ValidationError('Los siguientes campos son obligatorios salvo para tipo "No asignado": %s' % ', '.join(missing))


    @api.depends('tipo_interno')
    def _compute_ui_visibility_flags(self):
        for rec in self:
            if rec.tipo_interno == 'profesor':
                rec.show_nacionalidad = False
                rec.show_antiguedad = True
                rec.show_idiomas = False
                rec.show_profesor_coord = False
            elif rec.tipo_interno == 'estudiante':
                rec.show_nacionalidad = True
                rec.show_antiguedad = False
                rec.show_idiomas = True
                rec.show_profesor_coord = True
            else:
                # acompaniante (u otros)
                rec.show_nacionalidad = False
                rec.show_antiguedad = False
                rec.show_idiomas = False
                rec.show_profesor_coord = False

    # --- Contacto vinculado: helpers ---
    def action_create_or_link_partner(self):
        """Crear o vincular un res.partner con los datos básicos.
        - Si ya hay partner_id: abrirlo.
        - Si no, crearlo con nombre completo + email + móvil + dirección.
        Luego suscribirlo como follower para recibir mensajes/correos.
        """
        self.ensure_one()
        Partner = self.env['res.partner']
        if self.partner_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Contacto',
                'res_model': 'res.partner',
                'view_mode': 'form',
                'res_id': self.partner_id.id,
                'target': 'current',
            }
        safe_name = self.nombre_completo or ' '.join(p for p in [self.nombre, self.apellido1, self.apellido2] if p) or 'Sin nombre'
        vals = {
            'name': safe_name,
            'vat': self.nif or False,
            'email': self.email or False,
            'mobile': self.movil or False,
            'street': self.street or False,
            'street2': self.street2 or False,
            'zip': self.zip or False,
            'city': self.city or False,
            'state_id': self.state_id.id or False,
            'country_id': self.country_id.id or False,
        }
        partner = Partner.sudo().create(vals)
        self.partner_id = partner.id
        # Auto-suscribir contacto a la ficha para chatter y mails
        self.message_subscribe(partner_ids=[partner.id])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contacto',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': partner.id,
            'target': 'current',
        }

    def action_sync_to_partner(self):
        """Empujar cambios básicos al partner vinculado."""
        for rec in self:
            if not rec.partner_id:
                continue
            vals = {
                'name': rec.nombre_completo or rec.nombre,
                'email': rec.email or False,
                'mobile': rec.movil or False,
                'street': rec.street or False,
                'street2': rec.street2 or False,
                'zip': rec.zip or False,
                'city': rec.city or False,
                'state_id': rec.state_id.id or False,
                'country_id': rec.country_id.id or False,
            }
            rec.partner_id.write(vals)
            # asegurar suscripción
            rec.message_subscribe(partner_ids=[rec.partner_id.id])

    @api.model
    def _get_user_group_config(self, tipo):
        """Return the target groups/share/notification profile for a given tipo."""
        group_portal = self.env.ref('base.group_portal', raise_if_not_found=False)
        group_user = self.env.ref('base.group_user', raise_if_not_found=False)
        group_profesor = self.env.ref('gestion_erasmus.group_erasmus_profesor', raise_if_not_found=False)

        portal_id = group_portal.id if group_portal else False
        user_id = group_user.id if group_user else False
        profesor_id = group_profesor.id if group_profesor else False

        managed_ids = {gid for gid in [portal_id, user_id, profesor_id] if gid}
        target_ids = set()
        share = False
        notification = 'inbox'

        if tipo == 'estudiante':
            share = True
            notification = 'email'
            if portal_id:
                target_ids.add(portal_id)
        elif tipo == 'profesor':
            if user_id:
                target_ids.add(user_id)
            if profesor_id:
                target_ids.add(profesor_id)
        elif tipo in ('acompaniante', 'no_asignado'):
            if user_id:
                target_ids.add(user_id)
        else:
            if user_id:
                target_ids.add(user_id)

        return {
            'managed_ids': managed_ids,
            'target_ids': target_ids,
            'share': share,
            'notification': notification,
        }

    

    @api.model_create_multi
    def create(self, vals_list):
        self._logger.info("[erasmus.persona] CREATE vals_list=%s", vals_list)
        Partner = self.env['res.partner']
        for vals in vals_list:
            # Reglas especialización
            lvl = vals.get('nivel_imparticion')
            if lvl in ('egm', 'egs'):
                vals.update({'familia_profesional': False, 'ciclo_formativo_id': False, 'ciclo_formativo': False})
            # Crear contacto si no viene
            if not vals.get('partner_id'):
                full_name = ' '.join(p for p in [vals.get('nombre'), vals.get('apellido1'), vals.get('apellido2')] if p) or 'Sin nombre'
                partner = Partner.sudo().with_context(skip_auto_persona=True).create({
                    'name': full_name,
                    'vat': vals.get('nif') or False,
                    'email': vals.get('email') or False,
                    'mobile': vals.get('movil') or False,
                    'street': vals.get('street') or False,
                    'street2': vals.get('street2') or False,
                    'zip': vals.get('zip') or False,
                    'city': vals.get('city') or False,
                    'state_id': vals.get('state_id') or False,
                    'country_id': vals.get('country_id') or False,
                })
                vals['partner_id'] = partner.id
        records = super().create(vals_list)
        # Suscribir contactos
        for rec in records:
            if rec.partner_id:
                rec.message_subscribe(partner_ids=[rec.partner_id.id])
            # Si es estudiante y tiene profesor asignado con partner, suscribir al profesor como seguidor
            try:
                if rec.tipo_interno == 'estudiante' and rec.profesor_partner_id:
                    rec.message_subscribe(partner_ids=[rec.profesor_partner_id.id])
            except Exception:
                pass
            # Crear usuario vinculado si no existe y hay email (excepto si está 'no_asignado')
            if rec.tipo_interno != 'no_asignado' and not rec.user_id and rec.email and rec.partner_id:
                # Evitar abortos por login duplicado: comprobar existencia previa
                existing = self.env['res.users'].sudo().search([('login', '=', rec.email)], limit=1)
                if existing:
                    raise ValidationError("Ya existe un usuario con el email/login %s. Usa otro email o vincula la persona al usuario existente." % rec.email)
                user_vals = {
                    'name': rec.nombre_completo or rec.nombre,
                    'login': rec.email,
                    'password': 'changeme123',  # Contraseña predeterminada para todos los nuevos usuarios
                    'partner_id': rec.partner_id.id,
                    # Eliminado: no forzar cambio de contraseña en primer login
                }
                cfg = rec._get_user_group_config(rec.tipo_interno)
                target_ids = sorted(cfg['target_ids'])
                if target_ids:
                    user_vals['groups_id'] = [(6, 0, target_ids)]
                user_vals['share'] = cfg['share']
                user = self.env['res.users'].sudo().create(user_vals)
                # Preferencias de notificación adaptadas según perfil
                try:
                    if cfg['share']:
                        if rec.partner_id:
                            rec.partner_id.sudo().write({'notification_type': 'email'})
                    else:
                        try:
                            user.sudo().write({'notification_type': cfg['notification']})
                        except Exception:
                            pass
                        if rec.partner_id:
                            rec.partner_id.sudo().write({'notification_type': cfg['notification']})
                except Exception:
                    pass
                # Asegurar que el partner/usuario esté suscrito como follower para recibir mensajes
                try:
                    rec.message_subscribe(partner_ids=[user.partner_id.id])
                except Exception:
                    pass
                rec.user_id = user.id
        # Crear alias por persona de forma segura tras la creación (si procede).
        # create_person_alias ya comprueba contexto (install_mode/import_file/mass_person_create)
        for rec in records:
            try:
                rec.create_person_alias()
            except Exception as e:
                self._logger.error("[erasmus.persona] Error creando alias para persona id=%s: %s", rec.id, e)
        return records

    @api.model
    def default_get(self, fields_list):
        """Pre-carga Programa y Código Erasmus con valores globales del catálogo al abrir el formulario."""
        res = super().default_get(fields_list)
        Catalog = self.env['erasmus.codigo']
        def _get_default(key):
            rec = Catalog.search([('key', '=', key), ('ciclo_id', '=', False), ('active', '=', True)], limit=1)
            return rec.valor if rec else False
        if 'programa' in fields_list and not res.get('programa'):
            res['programa'] = _get_default('programa') or False
        if 'codigo_erasmus' in fields_list and not res.get('codigo_erasmus'):
            res['codigo_erasmus'] = _get_default('codigo_erasmus') or False
        # ISCED-F depende del ciclo; no se establece por defecto aquí
        return res

    def write(self, vals):
        self._logger.info("[erasmus.persona] WRITE ids=%s vals=%s", self.ids, vals)
        # Guardar email de vals para usarlo después de que se modifique vals
        new_email_from_vals = vals.get('email') if 'email' in vals else None
        self._logger.info("[erasmus.persona] DEBUG - Email inicial desde vals: %s", new_email_from_vals)
        # Permitir libremente elegir 'no_asignado' si el usuario lo desea (UI muestra todas las opciones)
        
        # Interceptar cambios en campos relacionados con contacto y escribir con sudo sobre res.partner
        partner_map = {
            'email': 'email',
            'movil': 'mobile',
            'street': 'street',
            'street2': 'street2',
            'zip': 'zip',
            'city': 'city',
            'state_id': 'state_id',
            'country_id': 'country_id',
            'nif': 'vat',
        }
        rel_keys_present = [k for k in partner_map.keys() if k in vals]
        if rel_keys_present:
            # Preparar actualización al partner solo si el origen NO es partner/user
            if not (self.env.context.get('from_partner') or self.env.context.get('from_user')):
                for rec in self:
                    # Asegurar partner
                    partner = rec.partner_id
                    if not partner:
                        partner = self.env['res.partner'].sudo().with_context(skip_auto_persona=True).create({'name': rec.nombre_completo or rec.nombre or 'Sin nombre'})
                        rec.partner_id = partner.id
                    upd = {}
                    for k in rel_keys_present:
                        v = vals.get(k)
                        upd[partner_map[k]] = v
                    if upd:
                        partner.sudo().with_context(skip_persona_sync=True).write(upd)
            # Quitar SIEMPRE las claves relacionadas para evitar que super().write dispare writes al partner por ser related
            vals = {k: v for k, v in vals.items() if k not in rel_keys_present}
        
        # Si se cambia el nivel a especialización, forzar limpieza en el mismo write
        if 'nivel_imparticion' in vals and vals.get('nivel_imparticion') in ('egm', 'egs'):
            vals = vals.copy()
            vals.update({
                'familia_profesional': False,
                'ciclo_formativo_id': False,
                'ciclo_formativo': False,
            })
        
        # Si ya estamos en especialización y alguien intenta asignar familia/ciclo, limpiar igualmente
        special_recs = self.filtered(lambda r: r.nivel_imparticion in ('egm', 'egs'))
        if special_recs and any(k in vals for k in ('familia_profesional', 'ciclo_formativo_id', 'ciclo_formativo')) and 'nivel_imparticion' not in vals:
            vals_clean = vals.copy()
            vals_clean.update({
                'familia_profesional': False,
                'ciclo_formativo_id': False,
                'ciclo_formativo': False,
            })
            res1 = super(ErasmusPersona, special_recs).write(vals_clean)
            res2 = super(ErasmusPersona, (self - special_recs)).write(vals)
            res = res1 and res2
        else:
            # Guardar followers previos si cambia profesor_id
            old_prof_partner = {}
            if 'profesor_id' in vals:
                for rec in self:
                    old_prof_partner[rec.id] = rec.profesor_partner_id.id if rec.profesor_partner_id else False
            res = super().write(vals)
            # Gestionar suscripciones de profesor a estudiantes tras el cambio
            if 'profesor_id' in vals:
                for rec in self:
                    if rec.tipo_interno != 'estudiante':
                        continue
                    old_pid = old_prof_partner.get(rec.id)
                    new_pid = rec.profesor_partner_id.id if rec.profesor_partner_id else False
                    try:
                        if old_pid and old_pid != new_pid:
                            rec.message_unsubscribe(partner_ids=[old_pid])
                    except Exception:
                        pass
                    try:
                        if new_pid and new_pid != old_pid:
                            rec.message_subscribe(partner_ids=[new_pid])
                    except Exception:
                        pass
        
        # Asegurar contacto si se editan related y no existe
        related_keys = {'email', 'movil', 'street', 'street2', 'zip', 'city', 'state_id', 'country_id'}
        if any(k in vals for k in related_keys):
            for rec in self:
                if not rec.partner_id:
                    partner = self.env['res.partner'].sudo().with_context(skip_auto_persona=True).create({
                        'name': rec.nombre_completo or rec.nombre or 'Sin nombre',
                        'vat': rec.nif or False,
                        'email': new_email_from_vals or rec.email or False,
                        'mobile': vals.get('movil') or False,
                        'street': vals.get('street') or False,
                        'street2': vals.get('street2') or False,
                        'zip': vals.get('zip') or False,
                        'city': vals.get('city') or False,
                        'state_id': vals.get('state_id') or False,
                        'country_id': vals.get('country_id') or False,
                    })
                    rec.partner_id = partner.id
                    rec.message_subscribe(partner_ids=[partner.id])
        
        # Sincronizar nombre completo y NIF hacia el contacto (evitar bucles)
        if not self.env.context.get('skip_partner_sync'):
            name_changed = {'nombre', 'apellido1', 'apellido2'}.intersection(vals.keys())
            nif_changed = 'nif' in vals
            if name_changed or nif_changed:
                for rec in self:
                    if rec.partner_id:
                        upd = {}
                        if name_changed:
                            upd['name'] = rec.nombre_completo or rec.nombre or rec.partner_id.name
                        if nif_changed:
                            upd['vat'] = rec.nif or False
                        if upd:
                            rec.partner_id.with_context(skip_persona_sync=True).write(upd)
        
        # Sincronizar cambios al usuario vinculado
        name_changed = {'nombre', 'apellido1', 'apellido2'}.intersection(vals.keys())
        email_changed = new_email_from_vals is not None  # Usar la variable guardada
        tipo_changed = 'tipo_interno' in vals
        self._logger.info("[erasmus.persona] DEBUG - Iniciando sync usuario: ids=%s, email_changed=%s, vals_email=%s", self.ids, email_changed, new_email_from_vals)
        for rec in self:
            if rec.user_id:
                self._logger.info("[erasmus.persona] DEBUG - Procesando usuario id=%s, login actual=%s, email_persona=%s, nombre=%s", 
                                  rec.user_id.id, rec.user_id.login, rec.email, rec.nombre_completo)
                user_upd = {}
                if name_changed:
                    user_upd['name'] = rec.nombre_completo or rec.nombre
                    self._logger.info("[erasmus.persona] DEBUG - Actualizando nombre usuario a: %s", user_upd['name'])
                if email_changed:
                    new_email = new_email_from_vals or rec.email or False
                    user_upd['login'] = new_email
                    user_upd['email'] = new_email
                    self._logger.info("[erasmus.persona] DEBUG - Intentando actualizar email/login a: %s", new_email)
                if tipo_changed:
                    new_tipo = vals['tipo_interno']
                    cfg = self._get_user_group_config(new_tipo)
                    current_group_ids = set(rec.user_id.sudo().groups_id.ids)
                    ops = []
                    for gid in cfg['managed_ids']:
                        if gid in cfg['target_ids']:
                            if gid not in current_group_ids:
                                ops.append((4, gid, 0))
                        else:
                            if gid in current_group_ids:
                                ops.append((3, gid, 0))
                    if ops:
                        user_upd['groups_id'] = ops
                    user_upd['share'] = cfg['share']
                if user_upd and not self.env.context.get('skip_user_sync'):
                    try:
                        rec.user_id.sudo().with_context(skip_persona_sync=True).write(user_upd)
                        self._logger.info("[erasmus.persona] DEBUG - Actualización usuario exitosa: %s", user_upd)
                    except Exception as e:
                        self._logger.error("[erasmus.persona] DEBUG - Error al actualizar usuario id=%s: %s", rec.user_id.id, str(e))  
                # Ajustar preferencias de notificación cuando cambia el tipo y ya existe usuario
                if tipo_changed:
                    try:
                        if cfg['share']:
                            if rec.partner_id:
                                rec.partner_id.sudo().write({'notification_type': 'email'})
                        else:
                            try:
                                rec.user_id.sudo().write({'notification_type': cfg['notification']})
                            except Exception:
                                pass
                            if rec.partner_id:
                                rec.partner_id.sudo().write({'notification_type': cfg['notification']})
                    except Exception:
                        pass
            # Si cambia el tipo desde 'no_asignado' a uno asignado y no hay usuario aún, créalo
            if tipo_changed and not rec.user_id and rec.tipo_interno and rec.tipo_interno != 'no_asignado' and rec.email and rec.partner_id:
                try:
                    cfg = rec._get_user_group_config(rec.tipo_interno)
                    # Evitar abortos por login duplicado
                    existing = self.env['res.users'].sudo().search([('login', '=', rec.email)], limit=1)
                    if existing:
                        raise ValidationError("Ya existe un usuario con el email/login %s. Usa otro email o vincula la persona al usuario existente." % rec.email)
                    uvals = {
                        'name': rec.nombre_completo or rec.nombre,
                        'login': rec.email,
                        'email': rec.email,
                        'password': 'changeme123',
                        'partner_id': rec.partner_id.id,
                        # Eliminado: no forzar cambio de contraseña en primer acceso
                    }
                    target_ids = sorted(cfg['target_ids'])
                    if target_ids:
                        uvals['groups_id'] = [(6, 0, target_ids)]
                    uvals['share'] = cfg['share']
                    user = self.env['res.users'].sudo().create(uvals)
                    # Notificaciones según tipo: internos en bandeja, estudiantes por email
                    try:
                        if cfg['share']:
                            if rec.partner_id:
                                rec.partner_id.sudo().write({'notification_type': 'email'})
                        else:
                            try:
                                user.sudo().write({'notification_type': cfg['notification']})
                            except Exception:
                                pass
                            if rec.partner_id:
                                rec.partner_id.sudo().write({'notification_type': cfg['notification']})
                    except Exception:
                        pass
                    try:
                        rec.message_subscribe(partner_ids=[user.partner_id.id])
                    except Exception:
                        pass
                    rec.user_id = user.id
                except Exception as e:
                    self._logger.error('[erasmus.persona] Error creando usuario tras cambio de tipo: %s', e)
        # Cascada de archivado/desarchivado a usuario y contacto vinculados (usuario primero)
        if 'active' in vals:
            new_active = bool(vals.get('active'))
            for rec in self:
                # 1) Usuario primero (para asegurar que se deshabilita el acceso inmediatamente)
                if rec.user_id:
                    try:
                        rec.user_id.sudo().with_context(skip_persona_sync=True).write({'active': new_active})
                    except Exception:
                        pass
                # 2) Contacto después
                if rec.partner_id and not self.env.context.get('skip_partner_back_write'):
                    try:
                        rec.partner_id.sudo().with_context(skip_partner_active_cascade=True).write({'active': new_active})
                    except Exception:
                        pass
        return res

    def create_person_alias(self):
        """Crear alias seguro para UNA persona.
        Reglas:
        - No crear durante install/import/mass_person_create.
        - No crear si alias_id ya existe.
        - Alias: persona<ID>
        - alias_model_id apunta a erasmus.persona
        - alias_force_thread_id = self.id
        """
        self.ensure_one()
        # Evitar creación durante instalación o import masivo
        if self.env.context.get('install_mode') or self.env.context.get('import_file') or self.env.context.get('mass_person_create'):
            return False
        # Si ya tiene alias, nada que hacer
        if self.alias_id:
            return True
        model_rec = self.env['ir.model']._get('erasmus.persona')
        model_id = model_rec.id
        # Valores base para alias por hilo (thread alias)
        vals = {
            'alias_name': f"persona{self.id}",
            'alias_model_id': model_id,
            'alias_force_thread_id': self.id,
            'alias_defaults': {},
        }
        # Añadir claves opcionales si existen en esta versión de Odoo (compatibilidad hacia atrás)
        alias_fields = self.env['mail.alias']._fields
        if 'alias_parent_model_id' in alias_fields:
            vals['alias_parent_model_id'] = model_id
        if 'alias_parent_thread_id' in alias_fields:
            vals['alias_parent_thread_id'] = self.id
        if 'alias_user_id' in alias_fields:
            vals['alias_user_id'] = False
        alias = self.env['mail.alias'].sudo().create(vals)
        # Asignar en modo sudo para evitar restricciones
        self.sudo().write({'alias_id': alias.id})
        return True

    def _message_get_reply_to(self, default=None):
        """
        Reply-To debe ser el correo real para que las respuestas lleguen a Gmail
        y Odoo las recoja vía IMAP. NO usar alias porque el dominio no existe.
        """
        self.ensure_one()
        # Priorizar el correo del servidor "Gmail Estudiantes" configurado
        reply_email = self._get_gmail_estudiantes_email()
        if reply_email:
            return reply_email
        # Luego el email del registro si es válido
        if self.email and '@' in self.email:
            return self.email
        # Fallback general
        return super(ErasmusPersona, self)._message_get_reply_to(default=default)

    def message_post(self, **kwargs):
        """Forzar reply_to al correo del usuario actual (Gmail real) ignorando alias.
        Esto evita que el sistema use el alias catchall y asegura que las respuestas vuelvan
        al buzón IMAP configurado y se encadenen por In-Reply-To.
        Prioridad:
        1. env.user.email
        2. kwargs.get('email_from') si parece válido
        3. company.email
        4. fallback al super (sin forzar)
        """
        # Priorizar el servidor "Gmail Estudiantes" si está configurado
        estudiantes_email = self._get_gmail_estudiantes_email()
        if estudiantes_email:
            kwargs['reply_to'] = estudiantes_email
        else:
            user_email = (self.env.user.email or '').strip()
            if user_email and '@' in user_email:
                kwargs['reply_to'] = user_email
            else:
                email_from = (kwargs.get('email_from') or '').strip()
                if email_from and '@' in email_from:
                    kwargs['reply_to'] = email_from
                else:
                    company_email = (self.env.company.email or '').strip()
                    if company_email and '@' in company_email:
                        kwargs['reply_to'] = company_email
        return super(ErasmusPersona, self).message_post(**kwargs)

    def _get_gmail_estudiantes_email(self):
        """Localiza el correo (usuario) del servidor llamado exactamente 'Gmail Estudiantes'.
        Busca primero en servidores de salida (ir.mail_server -> smtp_user) y luego en
        servidores de entrada (fetchmail.server -> user). Devuelve un email válido o False.
        """
        MailServer = self.env['ir.mail_server'].sudo()
        server = MailServer.search([('name', '=', 'Gmail Estudiantes'), ('active', '=', True)], limit=1)
        email = False
        if server and server.smtp_user and '@' in server.smtp_user:
            email = server.smtp_user.strip()
        if not email:
            FetchServer = self.env['fetchmail.server'].sudo()
            fserver = FetchServer.search([('name', '=', 'Gmail Estudiantes'), ('active', '=', True)], limit=1)
            if fserver and fserver.user and '@' in fserver.user:
                email = fserver.user.strip()
        return email if email and '@' in email else False
    
    def unlink(self):
        partners = self.mapped('partner_id')
        users = self.mapped('user_id')
        res = super().unlink()
        for user in users:
            if user:
                try:
                    user.sudo().unlink()
                except Exception:
                    pass
        for partner in partners:
            if not self.env['erasmus.persona'].search_count([('partner_id', '=', partner.id)]):
                try:
                    partner.sudo().unlink()
                except Exception:
                    pass
        return res

    def read(self, fields=None, load='_classic_read'):
        # Log requested fields and resulting street values for debugging reloads
        self._logger.info("[erasmus.persona] READ ids=%s fields=%s", self.ids, fields)
        res = super().read(fields=fields, load=load)
        try:
            # Only log a small sample to avoid noise
            for r in res[:10]:
                self._logger.info("[erasmus.persona] AFTER READ id=%s street=%s", r.get('id'), r.get('street'))
        except Exception:
            pass
        return res

    @api.depends('nombre', 'apellido1', 'apellido2')
    def _compute_nombre_completo(self):
        for rec in self:
            parts = [p for p in [rec.nombre, rec.apellido1, rec.apellido2] if p]
            rec.nombre_completo = ' '.join(parts)

    # Helpers para saber tipo (posible utilidad futura en dominios / vistas)
    es_estudiante = fields.Boolean(compute='_compute_tipo_flags')
    es_profesor = fields.Boolean(compute='_compute_tipo_flags')
    es_acompaniante = fields.Boolean(compute='_compute_tipo_flags')

    def _compute_tipo_flags(self):
        for rec in self:
            rec.es_estudiante = rec.tipo_interno == 'estudiante'
            rec.es_profesor = rec.tipo_interno == 'profesor'
            rec.es_acompaniante = rec.tipo_interno == 'acompaniante'

    # Name get para mostrar siempre el nombre completo coherente
    def name_get(self):
        result = []
        for rec in self:
            display = rec.nombre_completo or rec.nombre or str(rec.id)
            if rec.tipo_interno:
                display = f"[{rec.tipo_interno.capitalize()}] {display}"
            result.append((rec.id, display))
        return result

    # Movilidades vinculadas
    movilidad_ids = fields.One2many('erasmus.movilidad', 'persona_id', string='Movilidades')

    @api.onchange('tipo_interno')
    def _onchange_tipo_interno(self):
        """When switching type, clear fields not applicable to keep data consistent.
        - profesor: no idiomas, no bloque profesor coordinador
        - estudiante: no antiguedad_educacion
        - acompaniante: no idiomas, no profesor coordinador, no antiguedad
        """
        for rec in self:
            self._logger.info("[onchange tipo_interno] id=%s new=%s", rec.id or '(new)', rec.tipo_interno)
            self._logger.info(
                "[onchange tipo_interno] flags -> nac=%s ant=%s idi=%s coord=%s",
                rec.show_nacionalidad, rec.show_antiguedad, rec.show_idiomas, rec.show_profesor_coord
            )
            if rec.tipo_interno == 'profesor':
                # Clear student-only fields
                rec.nivel_ingles = False
                rec.nivel_frances = False
                rec.nivel_aleman = False
                rec.profesor_coordinador_nombre = False
                rec.profesor_coordinador_apellido1 = False
                rec.profesor_coordinador_apellido2 = False
                rec.profesor_coordinador_email = False
                rec.profesor_coordinador_telefono = False
            elif rec.tipo_interno == 'estudiante':
                # Clear professor-only fields
                rec.antiguedad_educacion = False
            elif rec.tipo_interno == 'acompaniante':
                # Clear both student/professor specific fields
                rec.nivel_ingles = False
                rec.nivel_frances = False
                rec.nivel_aleman = False
                rec.profesor_coordinador_nombre = False
                rec.profesor_coordinador_apellido1 = False
                rec.profesor_coordinador_apellido2 = False
                rec.profesor_coordinador_email = False
                rec.profesor_coordinador_telefono = False
                rec.antiguedad_educacion = False

    

    # RPC helper para resolver país y estado por nombre (para el widget JS)
    @api.model
    def resolve_address(self, country_code=None, state_name=None, country_name=None):
        """Resolve country and state IDs robustly.
        Args:
        - country_code: ISO alpha-2 (e.g., 'ES') if available
        - state_name: province/state name or code from Nominatim
        - country_name: fallback full country name (e.g., 'Spain', 'España')
        """
        country_id = False
        state_id = False
        Country = self.env['res.country']
        State = self.env['res.country.state']

        # Country resolution: prefer code; fallback to name
        cc = (country_code or '').strip().upper()
        cn = (country_name or '').strip()
        country = False
        if cc:
            country = Country.search([('code', '=', cc)], limit=1)
        if not country and cn:
            country = Country.search([('name', 'ilike', cn)], limit=1)
        country_id = country.id or False

        # State/province resolution within the country
        if state_name and country_id:
            val = (state_name or '').strip()
            # Helper: normalize for alias matching (lowercase, remove accents)
            def _norm(s):
                try:
                    return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn').lower()
                except Exception:
                    return (s or '').lower()
            state = State.search([
                ('country_id', '=', country_id),
                '|', ('code', '=', val.upper()), ('name', 'ilike', val)
            ], limit=1)
            # Aliases for Spain to cope with bilingual/diacritic variants
            if not state and cc == 'ES':
                aliases = {
                    # Euskadi
                    'gipuzkoa': {'code': 'SS', 'name': 'Guipúzcoa'},
                    'guipuzcoa': {'code': 'SS', 'name': 'Guipúzcoa'},
                    'bizkaia': {'code': 'BI', 'name': 'Vizcaya'},
                    'vizcaya': {'code': 'BI', 'name': 'Vizcaya'},
                    'araba': {'code': 'VI', 'name': 'Álava'},
                    'alava': {'code': 'VI', 'name': 'Álava'},
                    # Catalunya
                    'girona': {'code': 'GI', 'name': 'Gerona'},
                    'gerona': {'code': 'GI', 'name': 'Gerona'},
                    'lleida': {'code': 'L', 'name': 'Lérida'},
                    'lerida': {'code': 'L', 'name': 'Lérida'},
                    'tarragona': {'code': 'T', 'name': 'Tarragona'},
                    'barcelona': {'code': 'B', 'name': 'Barcelona'},
                    # Valencia / València
                    'castello': {'code': 'CS', 'name': 'Castellón'},
                    'castellon': {'code': 'CS', 'name': 'Castellón'},
                    'valencia': {'code': 'V', 'name': 'Valencia'},
                    'alacant': {'code': 'A', 'name': 'Alicante'},
                    'alicante': {'code': 'A', 'name': 'Alicante'},
                    # Galicia
                    'a coruna': {'code': 'C', 'name': 'A Coruña'},
                    'la coruna': {'code': 'C', 'name': 'A Coruña'},
                    'coruna': {'code': 'C', 'name': 'A Coruña'},
                    'ourense': {'code': 'OR', 'name': 'Ourense'},
                    'orense': {'code': 'OR', 'name': 'Ourense'},
                    'pontevedra': {'code': 'PO', 'name': 'Pontevedra'},
                    'lugo': {'code': 'LU', 'name': 'Lugo'},
                    # Illes Balears
                    'illes balears': {'code': 'PM', 'name': 'Islas Baleares'},
                    'islas baleares': {'code': 'PM', 'name': 'Islas Baleares'},
                    # Navarra
                    'nafarroa': {'code': 'NA', 'name': 'Navarra'},
                    'navarra': {'code': 'NA', 'name': 'Navarra'},
                }
                key = _norm(val)
                alias = aliases.get(key)
                if alias:
                    state = State.search([
                        ('country_id', '=', country_id),
                        '|', ('code', '=', alias['code']), ('name', 'ilike', alias['name'])
                    ], limit=1)
                state_id = state.id or False

        return {'country_id': country_id, 'state_id': state_id}

    # ----------------------------
    # ONCHANGE dinámicos de filtro
    # ----------------------------

    @api.onchange('nivel_imparticion')
    def _onchange_nivel_imparticion(self):
        """Ajusta los valores visibles/permitidos en función del nivel.
        NOTA: 'familia_profesional' y 'ciclo_formativo' son campos Selection; los dominios no aplican.
        Por eso aquí forzamos valores coherentes y limpiamos los inválidos para evitar combinaciones inconsistentes.
        """
        """Ajusta por nivel: limpia ciclos si el nivel no coincide."""
        for rec in self:
            self._logger.info("[onchange nivel_imparticion] id=%s nivel=%s before fam=%s ciclo_id=%s ciclo=%s", rec.id or '(new)', rec.nivel_imparticion, rec.familia_profesional, bool(rec.ciclo_formativo_id), rec.ciclo_formativo)
            # Si el ciclo seleccionado no pertenece al nivel actual, limpiar selección
            if rec.ciclo_formativo_id and rec.ciclo_formativo_id.nivel and rec.ciclo_formativo_id.nivel != rec.nivel_imparticion:
                rec.ciclo_formativo_id = False
                rec.ciclo_formativo = False
            # Si es una especialización, limpiar familia y ciclo y dejar los selects desactivados por vista
            if rec.nivel_imparticion in ('egm', 'egs'):
                rec.familia_profesional = False
                rec.ciclo_formativo_id = False
                rec.ciclo_formativo = False
            self._logger.info("[onchange nivel_imparticion] after fam=%s ciclo_id=%s ciclo=%s", rec.familia_profesional, bool(rec.ciclo_formativo_id), rec.ciclo_formativo)


    @api.onchange('familia_profesional')
    def _onchange_familia_profesional(self):
        """Ajusta el ciclo_formativo permitido según la familia profesional.
        Al ser Selection, no podemos aplicar dominio real; en su lugar, validamos y corregimos el valor.
        """
        allowed_by_family = {
            'informatica': ['smr', 'asir', 'dam', 'daw'],
            'administracion': ['gestion_admin', 'admin_finanzas'],
            'comercio': ['comercio_internacional', 'transporte_logistica'],
            'transporte': ['conduccion_transportes'],
            'sanidad': ['aux_enfermeria', 'farmacia', 'laboratorio', 'dietetica'],
            'servicios': ['integracion', 'educacion_infantil', 'dependencia'],
        }
        for rec in self:
            if not rec.familia_profesional:
                rec.ciclo_formativo = False
                rec.ciclo_formativo_id = False
                continue
            allowed = allowed_by_family.get(rec.familia_profesional, [])
            if rec.ciclo_formativo not in allowed:
                rec.ciclo_formativo = False
            # Ajustar Many2one según familia/domino
            if rec.ciclo_formativo:
                ciclo = self.env['erasmus.ciclo'].search([('code', '=', rec.ciclo_formativo)], limit=1)
                rec.ciclo_formativo_id = ciclo.id if ciclo and ciclo.familia_profesional == rec.familia_profesional else False
            else:
                rec.ciclo_formativo_id = False

    @api.onchange('ciclo_formativo_id')
    def _onchange_ciclo_formativo_id(self):
        """Sincroniza el Selection 'ciclo_formativo' con el Many2one elegido y valida la familia."""
        for rec in self:
            if rec.ciclo_formativo_id:
                # Si la familia no coincide con el dominio, ajustamos familia al del ciclo seleccionado
                if rec.familia_profesional and rec.ciclo_formativo_id.familia_profesional != rec.familia_profesional:
                    rec.familia_profesional = rec.ciclo_formativo_id.familia_profesional
                rec.ciclo_formativo = rec.ciclo_formativo_id.code
            else:
                rec.ciclo_formativo = False
        # Recalcular códigos en cliente al cambiar de ciclo
        self._compute_codigos()

    @api.onchange('profesor_id')
    def _onchange_profesor_id_fill_coordinator(self):
        """Al asignar un profesor, no copiar datos al bloque de 'Profesor Coordinador'.
        Petición: que la selección sirva solo para vincular (profesor asignado) y no auto-rellene nada.
        """
        # Intencionadamente no modificamos los campos de coordinador.
        # Si en el futuro se quiere limpiar esos campos al cambiar el profesor, se podría hacer aquí,
        # pero por ahora respetamos cualquier dato introducido manualmente.
        return

    def _get_codigo_catalogo(self, key, ciclo):
        """Obtiene el código desde el catálogo, priorizando por ciclo y con fallback global.
        key: 'programa' | 'codigo_erasmus' | 'codigo_iscedf'
        ciclo: erasmus.ciclo record or False
        """
        Catalog = self.env['erasmus.codigo']
        rec = False
        if ciclo:
            rec = Catalog.search([('key', '=', key), ('ciclo_id', '=', ciclo.id), ('active', '=', True)], limit=1)
        if not rec:
            rec = Catalog.search([('key', '=', key), ('ciclo_id', '=', False), ('active', '=', True)], limit=1)
        return rec.valor if rec else False

    @api.depends('ciclo_formativo_id')
    def _compute_codigos(self):
        for rec in self:
            ciclo = rec.ciclo_formativo_id
            rec.programa = rec._get_codigo_catalogo('programa', ciclo) or False
            rec.codigo_erasmus = rec._get_codigo_catalogo('codigo_erasmus', ciclo) or False
            rec.codigo_iscedf = rec._get_codigo_catalogo('codigo_iscedf', ciclo) or False

    @api.onchange('requiere_explicacion')
    def _onchange_requiere_explicacion(self):
        """Si el nivel implica especialización, limpimos familia y ciclo para evitar valores residuales."""
        for rec in self:
            if rec.requiere_explicacion:
                self._logger.info("[onchange requiere_explicacion] cleaning fam/ciclo due to specialization. id=%s", rec.id or '(new)')
                rec.familia_profesional = False
                rec.ciclo_formativo_id = False
                rec.ciclo_formativo = False

