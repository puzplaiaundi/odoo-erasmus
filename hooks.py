# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _ensure_super_env(env_or_cr):
    """Return an Environment using SUPERUSER_ID regardless of input type."""
    if isinstance(env_or_cr, api.Environment):
        cr = env_or_cr.cr
        context = dict(env_or_cr.context or {})
    else:
        cr = env_or_cr
        context = {}
    return api.Environment(cr, SUPERUSER_ID, context)


def post_init_hook(env):
    """Create Erasmus personas for existing contacts after module installation."""
    env = _ensure_super_env(env)
    Partner = env['res.partner'].with_context(active_test=False)
    Persona = env['erasmus.persona'].with_context(active_test=False)

    partners = Partner.search([])
    _logger.info("[gestion_erasmus] post-init: syncing %s partners into erasmus.persona", len(partners))

    for partner in partners:
        try:
            persona = partner.erasmus_persona_id
            if not persona:
                persona = Persona.search([('partner_id', '=', partner.id)], limit=1)
            if persona:
                if not partner.erasmus_persona_id:
                    partner.with_context(skip_persona_sync=True).write({'erasmus_persona_id': persona.id})
                continue

            name = (partner.name or '').strip()
            parts = name.split()
            persona_vals = {
                'tipo_interno': 'no_asignado',
                'partner_id': partner.id,
                'nombre': parts[0] if parts else False,
                'apellido1': parts[-1] if len(parts) > 1 else False,
                'apellido2': ' '.join(parts[1:-1]) if len(parts) > 2 else False,
                'email': partner.email or False,
                'movil': partner.mobile or False,
                'street': partner.street or False,
                'street2': partner.street2 or False,
                'zip': partner.zip or False,
                'city': partner.city or False,
                'state_id': partner.state_id.id or False,
                'country_id': partner.country_id.id or False,
                'nif': partner.vat or False,
            }
            persona = Persona.with_context(skip_partner_sync=True).create(persona_vals)
            if not partner.active:
                persona.with_context(skip_partner_sync=True).write({'active': False})
            partner.with_context(skip_persona_sync=True).write({'erasmus_persona_id': persona.id})
        except Exception as err:
            _logger.exception("[gestion_erasmus] post-init failed for partner %s: %s", partner.id, err)
    _logger.info("[gestion_erasmus] post-init: sync completed")

    # Hardening for fresh installs: ensure portal users land in Discuss (not backend actions they can't access)
    try:
        portal = env.ref('base.group_portal', raise_if_not_found=False)
        discuss = env.ref('mail.action_discuss', raise_if_not_found=False)
        if portal and discuss:
            users = env['res.users'].with_context(active_test=False).search([('groups_id', 'in', [portal.id])])
            if users:
                users.write({'action_id': discuss.id})
                _logger.info("[gestion_erasmus] post-init: set Discuss as Home Action for %s portal users", len(users))
    except Exception as err:
        _logger.warning("[gestion_erasmus] post-init: failed to set portal Home Action: %s", err)
