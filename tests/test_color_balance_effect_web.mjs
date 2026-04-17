import test from "node:test";
import assert from "node:assert/strict";

import {
    COLOR_BALANCE_PARAM_SPECS,
    apply_color_balance_uniform_from_widget,
} from "../web/color_balance_effect.js";

test("color balance param specs map controls to uniforms", () => {
    assert.deepEqual(COLOR_BALANCE_PARAM_SPECS, [
        { widget_name: "shadows_r", uniform_name: "u_shadows_r", default_value: 0.0 },
        { widget_name: "shadows_g", uniform_name: "u_shadows_g", default_value: 0.0 },
        { widget_name: "shadows_b", uniform_name: "u_shadows_b", default_value: 0.0 },
        { widget_name: "midtones_r", uniform_name: "u_midtones_r", default_value: 0.0 },
        { widget_name: "midtones_g", uniform_name: "u_midtones_g", default_value: 0.0 },
        { widget_name: "midtones_b", uniform_name: "u_midtones_b", default_value: 0.0 },
        { widget_name: "highlights_r", uniform_name: "u_highlights_r", default_value: 0.0 },
        { widget_name: "highlights_g", uniform_name: "u_highlights_g", default_value: 0.0 },
        { widget_name: "highlights_b", uniform_name: "u_highlights_b", default_value: 0.0 },
    ]);
});

test("apply_color_balance_uniform_from_widget updates shadows and midtones uniforms", () => {
    const calls = [];
    const node = {
        __cool_color_balance_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: COLOR_BALANCE_PARAM_SPECS,
        },
    };

    const shadows_applied = apply_color_balance_uniform_from_widget(node, "shadows_r", -0.75);
    const midtones_applied = apply_color_balance_uniform_from_widget(node, "midtones_g", 0.45);

    assert.equal(shadows_applied, true);
    assert.equal(midtones_applied, true);
    assert.deepEqual(calls, [
        ["u_shadows_r", -0.75],
        ["u_midtones_g", 0.45],
    ]);
});

test("apply_color_balance_uniform_from_widget updates highlights uniforms", () => {
    const calls = [];
    const node = {
        __cool_color_balance_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: COLOR_BALANCE_PARAM_SPECS,
        },
    };

    const highlight_applied = apply_color_balance_uniform_from_widget(
        node,
        "highlights_b",
        -0.25,
    );

    assert.equal(highlight_applied, true);
    assert.deepEqual(calls, [["u_highlights_b", -0.25]]);
});

test("apply_color_balance_uniform_from_widget ignores non-numeric values", () => {
    const calls = [];
    const node = {
        __cool_color_balance_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: COLOR_BALANCE_PARAM_SPECS,
        },
    };

    const applied = apply_color_balance_uniform_from_widget(node, "shadows_g", "not-a-number");

    assert.equal(applied, false);
    assert.deepEqual(calls, []);
});
