# -*- coding: utf-8 -*-
from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _sync_persona_partner_from_user_write(self, vals):
        if self.env.context.get('skip_persona_sync'):
            return
        for user in self:
            partner = user.partner_id
            if not partner:
                continue
            upd_partner = {}
            if 'name' in vals:
                upd_partner['name'] = vals.get('name') or user.name
            new_email = None
            if 'login' in vals:
                new_email = vals.get('login')
            elif 'email' in vals:
                new_email = vals.get('email')
            if new_email is not None:
                upd_partner['email'] = new_email or False
            if upd_partner:
                partner.sudo().with_context(skip_persona_sync=True).write(upd_partner)
            persona = self.env['erasmus.persona'].search([('partner_id', '=', partner.id)], limit=1)
            if persona:
                upd_persona = {}
                if 'name' in vals:
                    parts = (upd_partner.get('name') or user.name or '').split()
                    upd_persona['nombre'] = parts[0] if parts else False
                    upd_persona['apellido1'] = parts[-1] if len(parts) > 1 else False
                    upd_persona['apellido2'] = ' '.join(parts[1:-1]) if len(parts) > 2 else False
                if new_email is not None:
                    upd_persona['email'] = new_email or False
                if upd_persona:
                    persona.with_context(skip_partner_sync=True, from_user=True, skip_user_sync=True).write(upd_persona)

    def write(self, vals):
        res = super().write(vals)
        self._sync_persona_partner_from_user_write(vals)
        return res
