from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    erasmus_role = fields.Selection(
        selection=[
            ('', 'Sin acceso'),
            ('profesor', 'Profesor'),
            ('admin', 'Administrador'),
        ],
        string='Rol Erasmus',
        help='Controla el acceso al módulo Gestión Erasmus. "Sin acceso" no asigna ningún grupo.',
        default='' 
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

    def write(self, vals):
        """Ensure groups are consistent when writing programmatically."""
        res = super().write(vals)
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
