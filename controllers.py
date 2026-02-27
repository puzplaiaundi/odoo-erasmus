
# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response
import requests
import json


class GestionErasmusController(http.Controller):
	@http.route('/gestion_erasmus/nominatim', type='http', auth='user', csrf=False)
	def nominatim_proxy(self, q=None, limit=5, **kw):
		"""Same-origin proxy for Nominatim search to avoid CSP/CORS issues in the web client.

		Usage: GET /gestion_erasmus/nominatim?q=calle%20...
		Returns: JSON array as provided by Nominatim (format=json&addressdetails=1)
		"""
		try:
			limit = int(limit or 5)
		except Exception:
			limit = 5
		if not q or len(q) < 3:
			return Response(json.dumps([]), content_type='application/json;charset=utf-8')

		try:
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


class ErasmusPortalController(http.Controller):
	def _get_current_persona(self):
		user = request.env.user
		Persona = request.env['erasmus.persona']
		persona = Persona.search([('partner_id', '=', user.partner_id.id)], limit=1)
		return persona

	@http.route(['/my/erasmus'], type='http', auth='user', website=True)
	def my_erasmus_home(self, **kw):
		persona = self._get_current_persona()
		if not persona:
			return request.render('gestion_erasmus.portal_student_empty', {})
		movilidad = request.env['erasmus.movilidad'].search([('persona_id', '=', persona.id)], order='id desc', limit=1)
		flash = request.session.pop('erasmus_flash', None)
		values = {'persona': persona, 'movilidad': movilidad, 'flash': flash}
		return request.render('gestion_erasmus.portal_student_home', values)

	@http.route(['/my/erasmus/save'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
	def my_erasmus_save(self, **post):
		import base64
		persona = self._get_current_persona()
		if not persona:
			return request.redirect('/my/erasmus')
		allowed_persona_fields = ['street', 'street2', 'city', 'zip', 'movil']
		vals_p = {}
		for f in allowed_persona_fields:
			if f in post:
				vals_p[f] = post.get(f) or False
		if vals_p:
			try:
				persona.write(vals_p)
			except Exception:
				pass
		Mov = request.env['erasmus.movilidad']
		movilidad = Mov.search([('persona_id', '=', persona.id)], order='id desc', limit=1)
		if not movilidad:
			try:
				movilidad = Mov.create({'persona_id': persona.id, 'tipo_interno': 'estudiante'})
			except Exception:
				movilidad = Mov
		files_map = {
			'dni': 'dni', 'dni2': 'dni2', 'cert_titularidad_bancaria': 'cert_titularidad_bancaria',
			'curriculum_ingles': 'curriculum_ingles', 'carta_presentacion_ingles': 'carta_presentacion_ingles',
			'certificado_1': 'certificado_1', 'certificado_2': 'certificado_2', 'certificado_3': 'certificado_3',
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
		request.session['erasmus_flash'] = 'Tus cambios se han guardado correctamente.'
		return request.redirect('/my/erasmus')
