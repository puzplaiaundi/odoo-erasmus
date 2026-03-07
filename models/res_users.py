# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['erasmus_role']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['erasmus_role']

    erasmus_role = fields.Selection(
        selection=[
            ('', 'Sin acceso'),
            ('profesor', 'Profesor'),
            ('admin', 'Administrador'),
        ],
        string='Rol Erasmus',
        help='Controla el acceso al módulo Gestión Erasmus. "Sin acceso" no asigna ningún grupo.',
        default='',
        groups='base.group_system',
    )

    @api.onchange('erasmus_role')
    def _onchange_erasmus_role(self):
        """Sync Erasmus groups based on the selected role.
        Empty -> remove both groups; profesor -> assign professor; admin -> assign admin.
        """
        Group = self.env['res.groups']
        # xml_id is not a stored field on res.groups; use env.ref safely
        try:
            g_prof = self.env.ref('gestion_erasmus.group_erasmus_profesor')
        except Exception:
            g_prof = Group.browse()
        try:
            g_admin = self.env.ref('gestion_erasmus.group_erasmus_admin')
        except Exception:
            g_admin = Group.browse()

        for user in self:
            # Start by removing both groups
            groups_to_remove = (g_prof | g_admin)
            if groups_to_remove:
                user.groups_id -= groups_to_remove

            if user.erasmus_role == 'profesor' and g_prof:
                user.groups_id |= g_prof
            elif user.erasmus_role == 'admin' and g_admin:
                user.groups_id |= g_admin

    def _sync_persona_partner_from_user_write(self, vals):
        if self.env.context.get('skip_persona_sync'):
            return
        for user in self:
            partner = user.partner_id
            if not partner:
                continue
            # Actualizar partner con nombre o email/login
            upd_partner = {}
            if 'name' in vals:
                upd_partner['name'] = vals.get('name') or user.name
            # Priorizar login como email si se cambia, si no, usar email explícito
            new_email = None
            if 'login' in vals:
                new_email = vals.get('login')
            elif 'email' in vals:
                new_email = vals.get('email')
            if new_email is not None:
                upd_partner['email'] = new_email or False
            if upd_partner:
                partner.sudo().with_context(skip_persona_sync=True).write(upd_partner)
            # Actualizar persona vinculada: nombre desglosado y email
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
                    # Evitar escribir partner de nuevo y evitar reescritura sobre el propio user
                    persona.with_context(skip_partner_sync=True, from_user=True, skip_user_sync=True).write(upd_persona)

    def write(self, vals):
        res = super().write(vals)
        self._sync_persona_partner_from_user_write(vals)
        if 'erasmus_role' in vals:
            self._onchange_erasmus_role()
            # Si queda sin acceso, aseguramos que no apunte a una acción por defecto de Erasmus
            for user in self:
                if (user.erasmus_role or '') == '':
                    # Fijar una acción segura (Discuss) para evitar aterrizar en acciones restringidas
                    try:
                        discuss = self.env.ref('mail.action_discuss')
                        user.action_id = discuss
                    except Exception:
                        try:
                            user.action_id = False
                        except Exception:
                            pass
        return res

    @api.model
    def create(self, vals):
        """On user creation, if Erasmus role is empty, avoid defaulting to an Erasmus action."""
        user = super().create(vals)
        if not (user.erasmus_role or ''):
            try:
                discuss = self.env.ref('mail.action_discuss')
                user.action_id = discuss
            except Exception:
                try:
                    user.action_id = False
                except Exception:
                    pass
        return user
