import test from "node:test";
import assert from "node:assert/strict";

import {
    COLOR_TEMPERATURE_PARAM_SPECS,
    apply_color_temperature_uniform_from_widget,
} from "../web/color_temperature_effect.js";

test("color temperature param specs map controls to uniforms", () => {
    assert.deepEqual(COLOR_TEMPERATURE_PARAM_SPECS, [
        {
            widget_name: "temperature",
            uniform_name: "u_temperature",
            default_value: 0.0,
        },
        {
            widget_name: "tint",
            uniform_name: "u_tint",
            default_value: 0.0,
        },
    ]);
});

test("apply_color_temperature_uniform_from_widget updates temperature uniform", () => {
    const calls = [];
    const node = {
        __cool_color_temperature_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: COLOR_TEMPERATURE_PARAM_SPECS,
        },
    };

    const applied = apply_color_temperature_uniform_from_widget(
        node,
        "temperature",
        0.41,
    );

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_temperature", 0.41]]);
});

test("apply_color_temperature_uniform_from_widget updates tint uniform", () => {
    const calls = [];
    const node = {
        __cool_color_temperature_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: COLOR_TEMPERATURE_PARAM_SPECS,
        },
    };

    const applied = apply_color_temperature_uniform_from_widget(node, "tint", -0.33);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_tint", -0.33]]);
});

test("apply_color_temperature_uniform_from_widget ignores non-numeric values", () => {
    const calls = [];
    const node = {
        __cool_color_temperature_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: COLOR_TEMPERATURE_PARAM_SPECS,
        },
    };

    const applied = apply_color_temperature_uniform_from_widget(
        node,
        "temperature",
        "not-a-number",
    );

    assert.equal(applied, false);
    assert.deepEqual(calls, []);
});
