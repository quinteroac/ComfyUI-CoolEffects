import test from "node:test";
import assert from "node:assert/strict";

import {
    CURVES_PARAM_SPECS,
    apply_curves_uniform_from_widget,
} from "../web/curves_effect.js";

test("curves param specs map controls to uniforms", () => {
    assert.deepEqual(CURVES_PARAM_SPECS, [
        {
            widget_name: "lift",
            uniform_name: "u_lift",
            default_value: 0.0,
        },
        {
            widget_name: "gamma",
            uniform_name: "u_gamma",
            default_value: 1.0,
        },
        {
            widget_name: "gain",
            uniform_name: "u_gain",
            default_value: 1.0,
        },
    ]);
});

test("apply_curves_uniform_from_widget updates lift uniform", () => {
    const calls = [];
    const node = {
        __cool_curves_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: CURVES_PARAM_SPECS,
        },
    };

    const applied = apply_curves_uniform_from_widget(node, "lift", 0.4);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_lift", 0.4]]);
});

test("apply_curves_uniform_from_widget updates gamma and gain uniforms", () => {
    const calls = [];
    const node = {
        __cool_curves_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: CURVES_PARAM_SPECS,
        },
    };

    const gamma_applied = apply_curves_uniform_from_widget(node, "gamma", 2.2);
    const gain_applied = apply_curves_uniform_from_widget(node, "gain", 1.5);

    assert.equal(gamma_applied, true);
    assert.equal(gain_applied, true);
    assert.deepEqual(calls, [
        ["u_gamma", 2.2],
        ["u_gain", 1.5],
    ]);
});
