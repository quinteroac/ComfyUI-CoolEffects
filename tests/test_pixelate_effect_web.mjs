import test from "node:test";
import assert from "node:assert/strict";

import {
    PIXELATE_PARAM_SPECS,
    apply_pixelate_uniform_from_widget,
} from "../web/pixelate_effect.js";

test("pixelate param specs map widgets to uniforms", () => {
    assert.deepEqual(PIXELATE_PARAM_SPECS, [
        {
            widget_name: "pixel_size",
            uniform_name: "u_pixel_size",
            default_value: 8.0,
        },
        {
            widget_name: "aspect_ratio",
            uniform_name: "u_aspect_ratio",
            default_value: 1.0,
        },
    ]);
});

test("apply_pixelate_uniform_from_widget updates identity preset values", () => {
    const calls = [];
    const node = {
        __cool_pixelate_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: PIXELATE_PARAM_SPECS,
        },
    };

    const applied_pixel = apply_pixelate_uniform_from_widget(node, "pixel_size", 1);
    const applied_aspect = apply_pixelate_uniform_from_widget(node, "aspect_ratio", 1.0);

    assert.equal(applied_pixel, true);
    assert.equal(applied_aspect, true);
    assert.deepEqual(calls, [
        ["u_pixel_size", 1],
        ["u_aspect_ratio", 1.0],
    ]);
});

test("apply_pixelate_uniform_from_widget updates chunky wide-pixel preset values", () => {
    const calls = [];
    const node = {
        __cool_pixelate_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: PIXELATE_PARAM_SPECS,
        },
    };

    const applied_pixel = apply_pixelate_uniform_from_widget(node, "pixel_size", 32);
    const applied_aspect = apply_pixelate_uniform_from_widget(node, "aspect_ratio", 2.0);

    assert.equal(applied_pixel, true);
    assert.equal(applied_aspect, true);
    assert.deepEqual(calls, [
        ["u_pixel_size", 32],
        ["u_aspect_ratio", 2.0],
    ]);
});
