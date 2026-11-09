import { t, useProps } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';
import { registry } from '@web/core/registry';
import {
    SelectionField,
    selectionField,
    selectionFieldProps,
} from '@web/views/fields/selection/selection_field';

/** Selection field limited to the tiers listed in a JSON options field. */
export class EffortPickerField extends SelectionField {
    props = useProps({
        ...selectionFieldProps,
        optionsField: t.string().optional(''),
    });
    get options() {
        const base = super.options;
        if (!this.props.optionsField) {
            return base;
        }
        const supported = this.props.record.data[this.props.optionsField];
        if (!Array.isArray(supported)) {
            return base;
        }
        const allowed = new Set(supported);
        return base.filter(([tier]) => allowed.has(tier));
    }
}

export const effortPickerField = {
    ...selectionField,
    component: EffortPickerField,
    displayName: _t('Effort Picker'),
    supportedOptions: [
        {
            label: _t('Options field'),
            name: 'options_field',
            type: 'string',
        },
    ],
    supportedTypes: ['selection'],
    extractProps: (staticInfo, dynamicInfo) => ({
        ...selectionField.extractProps(staticInfo, dynamicInfo),
        optionsField: staticInfo.options.options_field || '',
    }),
    fieldDependencies: ({ options }) =>
        options.options_field ? [{ name: options.options_field, type: 'json' }] : [],
};

registry.category('fields').add('wooai_effort_picker', effortPickerField);
