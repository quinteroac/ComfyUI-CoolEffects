import test from "node:test";
import assert from "node:assert/strict";

import {
    FISHEYE_PARAM_SPECS,
    apply_fisheye_uniform_from_widget,
} from "../web/fisheye_effect.js";

test("fisheye param specs map sliders to uniforms", () => {
    assert.deepEqual(FISHEYE_PARAM_SPECS, [
        {
            widget_name: "strength",
            uniform_name: "u_strength",
            default_value: 0.5,
        },
        {
            widget_name: "zoom",
            uniform_name: "u_zoom",
            default_value: 1.0,
        },
    ]);
});

test("apply_fisheye_uniform_from_widget updates preview uniform for strength", () => {
    const calls = [];
    const node = {
        __cool_fisheye_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: FISHEYE_PARAM_SPECS,
        },
    };

    const applied = apply_fisheye_uniform_from_widget(node, "strength", 0.83);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_strength", 0.83]]);
});

test("apply_fisheye_uniform_from_widget updates preview uniform for zoom", () => {
    const calls = [];
    const node = {
        __cool_fisheye_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: FISHEYE_PARAM_SPECS,
        },
    };

    const applied = apply_fisheye_uniform_from_widget(node, "zoom", 1.45);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_zoom", 1.45]]);
});
