import test from "node:test";
import assert from "node:assert/strict";

import {
    DITHERING_PARAM_SPECS,
    apply_dithering_uniform_from_widget,
} from "../web/dithering_effect.js";

test("dithering param specs map controls to uniforms", () => {
    assert.deepEqual(DITHERING_PARAM_SPECS, [
        {
            widget_name: "dither_scale",
            uniform_name: "u_dither_scale",
            default_value: 1.0,
        },
        {
            widget_name: "threshold",
            uniform_name: "u_threshold",
            default_value: 0.5,
        },
        {
            widget_name: "palette_size",
            uniform_name: "u_palette_size",
            default_value: 2.0,
        },
    ]);
});

test("apply_dithering_uniform_from_widget updates scale and threshold uniforms", () => {
    const calls = [];
    const node = {
        __cool_dithering_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: DITHERING_PARAM_SPECS,
        },
    };

    const applied_scale = apply_dithering_uniform_from_widget(node, "dither_scale", 0.5);
    const applied_threshold = apply_dithering_uniform_from_widget(node, "threshold", 0.4);

    assert.equal(applied_scale, true);
    assert.equal(applied_threshold, true);
    assert.deepEqual(calls, [
        ["u_dither_scale", 0.5],
        ["u_threshold", 0.4],
    ]);
});

test("apply_dithering_uniform_from_widget supports palette presets for bw and 4-level dither", () => {
    const calls = [];
    const node = {
        __cool_dithering_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: DITHERING_PARAM_SPECS,
        },
    };

    const applied_bw = apply_dithering_uniform_from_widget(node, "palette_size", 2);
    const applied_four_level = apply_dithering_uniform_from_widget(node, "palette_size", 4);

    assert.equal(applied_bw, true);
    assert.equal(applied_four_level, true);
    assert.deepEqual(calls, [
        ["u_palette_size", 2],
        ["u_palette_size", 4],
    ]);
});
