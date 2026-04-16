import test from "node:test";
import assert from "node:assert/strict";

import {
    VIGNETTE_PARAM_SPECS,
    apply_vignette_uniform_from_widget,
} from "../web/vignette_effect.js";

test("vignette param specs map sliders to uniforms", () => {
    assert.deepEqual(VIGNETTE_PARAM_SPECS, [
        {
            widget_name: "strength",
            uniform_name: "u_strength",
            default_value: 0.5,
        },
        {
            widget_name: "radius",
            uniform_name: "u_radius",
            default_value: 0.75,
        },
        {
            widget_name: "softness",
            uniform_name: "u_softness",
            default_value: 0.5,
        },
    ]);
});

test("apply_vignette_uniform_from_widget updates preview uniform for strength", () => {
    const calls = [];
    const node = {
        __cool_vignette_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: VIGNETTE_PARAM_SPECS,
        },
    };

    const applied = apply_vignette_uniform_from_widget(node, "strength", 0.84);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_strength", 0.84]]);
});

test("apply_vignette_uniform_from_widget updates preview uniform for radius", () => {
    const calls = [];
    const node = {
        __cool_vignette_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: VIGNETTE_PARAM_SPECS,
        },
    };

    const applied = apply_vignette_uniform_from_widget(node, "radius", 1.12);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_radius", 1.12]]);
});

test("apply_vignette_uniform_from_widget updates preview uniform for softness", () => {
    const calls = [];
    const node = {
        __cool_vignette_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: VIGNETTE_PARAM_SPECS,
        },
    };

    const applied = apply_vignette_uniform_from_widget(node, "softness", 0.29);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_softness", 0.29]]);
});
