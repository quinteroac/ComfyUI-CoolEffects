import test from "node:test";
import assert from "node:assert/strict";

import {
    BRIGHTNESS_CONTRAST_PARAM_SPECS,
    apply_brightness_contrast_uniform_from_widget,
} from "../web/brightness_contrast_effect.js";

test("brightness contrast param specs map sliders to uniforms", () => {
    assert.deepEqual(BRIGHTNESS_CONTRAST_PARAM_SPECS, [
        {
            widget_name: "brightness",
            uniform_name: "u_brightness",
            default_value: 0.0,
        },
        {
            widget_name: "contrast",
            uniform_name: "u_contrast",
            default_value: 0.0,
        },
    ]);
});

test("apply_brightness_contrast_uniform_from_widget updates brightness uniform", () => {
    const calls = [];
    const node = {
        __cool_brightness_contrast_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: BRIGHTNESS_CONTRAST_PARAM_SPECS,
        },
    };

    const applied = apply_brightness_contrast_uniform_from_widget(
        node,
        "brightness",
        0.32,
    );

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_brightness", 0.32]]);
});

test("apply_brightness_contrast_uniform_from_widget updates contrast uniform", () => {
    const calls = [];
    const node = {
        __cool_brightness_contrast_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: BRIGHTNESS_CONTRAST_PARAM_SPECS,
        },
    };

    const applied = apply_brightness_contrast_uniform_from_widget(
        node,
        "contrast",
        -0.45,
    );

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_contrast", -0.45]]);
});
