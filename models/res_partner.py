# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    erasmus_persona_id = fields.Many2one('erasmus.persona', string='Persona Erasmus Vinculada', readonly=True)



class ResPartner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        # PRE: Cascada de archivado hacia persona/usuario (usuario primero) si cambia active en contacto
        if 'active' in vals and not self.env.context.get('skip_partner_active_cascade'):
            new_active = bool(vals.get('active'))
            personas = self.env['erasmus.persona'].with_context(active_test=False).sudo().search([('partner_id', 'in', self.ids)])
            if personas:
                try:
                    # Evitar que persona.write reescriba el partner durante este write
                    personas.sudo().with_context(skip_partner_back_write=True).write({'active': new_active})
                except Exception:
                    pass
        res = super().write(vals)
        # Sincronizar cambios a persona salvo que venga con flag para evitar bucles
        if not self.env.context.get('skip_persona_sync'):
            # Considerar más claves: name, vat, email, mobile, y dirección
            keys = {'name', 'vat', 'email', 'mobile', 'street', 'street2', 'zip', 'city', 'state_id', 'country_id'}
            if any(k in vals for k in keys):
                personas = self.env['erasmus.persona'].search([('partner_id', 'in', self.ids)])
                for persona in personas:
                    updates = {}
                    if 'name' in vals and vals.get('name'):
                        parts = (vals['name'] or '').split()
                        if parts:
                            updates['nombre'] = parts[0]
                            updates['apellido1'] = parts[-1] if len(parts) > 1 else False
                            updates['apellido2'] = ' '.join(parts[1:-1]) if len(parts) > 2 else False
                    if 'vat' in vals:
                        updates['nif'] = vals.get('vat') or False
                    if 'email' in vals:
                        updates['email'] = vals.get('email') or False
                    if 'mobile' in vals:
                        updates['movil'] = vals.get('mobile') or False
                    for k in ('street', 'street2', 'zip', 'city', 'state_id', 'country_id'):
                        if k in vals:
                            updates[k] = vals.get(k) or False
                    if updates:
                        # from_partner: evitar que persona.write vuelva a escribir partner
                        # skip_user_sync=False para que actualice usuario si aplica (email/nombre)
                        persona.with_context(skip_partner_sync=True, from_partner=True).write(updates)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # Evitar auto-creación si viene desde erasmus.persona
        if self.env.context.get('skip_auto_persona'):
            return records
        Persona = self.env['erasmus.persona']
        for partner in records:
            try:
                # No duplicar si ya hay vinculada
                existing = Persona.search([('partner_id', '=', partner.id)], limit=1)
                if existing:
                    partner.erasmus_persona_id = existing.id
                    continue
                name = (partner.name or '').strip()
                parts = name.split()
                # Crear persona mínima y evitar escribir campos relacionados (email/móvil/dirección)
                # para no disparar partner.write durante partner.create
                persona = Persona.sudo().create({
                    'tipo_interno': 'no_asignado',
                    'partner_id': partner.id,
                    'nombre': parts[0] if parts else False,
                    'apellido1': parts[-1] if len(parts) > 1 else False,
                    'apellido2': ' '.join(parts[1:-1]) if len(parts) > 2 else False,
                    # nif/email/móvil/dirección se reflejarán vía campos related sin escribir de nuevo el partner
                })
                partner.erasmus_persona_id = persona.id
            except Exception:
                # No bloquear creación de partner por errores no críticos
                continue
        return records

    def action_open_or_create_persona(self):
        self.ensure_one()
        Persona = self.env['erasmus.persona'].with_context(active_test=False)
        persona = Persona.search([('partner_id', '=', self.id)], limit=1)
        if not persona:
            name = (self.name or '').strip()
            parts = name.split()
            persona = Persona.sudo().create({
                'tipo_interno': 'no_asignado',
                'partner_id': self.id,
                'nombre': parts[0] if parts else False,
                'apellido1': parts[-1] if len(parts) > 1 else False,
                'apellido2': ' '.join(parts[1:-1]) if len(parts) > 2 else False,
            })
            self.erasmus_persona_id = persona.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Persona Erasmus',
            'res_model': 'erasmus.persona',
            'view_mode': 'form',
            'res_id': persona.id,
            'target': 'current',
        }


