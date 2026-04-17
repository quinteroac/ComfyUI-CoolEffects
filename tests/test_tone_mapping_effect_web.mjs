import test from "node:test";
import assert from "node:assert/strict";

import {
    MODE_UNIFORM_VALUES,
    TONE_MAPPING_PARAM_SPECS,
    apply_tone_mapping_uniform_from_widget,
    map_mode_to_uniform_value,
} from "../web/tone_mapping_effect.js";

test("tone mapping param specs map controls to uniforms", () => {
    assert.deepEqual(TONE_MAPPING_PARAM_SPECS, [
        { widget_name: "mode", uniform_name: "u_mode", default_value: 0.0 },
        { widget_name: "intensity", uniform_name: "u_intensity", default_value: 1.0 },
        { widget_name: "shadow_r", uniform_name: "u_shadow_r", default_value: 0.0 },
        { widget_name: "shadow_g", uniform_name: "u_shadow_g", default_value: 0.0 },
        { widget_name: "shadow_b", uniform_name: "u_shadow_b", default_value: 0.0 },
        { widget_name: "highlight_r", uniform_name: "u_highlight_r", default_value: 1.0 },
        { widget_name: "highlight_g", uniform_name: "u_highlight_g", default_value: 1.0 },
        { widget_name: "highlight_b", uniform_name: "u_highlight_b", default_value: 1.0 },
    ]);
});

test("map_mode_to_uniform_value maps all tone mapping modes", () => {
    assert.equal(map_mode_to_uniform_value("none"), MODE_UNIFORM_VALUES.none);
    assert.equal(map_mode_to_uniform_value("bw"), MODE_UNIFORM_VALUES.bw);
    assert.equal(map_mode_to_uniform_value("sepia"), MODE_UNIFORM_VALUES.sepia);
    assert.equal(map_mode_to_uniform_value("duotone"), MODE_UNIFORM_VALUES.duotone);
    assert.equal(map_mode_to_uniform_value("unknown"), MODE_UNIFORM_VALUES.none);
});

test("apply_tone_mapping_uniform_from_widget updates mode and numeric uniforms", () => {
    const calls = [];
    const node = {
        __cool_tone_mapping_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: TONE_MAPPING_PARAM_SPECS,
        },
    };

    const mode_applied = apply_tone_mapping_uniform_from_widget(node, "mode", "sepia");
    const intensity_applied = apply_tone_mapping_uniform_from_widget(node, "intensity", 0.55);
    const shadow_applied = apply_tone_mapping_uniform_from_widget(node, "shadow_b", 0.25);

    assert.equal(mode_applied, true);
    assert.equal(intensity_applied, true);
    assert.equal(shadow_applied, true);
    assert.deepEqual(calls, [
        ["u_mode", 2.0],
        ["u_intensity", 0.55],
        ["u_shadow_b", 0.25],
    ]);
});

test("apply_tone_mapping_uniform_from_widget ignores non-numeric numeric-widget values", () => {
    const calls = [];
    const node = {
        __cool_tone_mapping_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: TONE_MAPPING_PARAM_SPECS,
        },
    };

    const applied = apply_tone_mapping_uniform_from_widget(node, "highlight_g", "invalid-number");

    assert.equal(applied, false);
    assert.deepEqual(calls, []);
});
