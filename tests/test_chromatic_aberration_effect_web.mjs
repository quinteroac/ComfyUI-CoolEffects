import test from "node:test";
import assert from "node:assert/strict";

import {
    CHROMATIC_ABERRATION_PARAM_SPECS,
    apply_chromatic_aberration_uniform_from_widget,
} from "../web/chromatic_aberration_effect.js";

test("chromatic aberration param specs map controls to uniforms", () => {
    assert.deepEqual(CHROMATIC_ABERRATION_PARAM_SPECS, [
        {
            widget_name: "strength",
            uniform_name: "u_strength",
            default_value: 0.01,
        },
        {
            widget_name: "radial",
            uniform_name: "u_radial",
            default_value: 1.0,
        },
    ]);
});

test("apply_chromatic_aberration_uniform_from_widget updates strength uniform", () => {
    const calls = [];
    const node = {
        __cool_chromatic_aberration_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: CHROMATIC_ABERRATION_PARAM_SPECS,
        },
    };

    const applied = apply_chromatic_aberration_uniform_from_widget(
        node,
        "strength",
        0.052,
    );

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_strength", 0.052]]);
});

test("apply_chromatic_aberration_uniform_from_widget maps radial boolean to float", () => {
    const calls = [];
    const node = {
        __cool_chromatic_aberration_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: CHROMATIC_ABERRATION_PARAM_SPECS,
        },
    };

    const applied = apply_chromatic_aberration_uniform_from_widget(
        node,
        "radial",
        false,
    );

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_radial", 0]]);
});
