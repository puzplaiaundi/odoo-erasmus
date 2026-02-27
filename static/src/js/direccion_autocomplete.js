/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, xml, onWillUnmount, onWillUpdateProps, onMounted } from "@odoo/owl";

class DireccionAutocomplete extends Component {
   static template = xml`
    <div class="o_field_char o_field_direccion_autocomplete" style="position: relative;">
     <input type="text" class="o_input"
         t-att-placeholder="props.placeholder"
         t-att-readonly="props.readonly"
         t-att-disabled="props.readonly"
               t-att-value="state.inputValue"
               t-on-input="onInput"
               t-on-change="onChange"
               t-on-keydown="onKeydown"
               t-on-blur="onBlur" />
        <t t-if="state.open &amp;&amp; state.suggestions.length">
            <ul class="o_direccion_dropdown" style="position:absolute;top:100%;left:0;z-index:3000;background:#fff;list-style:none;padding:0;margin:0;border:1px solid #ccc;width:100%;max-height:180px;overflow-y:auto;box-shadow:0 2px 6px rgba(0,0,0,0.08)">
                <li t-foreach="state.suggestions" t-as="s" t-key="s.place_id or s._i"
                    t-att-data-index="s._i"
                    t-on-mousedown="onSelectFromEvent"
                    t-att-class="'o_direccion_option' + (s._i === state.highlight ? ' o_selected' : '')"
                    style="padding:6px 8px; cursor:pointer;">
                    <span t-esc="s.street"/>
                    <t t-if="s.portal">
                        <span>, </span><span t-esc="s.portal"/>
                    </t>
                    <t t-if="s.puerta">
                        <span>, </span><span t-esc="s.puerta"/>
                    </t>
                    <t t-if="s.city">
                        <span>, </span><span t-esc="s.city"/>
                    </t>
                    <t t-if="s.state">
                        <span>, </span><span t-esc="s.state"/>
                    </t>
                    <t t-if="s.country">
                        <span>, </span><span t-esc="s.country"/>
                    </t>
                </li>
            </ul>
        </t>
        <t t-if="state.open &amp;&amp; !(state.suggestions.length) &amp;&amp; state.lastQuery &amp;&amp; state.lastQuery.length &gt;= 3">
            <ul class="o_direccion_dropdown" style="position:absolute;top:100%;left:0;z-index:3000;background:#fff;list-style:none;padding:0;margin:0;border:1px solid #ccc;width:100%;max-height:180px;overflow-y:auto;box-shadow:0 2px 6px rgba(0,0,0,0.08)">
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
        this.state = useState({ inputValue: this.props.value || "", suggestions: [], highlight: -1, lastQuery: "", open: false });
    // Debug helper (set to false to silence logs)
    this._DEBUG = false;
        this._log = (...args) => {
            if (this._DEBUG && typeof console !== 'undefined') {
                console.log('[DireccionAutocomplete]', ...args);
            }
        };
        this._log('setup', {
            field: this.props.name,
            recordId: this.props.record && this.props.record.resId,
            initialValue: this.props.value,
        });
        // Sync input with incoming props or record data
        onWillUpdateProps((nextProps) => {
            const nextDataVal = nextProps && nextProps.record && nextProps.record.data ? nextProps.record.data[nextProps.name] : undefined;
            const nextVal = (nextProps.value !== undefined) ? nextProps.value : (nextDataVal !== undefined ? nextDataVal : "");
            this._log('onWillUpdateProps', { nextValue: nextProps.value, nextDataVal, computed: nextVal, prevInput: this.state.inputValue });
            if (nextVal !== this.state.inputValue) {
                this.state.inputValue = nextVal || "";
            }
        });
        onMounted(() => {
            const dataVal = this.props && this.props.record && this.props.record.data ? this.props.record.data[this.props.name] : undefined;
            const initial = (this.props.value !== undefined) ? this.props.value : (dataVal !== undefined ? dataVal : "");
            if (initial !== this.state.inputValue) {
                this.state.inputValue = initial || "";
            }
            this._log('onMounted', { inputValue: this.state.inputValue, dataVal, propsValue: this.props.value });
        });
        this._debounce = null;
        this._abortCtrl = null;
        onWillUnmount(() => {
            if (this._debounce) clearTimeout(this._debounce);
            if (this._abortCtrl) {
                try { this._abortCtrl.abort(); } catch (e) {}
            }
        });
        // (moved above for robust sync)
    }

    _commitValue(val) {
        const v = val != null ? val : (this.state.inputValue || "");
        this._log('commitValue ->', v);
        // Always prefer the field update API for the main field to ensure proper dirty tracking
        if (typeof this.props.update === 'function') {
            const p = this.props.update(v);
            if (p && typeof p.then === 'function') {
                p.then(() => this._log('commitValue done (props.update)', { value: v }))
                 .catch((e) => this._log('commitValue error (props.update)', e));
            }
            return p;
        }
        // Fallback (should rarely happen in standard field usage)
        if (this.props.record && this.props.name) {
            const p = this.props.record.update({ [this.props.name]: v });
            if (p && typeof p.then === 'function') {
                p.then(() => this._log('commitValue done (record.update)', { value: v }))
                 .catch((e) => this._log('commitValue error (record.update)', e));
            }
            return p;
        }
        return Promise.resolve();
    }

    onInput(ev) {
        if (this.props.readonly) {
            return; // ignore typing when readonly
        }
        const val = ev.target.value || "";
        this._log('onInput', { val });
        // Keep local echo responsive
        this.state.inputValue = val;
        // Also propagate to the model so saving works as expected
        this._commitValue(val);
        try {
            this._log('record.data after input', this.props.record && this.props.record.data && this.props.record.data[this.props.name]);
        } catch(_) {}
        this.state.lastQuery = val;
        this.state.highlight = -1;
        this.state.open = true;
        if (this._debounce) clearTimeout(this._debounce);
        if (val.length < 3) {
            this.state.suggestions = [];
            return;
        }
        this._debounce = setTimeout(() => this._fetchSuggestions(val), 300);
    }

    onChange(ev) {
        // Ensure that if user leaves the field without selecting, the latest value is committed
        if (this.props.readonly) return;
        const val = (ev && ev.target && ev.target.value) || this.state.inputValue || "";
        this._log('onChange', { val });
        this._commitValue(val);
    }

    onKeydown(ev) {
        // Allow closing with Escape even without suggestions
        if (ev.key === 'Escape') {
            this.state.suggestions = [];
            this.state.open = false;
            return;
        }
        if (!this.state.suggestions.length) return;
        const key = ev.key;
        if (key === 'ArrowDown') {
            ev.preventDefault();
            this.state.highlight = Math.min(this.state.highlight + 1, this.state.suggestions.length - 1);
        } else if (key === 'ArrowUp') {
            ev.preventDefault();
            this.state.highlight = Math.max(this.state.highlight - 1, 0);
        } else if (key === 'Enter' || key === 'Tab') {
            if (this.state.highlight >= 0) {
                ev.preventDefault();
                this.onSelect(this.state.highlight);
            } else if (this.state.suggestions.length === 1) {
                // Fast-accept single suggestion
                if (key === 'Enter') ev.preventDefault();
                this.onSelect(0);
            }
        }
    }

    async _fetchSuggestions(query) {
    this._log('_fetchSuggestions query ->', query);
    // Bias search by current country when available
        let countryCode = '';
        try {
            const c = this.props.record && this.props.record.data && this.props.record.data.country_id;
            // many2one values are [id, display_name]
            if (Array.isArray(c) && c.length) {
                // We need the ISO code; fetch synchronously would be heavy. Let backend resolve, or pass empty.
                // As a heuristic, if display_name contains '(XX)', extract it. Otherwise, leave blank.
                const m = typeof c[1] === 'string' ? c[1].match(/\(([A-Z]{2})\)/) : null;
                if (m) countryCode = m[1];
            }
        } catch (_) {}
        // Language preference
        const navLang = (typeof navigator !== 'undefined' && navigator.language) ? navigator.language : 'es-ES';
        const acceptLang = encodeURIComponent(`${navLang},es;q=0.8,en;q=0.5`);
        const limit = 7;
        const base = `format=json&addressdetails=1&limit=${limit}&accept-language=${acceptLang}` + (countryCode ? `&countrycodes=${countryCode.toLowerCase()}` : '');
        const directUrl = `https://nominatim.openstreetmap.org/search?${base}&q=${encodeURIComponent(query)}`;
        const proxyUrl = `/gestion_erasmus/nominatim?${base}&q=${encodeURIComponent(query)}`;
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
            this._log('_fetchSuggestions direct OK', { count: data && data.length });
        } catch (e1) {
            this._log('_fetchSuggestions direct FAIL', e1);
            try {
                // Fallback to same-origin proxy if available
                data = await fetchJSON(proxyUrl);
                this._log('_fetchSuggestions proxy OK', { count: data && data.length });
            } catch (e2) {
                this._log('_fetchSuggestions proxy FAIL', e2);
                data = [];
            }
        }

        if (this.state.lastQuery !== query) return;
        const arr = Array.isArray(data) ? data : [];
        const seen = new Set();
        this.state.suggestions = arr.map((item, idx) => {
            const address = item.address || {};
            // Heurística simple para separar portal y puerta a partir de house_number
            const house = (address.house_number || '').trim();
            let portal = '';
            let puerta = '';
            if (house) {
                const parts = house.split(/[\s\/-]+/);
                if (parts.length >= 2) {
                    portal = parts[0];
                    puerta = parts.slice(1).join(' ');
                } else {
                    portal = house;
                }
            }
            const dn = (item.display_name || '').trim();
            // Mejor extracción de vía: incluye variantes (pedestrian, footway, residential, path, cycleway)
            const road = (address.road || address.pedestrian || address.footway || address.residential || address.path || address.cycleway || '').toString().trim() || (dn ? dn.split(',')[0].trim() : '');
            // Ciudad/localidad con más variantes y orden intuitivo
            const city = (address.city || address.town || address.village || address.municipality || address.locality || address.borough || address.suburb || address.city_district || address.hamlet || '').toString();
            // Estado/Provincia: para España priorizamos provincia/county y no la comunidad
            const country_code = (address.country_code || '').toUpperCase();
            let state = '';
            if (country_code === 'ES') {
                state = (address.province || address.county || address.state || address.region || '').toString();
            } else {
                state = (address.state || address.province || address.region || address.county || '').toString();
            }
            const zip = (address.postcode || '').toString();
            const country = (address.country || '').toString();
            const key = `${road}|${portal}|${puerta}|${city}|${state}|${country}|${zip}`.toLowerCase();
            if (seen.has(key)) return null; // dedupe
            seen.add(key);
            return {
        _i: idx,
        place_id: item.place_id,
                display_name: item.display_name,
                // Usamos solo el nombre de la vía para evitar duplicar el número (se muestra aparte como portal/puerta)
                street: road,
                city,
                zip,
                state,
                country,
                country_code,
                portal,
                puerta,
            };
        }).filter(Boolean);
        this._log('_fetchSuggestions mapped', { count: this.state.suggestions.length });
    }

    async onSelect(index) {
        const choice = this.state.suggestions[index];
        if (!choice) return;
        const streetVal = (choice.street || '').trim() || (choice.display_name || '').split(',')[0].trim() || '';
        this._log('onSelect', { index, choice, streetVal });
        // Use field update API for the main field
        if (typeof this.props.update === 'function') {
            await this.props.update(streetVal);
        } else if (this.props.record && this.props.name) {
            await this.props.record.update({ [this.props.name]: streetVal });
        }
        this.state.inputValue = streetVal;
        this.state.suggestions = [];
        this.state.open = false;
        this.state.lastQuery = '';

        let res = {};
        try {
            // Pass (country_code, state_name, country_name) for robust matching
            res = await this.orm.call('erasmus.persona', 'resolve_address', [choice.country_code || '', choice.state || '', choice.country || '']);
            this._log('resolve_address result', res);
        } catch (e) {}

    const changes = {};
        const has = (f) => this.props.record && Object.prototype.hasOwnProperty.call(this.props.record.data, f);
        if (has('city')) changes.city = choice.city || '';
        if (has('zip')) changes.zip = choice.zip || '';
    // Portal/Puerta: solo rellenar puerta si existe portal
    if (has('portal')) changes.portal = choice.portal || '';
    if (has('puerta')) changes.puerta = (choice.portal ? (choice.puerta || '') : '');

        // Ensure country resolution; fallback client-side if backend didn't find it
        if ((!res || !res.country_id) && choice.country_code) {
            try {
                const countries = await this.orm.searchRead('res.country', [['code', '=', choice.country_code]], ['display_name']);
                if (countries && countries.length) {
                    res = Object.assign({}, res, { country_id: countries[0].id });
                }
            } catch (e) {}
        }
        if ((!res || !res.country_id) && choice.country) {
            try {
                const countries = await this.orm.searchRead('res.country', [['name', 'ilike', choice.country]], ['display_name']);
                if (countries && countries.length) {
                    res = Object.assign({}, res, { country_id: countries[0].id });
                }
            } catch (e) {}
        }

        // Prepare many2one values as [id, display_name]
        if (res && res.country_id && has('country_id')) {
            try {
                const recs = await this.orm.read('res.country', [res.country_id], ['display_name']);
                const name = (recs && recs[0] && (recs[0].display_name || recs[0].name)) || '';
                changes.country_id = [res.country_id, name];
            } catch (e) {
                changes.country_id = [res.country_id, choice.country || ''];
            }
        }
        // Ensure state resolution; fallback client-side if backend didn't find it
        if ((!res || !res.state_id) && res && res.country_id && choice.state) {
            try {
                const states = await this.orm.searchRead('res.country.state', [['country_id', '=', res.country_id], '|', ['code', '=', (choice.state || '').toUpperCase()], ['name', 'ilike', choice.state]], ['display_name']);
                if (states && states.length) {
                    res = Object.assign({}, res, { state_id: states[0].id });
                }
            } catch (e) {}
        }
        if (res && res.state_id && has('state_id')) {
            try {
                const recs = await this.orm.read('res.country.state', [res.state_id], ['display_name']);
                const name = (recs && recs[0] && (recs[0].display_name || recs[0].name)) || '';
                changes.state_id = [res.state_id, name];
            } catch (e) {
                changes.state_id = [res.state_id, choice.state || ''];
            }
        }

        if (Object.keys(changes).length) {
            this._log('onSelect -> updating aux fields', changes);
            this.props.record.update(changes).then(() => this._log('aux fields updated')).catch((e)=>this._log('aux fields update error', e));
        }
    }

    onSelectFromEvent(ev) {
        const idx = Number(ev.currentTarget.dataset.index || -1);
        if (idx >= 0) {
            this.onSelect(idx);
        }
    }

    onBlur() {
        // Commit latest typed value before closing to avoid lost edits
        if (!this.props.readonly) {
            this._log('onBlur commit', { current: this.state.inputValue });
            this._commitValue();
        }
        // slight delay to allow mousedown selection to fire first
        setTimeout(() => {
            this.state.open = false;
        }, 150);
    }
}

try {
    registry.category('fields').add('direccion_autocomplete', {
        component: DireccionAutocomplete,
        supportedTypes: ['char'],
    });
    if (typeof console !== 'undefined') {
        console.info('direccion_autocomplete widget registered (gestion_erasmus)');
    }
} catch (e) {
    // If already registered or registry unavailable, log once for diagnostics
    if (typeof console !== 'undefined') {
        console.warn('direccion_autocomplete widget registration issue:', e && e.message ? e.message : e);
    }
}

export default DireccionAutocomplete;