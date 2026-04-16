import test from "node:test";
import assert from "node:assert/strict";

import {
    TILT_SHIFT_PARAM_SPECS,
    apply_tilt_shift_uniform_from_widget,
} from "../web/tilt_shift_effect.js";

test("tilt-shift param specs map controls to uniforms", () => {
    assert.deepEqual(TILT_SHIFT_PARAM_SPECS, [
        {
            widget_name: "focus_center",
            uniform_name: "u_focus_center",
            default_value: 0.5,
        },
        {
            widget_name: "focus_width",
            uniform_name: "u_focus_width",
            default_value: 0.2,
        },
        {
            widget_name: "blur_strength",
            uniform_name: "u_blur_strength",
            default_value: 0.5,
        },
        {
            widget_name: "angle",
            uniform_name: "u_angle",
            default_value: 0.0,
        },
    ]);
});

test("apply_tilt_shift_uniform_from_widget updates focus_center uniform", () => {
    const calls = [];
    const node = {
        __cool_tilt_shift_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: TILT_SHIFT_PARAM_SPECS,
        },
    };

    const applied = apply_tilt_shift_uniform_from_widget(node, "focus_center", 0.73);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_focus_center", 0.73]]);
});

test("apply_tilt_shift_uniform_from_widget updates focus_width uniform", () => {
    const calls = [];
    const node = {
        __cool_tilt_shift_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: TILT_SHIFT_PARAM_SPECS,
        },
    };

    const applied = apply_tilt_shift_uniform_from_widget(node, "focus_width", 0.36);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_focus_width", 0.36]]);
});

test("apply_tilt_shift_uniform_from_widget updates blur_strength uniform", () => {
    const calls = [];
    const node = {
        __cool_tilt_shift_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: TILT_SHIFT_PARAM_SPECS,
        },
    };

    const applied = apply_tilt_shift_uniform_from_widget(node, "blur_strength", 0.61);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_blur_strength", 0.61]]);
});

test("apply_tilt_shift_uniform_from_widget updates angle uniform", () => {
    const calls = [];
    const node = {
        __cool_tilt_shift_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: TILT_SHIFT_PARAM_SPECS,
        },
    };

    const applied = apply_tilt_shift_uniform_from_widget(node, "angle", 45.0);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_angle", 45]]);
});
