import test from "node:test";
import assert from "node:assert/strict";

import { HSL_PARAM_SPECS, apply_hsl_uniform_from_widget } from "../web/hsl_effect.js";

test("hsl param specs map controls to uniforms", () => {
    assert.deepEqual(HSL_PARAM_SPECS, [
        {
            widget_name: "hue_shift",
            uniform_name: "u_hue_shift",
            default_value: 0.0,
        },
        {
            widget_name: "saturation",
            uniform_name: "u_saturation",
            default_value: 0.0,
        },
        {
            widget_name: "lightness",
            uniform_name: "u_lightness",
            default_value: 0.0,
        },
    ]);
});

test("apply_hsl_uniform_from_widget updates hue shift uniform", () => {
    const calls = [];
    const node = {
        __cool_hsl_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: HSL_PARAM_SPECS,
        },
    };

    const applied = apply_hsl_uniform_from_widget(node, "hue_shift", 135.0);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_hue_shift", 135.0]]);
});

test("apply_hsl_uniform_from_widget updates saturation uniform", () => {
    const calls = [];
    const node = {
        __cool_hsl_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: HSL_PARAM_SPECS,
        },
    };

    const applied = apply_hsl_uniform_from_widget(node, "saturation", -0.35);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_saturation", -0.35]]);
});

test("apply_hsl_uniform_from_widget updates lightness uniform", () => {
    const calls = [];
    const node = {
        __cool_hsl_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: HSL_PARAM_SPECS,
        },
    };

    const applied = apply_hsl_uniform_from_widget(node, "lightness", 0.22);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_lightness", 0.22]]);
});
