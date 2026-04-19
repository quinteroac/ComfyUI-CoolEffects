import test from "node:test";
import assert from "node:assert/strict";

import {
    COLOR_QUANTIZATION_PARAM_SPECS,
    apply_color_quantization_uniform_from_widget,
} from "../web/color_quantization_effect.js";

test("color quantization param specs map controls to uniforms", () => {
    assert.deepEqual(COLOR_QUANTIZATION_PARAM_SPECS, [
        {
            widget_name: "levels_r",
            uniform_name: "u_levels_r",
            default_value: 4.0,
        },
        {
            widget_name: "levels_g",
            uniform_name: "u_levels_g",
            default_value: 4.0,
        },
        {
            widget_name: "levels_b",
            uniform_name: "u_levels_b",
            default_value: 4.0,
        },
    ]);
});

test("apply_color_quantization_uniform_from_widget updates 8-color preset uniforms", () => {
    const calls = [];
    const node = {
        __cool_color_quantization_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: COLOR_QUANTIZATION_PARAM_SPECS,
        },
    };

    const applied_r = apply_color_quantization_uniform_from_widget(node, "levels_r", 2);
    const applied_g = apply_color_quantization_uniform_from_widget(node, "levels_g", 2);
    const applied_b = apply_color_quantization_uniform_from_widget(node, "levels_b", 2);

    assert.equal(applied_r, true);
    assert.equal(applied_g, true);
    assert.equal(applied_b, true);
    assert.deepEqual(calls, [
        ["u_levels_r", 2],
        ["u_levels_g", 2],
        ["u_levels_b", 2],
    ]);
});

test("apply_color_quantization_uniform_from_widget updates 512-color preset uniforms", () => {
    const calls = [];
    const node = {
        __cool_color_quantization_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: COLOR_QUANTIZATION_PARAM_SPECS,
        },
    };

    const applied_r = apply_color_quantization_uniform_from_widget(node, "levels_r", 8);
    const applied_g = apply_color_quantization_uniform_from_widget(node, "levels_g", 8);
    const applied_b = apply_color_quantization_uniform_from_widget(node, "levels_b", 8);

    assert.equal(applied_r, true);
    assert.equal(applied_g, true);
    assert.equal(applied_b, true);
    assert.deepEqual(calls, [
        ["u_levels_r", 8],
        ["u_levels_g", 8],
        ["u_levels_b", 8],
    ]);
});
