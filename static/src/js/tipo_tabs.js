/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";

function toggleTipoTabs(root) {
    try {
        // Find current tipo_interno value from rendered inputs or dataset
        const tipoRadio = root.querySelector('input[name="tipo_interno"]:checked');
        const tipo = tipoRadio ? tipoRadio.value : null;
        const notebook = root.querySelector('.o_notebook');
        if (!notebook) return;
        // Tabs header items
        const tabs = notebook.querySelectorAll('.nav-tabs .nav-item');
        const panes = notebook.querySelectorAll('.tab-content .tab-pane, .o_notebook_page');
        // Our page markers
        const estPage = root.querySelector('.ge-page-estudiante');
        const profPage = root.querySelector('.ge-page-profesor');
        const estHeader = tabs && Array.from(tabs).find(li => /Estudiante/i.test(li.textContent || ''));
        const profHeader = tabs && Array.from(tabs).find(li => /Profesor/i.test(li.textContent || ''));
        // Helper to show/hide
        const setVisible = (el, visible) => {
            if (!el) return;
            el.style.display = visible ? '' : 'none';
        };
        // Default: show all so Odoo can initialize, then hide non-matching
        const wantEst = tipo === 'estudiante';
        const wantProf = tipo === 'profesor';
        // Hide/show pages
        setVisible(estPage, !!wantEst);
        setVisible(profPage, !!wantProf);
        // Hide/show headers (if rendered with tabs)
        setVisible(estHeader, !!wantEst);
        setVisible(profHeader, !!wantProf);
        // If the active tab was hidden, switch to the visible one
        const activeHeader = notebook.querySelector('.nav-tabs .nav-item .nav-link.active');
        const activeIsHidden = activeHeader && activeHeader.closest('.nav-item') && activeHeader.closest('.nav-item').style.display === 'none';
        if (activeIsHidden) {
            const target = wantEst ? estHeader : profHeader;
            if (target) {
                const link = target.querySelector('.nav-link');
                link && link.click();
            }
        }
    } catch (_) {}
}

patch(FormRenderer.prototype, 'gestion_erasmus_tipo_tabs', {
    setup() {
        this._super(...arguments);
        // Observe radio changes
        this.__ge_onChange = (ev) => {
            const t = ev && ev.target;
            if (t && t.name === 'tipo_interno') {
                toggleTipoTabs(this.el);
            }
        };
    },
    mounted() {
        this._super(...arguments);
        if (this.el) {
            this.el.addEventListener('change', this.__ge_onChange, true);
            toggleTipoTabs(this.el);
        }
    },
    willUnmount() {
        try {
            this.el && this.el.removeEventListener('change', this.__ge_onChange, true);
        } catch(_) {}
        this._super(...arguments);
    },
});
