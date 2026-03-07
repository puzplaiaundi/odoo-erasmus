# -*- coding: utf-8 -*-
from odoo import models


class ResCountry(models.Model):
    _inherit = 'res.country'

    def name_get(self):
        res = super().name_get()
        if not self.env.context.get('erasmus_pais_label'):
            return res
        # Build map country_id -> (eu, es)
        Pais = self.env['erasmus.pais'].sudo()
        mapping = {p.country_id.id: (p.name_eu or '', p.name_es or '') for p in Pais.search([('country_id', 'in', self.ids)])}
        labeled = []
        for rec in self:
            eu_es = mapping.get(rec.id)
            if eu_es:
                eu, es = eu_es
                label = f"{eu} - {es}" if eu and es else (eu or es or rec.name)
                labeled.append((rec.id, label))
            else:
                labeled.append((rec.id, rec.name))
        return labeled