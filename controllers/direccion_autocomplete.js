/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, xml, onWillUnmount, onWillUpdateProps } from "@odoo/owl";

class DireccionAutocomplete extends Component {
    static template = xml`
        <div class="o_field_char o_field_direccion_autocomplete" style="position: relative;">
         <input type="text" class="o_input"
                   t-att-placeholder="props.placeholder"
                   t-att-readonly="props.readonly"
                   t-att-disabled="props.readonly"
             t-att-value="state.inputValue"
                   t-on-input="onInput"
                   t-on-keydown="onKeydown" />
            <t t-if="state.suggestions.length">
                <ul class="o_direccion_dropdown" style="position:absolute;z-index:2000;background:#fff;list-style:none;padding:0;margin:0;border:1px solid #ccc;width:100%;max-height:180px;overflow-y:auto;box-shadow:0 2px 6px rgba(0,0,0,0.08)">
                    <li t-foreach="state.suggestions" t-as="s" t-key="s.display_name"
                        t-att-data-index="loop.index0"
                        t-on-mousedown="onSelectFromEvent"
                        t-att-class="'o_direccion_option' + (loop.index0 === state.highlight ? ' o_selected' : '')"
                        style="padding:6px 8px; cursor:pointer;">
                        <t t-esc="s.display_name"/>
                    </li>
                </ul>
            </t>
            <t t-if="!(state.suggestions.length) && state.lastQuery && state.lastQuery.length >= 3">
                <ul class="o_direccion_dropdown" style="position:absolute;z-index:2000;background:#fff;list-style:none;padding:0;margin:0;border:1px solid #ccc;width:100%;max-height:180px;overflow-y:auto;box-shadow:0 2px 6px rgba(0,0,0,0.08)">
                    <li class="o_direccion_option o_empty" style="padding:6px 8px;color:#999;cursor:default;">
                        Sin resultados
                    </li>
                </ul>
            </t>
        </div>
    `;

    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
    };
    static supportedTypes = ["char"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({ inputValue: this.props.value || "", suggestions: [], highlight: -1, lastQuery: "" });
        this._debounce = null;
        this._abortCtrl = null;
        onWillUnmount(() => {
            if (this._debounce) clearTimeout(this._debounce);
            if (this._abortCtrl) {
                try { this._abortCtrl.abort(); } catch (e) {}
            }
        });
        onWillUpdateProps((nextProps) => {
            // Sync local input only when the external value changes and differs from what the user is typing
            if (nextProps.value !== this.props.value && nextProps.value !== this.state.inputValue) {
                this.state.inputValue = nextProps.value || "";
            }
        });
    }

    onInput(ev) {
        const val = ev.target.value || "";
        // Keep local echo responsive
        this.state.inputValue = val;
        // Also propagate to the model so saving works as expected
        if (typeof this.props.update === 'function') {
            this.props.update(val);
        } else if (this.props.record && this.props.name) {
            this.props.record.update({ [this.props.name]: val });
        }
        this.state.lastQuery = val;
        this.state.highlight = -1;
        if (this._debounce) clearTimeout(this._debounce);
        if (val.length < 3) {
            this.state.suggestions = [];
            return;
        }
        this._debounce = setTimeout(() => this._fetchSuggestions(val), 300);
    }

    onKeydown(ev) {
        if (!this.state.suggestions.length) return;
        const key = ev.key;
        if (key === 'ArrowDown') {
            ev.preventDefault();
            this.state.highlight = Math.min(this.state.highlight + 1, this.state.suggestions.length - 1);
        } else if (key === 'ArrowUp') {
            ev.preventDefault();
            this.state.highlight = Math.max(this.state.highlight - 1, 0);
        } else if (key === 'Enter') {
            if (this.state.highlight >= 0) {
                ev.preventDefault();
                this.onSelect(this.state.highlight);
            }
        } else if (key === 'Escape') {
            this.state.suggestions = [];
        }
    }

    async _fetchSuggestions(query) {
        const directUrl = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=5&q=${encodeURIComponent(query)}`;
        const proxyUrl = `/gestion_erasmus/nominatim?limit=5&q=${encodeURIComponent(query)}`;
        if (this._abortCtrl) {
            try { this._abortCtrl.abort(); } catch (e) {}
        }
        this._abortCtrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
        const opts = { headers: { 'Accept': 'application/json' } };
        if (this._abortCtrl) opts.signal = this._abortCtrl.signal;

        const fetchJSON = async (url) => {
            const r = await fetch(url, opts);
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            return r.json();
        };

        let data = [];
        try {
            // Prefer direct Nominatim (usually allowed by CORS)
            data = await fetchJSON(directUrl);
        } catch (e1) {
            try {
                // Fallback to same-origin proxy if available
                data = await fetchJSON(proxyUrl);
            } catch (e2) {
                data = [];
            }
        }

        if (this.state.lastQuery !== query) return;
        this.state.suggestions = (data || []).map(item => {
            const address = item.address || {};
            return {
                display_name: item.display_name,
                street: [address.road, address.house_number].filter(Boolean).join(' '),
                city: address.city || address.town || address.village || address.hamlet || '',
                zip: address.postcode || '',
                state: address.state || address.county || '',
                country: address.country || '',
                country_code: address.country_code || '',
            };
        });
    }

    async onSelect(index) {
        const choice = this.state.suggestions[index];
        if (!choice) return;
        const streetVal = choice.street || choice.display_name || '';
        if (typeof this.props.update === 'function') {
            await this.props.update(streetVal);
        } else if (this.props.record && this.props.name) {
            await this.props.record.update({ [this.props.name]: streetVal });
        }
        this.state.inputValue = streetVal;
        this.state.suggestions = [];

        let res = {};
        try {
            // @api.model: pass only (country_name, state_name)
            res = await this.orm.call('erasmus.persona', 'resolve_address', [choice.country || choice.country_code, choice.state]);
        } catch (e) {}

        const changes = {};
        const has = (f) => this.props.record && Object.prototype.hasOwnProperty.call(this.props.record.data, f);
        if (has('city')) changes.city = choice.city || '';
        if (has('zip')) changes.zip = choice.zip || '';
        if (res && res.country_id && has('country_id')) changes.country_id = res.country_id;
        if (res && res.state_id && has('state_id')) changes.state_id = res.state_id;
        if (Object.keys(changes).length) {
            this.props.record.update(changes);
        }
    }

    onSelectFromEvent(ev) {
        const idx = Number(ev.currentTarget.dataset.index || -1);
        if (idx >= 0) {
            this.onSelect(idx);
        }
    }
}

registry.category('fields').add('direccion_autocomplete', {
    component: DireccionAutocomplete,
    supportedTypes: ['char'],
});

export default DireccionAutocomplete;