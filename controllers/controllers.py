# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response
import werkzeug

import json
import logging

_logger = logging.getLogger(__name__)


class GestionErasmusController(http.Controller):
	@http.route('/gestion_erasmus/nominatim', type='http', auth='user', csrf=False)
	def nominatim_proxy(self, q=None, limit=5, **kw):
		"""Same-origin proxy for Nominatim search to avoid CSP/CORS issues in the web client.

		Usage: GET /gestion_erasmus/nominatim?q=calle%20...
		Returns: JSON array as provided by Nominatim (format=json&addressdetails=1)
		"""
		# Basic validation
		try:
			limit = int(limit or 5)
		except Exception:
			limit = 5
		if not q or len(q) < 3:
			return Response(json.dumps([]), content_type='application/json;charset=utf-8')
		# Perform upstream request
		try:
			import requests
			accept_language = kw.get('accept-language') or kw.get('accept_language')
			countrycodes = kw.get('countrycodes')
			params = {
				'format': 'json',
				'addressdetails': 1,
				'limit': limit,
				'q': q,
			}
			if accept_language:
				params['accept-language'] = accept_language
			if countrycodes:
				params['countrycodes'] = countrycodes
			headers = {
				'Accept': 'application/json',
				'User-Agent': 'odoo-gestion-erasmus/1.0 (+https://www.odoo.com)',
			}
			r = requests.get('https://nominatim.openstreetmap.org/search', params=params, headers=headers, timeout=5)
			r.raise_for_status()
			return Response(r.content, content_type='application/json;charset=utf-8')
		except Exception:
			return Response(json.dumps([]), content_type='application/json;charset=utf-8')

	@http.route('/gestion_erasmus/logo', type='http', auth='public', csrf=False)
	def module_logo(self, **kw):
		from odoo.modules.module import get_module_resource
		import mimetypes
		path = get_module_resource('gestion_erasmus', 'static', 'img', 'iconoplaiaundi.jpg')
		if not path:
			return Response(status=404)
		try:
			with open(path, 'rb') as f:
				data = f.read()
			ctype = mimetypes.guess_type(path)[0] or 'image/jpeg'
			return Response(data, content_type=ctype)
		except Exception:
			return Response(status=404)

	@http.route('/gestion_erasmus/contrato_pdf/<int:persona_id>', type='http', auth='user', csrf=False)
	def contrato_pdf(self, persona_id, **kw):
		"""Genera PDF rellenando campos AcroForm del PDF base.
		Campos: nombre_apellido, direccion_completa
		Ubicación: gestion_erasmus/static/src/pdf/contrato_template.pdf
		"""
		Persona = request.env['erasmus.persona']
		persona_sudo = Persona.sudo().browse(persona_id)
		if not persona_sudo.exists():
			return Response('Persona no encontrada', status=404)
		user = request.env.user
		is_internal = user.has_group('base.group_user')
		if not is_internal:
			try:
				Persona.check_access_rights('read')
				Persona.check_access_rule(persona_id)
				persona = Persona.browse(persona_id)
				_ = persona.nombre
			except Exception:
				return Response('Acceso denegado', status=403)
		from odoo.modules.module import get_module_resource
		pdf_path = get_module_resource('gestion_erasmus', 'static', 'src', 'pdf', 'contrato_template.pdf')
		if not pdf_path:
			return Response('Plantilla PDF no encontrada', status=404)
		nombre_apellido = persona_sudo.nombre_completo or (
			((persona_sudo.nombre or '') + ' ' + (persona_sudo.apellido1 or '') + ((' ' + persona_sudo.apellido2) if persona_sudo.apellido2 else '')).strip()
		)
		dir_parts = [p for p in [persona_sudo.street or '', persona_sudo.street2 or '', persona_sudo.zip or '', persona_sudo.city or '', persona_sudo.state_id.name or '', persona_sudo.country_id.name or ''] if p]
		direccion_completa = ', '.join(dir_parts)
		data_map = {
			'nombre_apellido': nombre_apellido or '',
			'direccion_completa': direccion_completa or ''
		}
		try:
			from pdfrw import PdfReader, PdfWriter, PdfString, PdfDict, PdfName
			import io, re, unicodedata

			def _norm(s):
				try:
					s = unicodedata.normalize('NFKD', s)
					s = s.encode('ascii', 'ignore').decode('ascii')
					s = s.lower().replace(' ', '_')
					s = re.sub(r'[^a-z0-9_]', '', s)
					return s
				except Exception:
					return (s or '').lower()

			pdf = PdfReader(pdf_path)
			field_names = []
			# Forzar apariencias
			if getattr(pdf, 'Root', None) and getattr(pdf.Root, 'AcroForm', None):
				pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfString('true')))
				# Recolectar campos del árbol de AcroForm
				def _collect_fields(fields, acc):
					for f in fields or []:
						name = None
						try:
							name = f.T.to_unicode() if getattr(f, 'T', None) else None
						except Exception:
							name = None
						if name:
							acc.append(name)
						# Fill here as well if matches
						if name and _norm(name) in (_norm(k) for k in data_map.keys()):
							val = data_map[[k for k in data_map.keys() if _norm(k) == _norm(name)][0]]
							f.update(PdfDict(V=PdfString.encode(val), DV=PdfString.encode(val)))
						kids = getattr(f, 'Kids', None)
						if kids:
							_collect_fields(kids, acc)
				_collect_fields(getattr(pdf.Root.AcroForm, 'Fields', None), field_names)

			# También intentar sobre las anotaciones por página
			for page in pdf.pages:
				annots = getattr(page, 'Annots', None)
				if not annots:
					continue
				for annot in annots:
					try:
						name = (getattr(annot, 'T', None) or '').to_unicode() if getattr(annot, 'T', None) else None
						if name and name not in field_names:
							field_names.append(name)
						# Matching por nombre normalizado
						for key, value in data_map.items():
							if _norm(key) == _norm(name):
								annot.update(PdfDict(V=PdfString.encode(value), DV=PdfString.encode(value)))
					except Exception:
						continue

			# Log de diagnóstico (solo en servidor) con los nombres detectados
			try:
				_logger.info('AcroForm fields detectados en contrato_template.pdf: %s', field_names)
			except Exception:
				pass

			# Modo depuración opcional: devolver nombres de campos en JSON
			if request.params.get('debug') == '1':
				return Response(json.dumps({'fields': field_names}), content_type='application/json;charset=utf-8')

			buf = io.BytesIO()
			PdfWriter().write(buf, pdf)
			payload = buf.getvalue()
			filename = (persona_sudo.nombre_completo or 'persona') + '_contrato.pdf'
			headers = [('Content-Type', 'application/pdf'), ('Content-Disposition', f'attachment; filename="{filename}"')]
			return Response(payload, headers=headers)
		except Exception:
			return Response('Error generando PDF', status=500)


		# Eliminado: controladores de forzar cambio de contraseña en login


	# ---------------------------
	# Portal para Estudiantes
	# ---------------------------


class ErasmusPortalController(http.Controller):
		def _get_current_persona(self):
			user = request.env.user
			Persona = request.env['erasmus.persona']
			# Buscar la persona vinculada al partner del usuario
			persona = Persona.search([('partner_id', '=', user.partner_id.id)], limit=1)
			return persona

		@http.route(['/my/erasmus'], type='http', auth='user', website=True)
		def my_erasmus_home(self, **kw):
			persona = self._get_current_persona()
			if not persona:
				# Si no hay persona vinculada, mostrar mensaje simple
				return request.render('gestion_erasmus.portal_student_empty', {})

			# Movilidad principal (si no existe, no pasa nada; el usuario podrá crearla)
			movilidad = request.env['erasmus.movilidad'].search([('persona_id', '=', persona.id)], order='id desc', limit=1)
			# Flash message desde la sesión (si existe)
			flash = request.session.pop('erasmus_flash', None)
			values = {
				'persona': persona,
				'movilidad': movilidad,
				'flash': flash,
			}
			return request.render('gestion_erasmus.portal_student_home', values)

		@http.route(['/my/erasmus/save'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
		def my_erasmus_save(self, **post):
			import base64
			persona = self._get_current_persona()
			if not persona:
				return request.redirect('/my/erasmus')

			# Actualizar datos básicos permitidos
			allowed_persona_fields = ['street', 'street2', 'city', 'zip', 'movil']
			vals_p = {}
			for f in allowed_persona_fields:
				if f in post:
					vals_p[f] = post.get(f) or False
			if vals_p:
				# No usar sudo: reglas portal permiten escribir su propia ficha
				try:
					persona.write(vals_p)
				except Exception:
					pass

			# Asegurar que hay una movilidad para subir documentos
			Mov = request.env['erasmus.movilidad']
			movilidad = Mov.search([('persona_id', '=', persona.id)], order='id desc', limit=1)
			if not movilidad:
				try:
					movilidad = Mov.create({'persona_id': persona.id, 'tipo_interno': 'estudiante'})
				except Exception:
					movilidad = Mov

			# Subida de documentos (si hay movilidad)
			files_map = {
				'dni': 'dni',
				'dni2': 'dni2',
				'cert_titularidad_bancaria': 'cert_titularidad_bancaria',
				'curriculum_ingles': 'curriculum_ingles',
				'carta_presentacion_ingles': 'carta_presentacion_ingles',
				'certificado_1': 'certificado_1',
				'certificado_2': 'certificado_2',
				'certificado_3': 'certificado_3',
			}
			if hasattr(request.httprequest, 'files') and movilidad and movilidad._name == 'erasmus.movilidad':
				uploads = request.httprequest.files
				upd = {}
				for form_key, field_name in files_map.items():
					f = uploads.get(form_key)
					if f and f.filename:
						try:
							data = base64.b64encode(f.read())
							upd[field_name] = data
							# también rellenar filename auxiliar si existe el campo *_filename
							fn_field = f"{field_name}_filename"
							if fn_field in movilidad._fields:
								upd[fn_field] = f.filename
						except Exception:
							continue
				if upd:
					try:
						movilidad.write(upd)
					except Exception:
						pass

			# Mensaje de confirmación genérico
			request.session['erasmus_flash'] = 'Tus cambios se han guardado correctamente.'
			return request.redirect('/my/erasmus')

