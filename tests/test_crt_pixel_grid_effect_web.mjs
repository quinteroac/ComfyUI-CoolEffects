import test from "node:test";
import assert from "node:assert/strict";

import {
    CRT_PIXEL_GRID_PARAM_SPECS,
    apply_crt_pixel_grid_uniform_from_widget,
} from "../web/crt_pixel_grid_effect.js";

test("crt pixel grid param specs map controls to uniforms", () => {
    assert.deepEqual(CRT_PIXEL_GRID_PARAM_SPECS, [
        {
            widget_name: "pixel_size",
            uniform_name: "u_pixel_size",
            default_value: 6.0,
        },
        {
            widget_name: "grid_strength",
            uniform_name: "u_grid_strength",
            default_value: 0.6,
        },
        {
            widget_name: "scanline_strength",
            uniform_name: "u_scanline_strength",
            default_value: 0.4,
        },
    ]);
});

test("apply_crt_pixel_grid_uniform_from_widget updates near-identity preset", () => {
    const calls = [];
    const node = {
        __cool_crt_pixel_grid_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: CRT_PIXEL_GRID_PARAM_SPECS,
        },
    };

    const applied_grid = apply_crt_pixel_grid_uniform_from_widget(node, "grid_strength", 0.0);
    const applied_scanline = apply_crt_pixel_grid_uniform_from_widget(
        node,
        "scanline_strength",
        0.0,
    );

    assert.equal(applied_grid, true);
    assert.equal(applied_scanline, true);
    assert.deepEqual(calls, [
        ["u_grid_strength", 0.0],
        ["u_scanline_strength", 0.0],
    ]);
});

test("apply_crt_pixel_grid_uniform_from_widget updates strong CRT preset", () => {
    const calls = [];
    const node = {
        __cool_crt_pixel_grid_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: CRT_PIXEL_GRID_PARAM_SPECS,
        },
    };

    const applied_pixel_size = apply_crt_pixel_grid_uniform_from_widget(node, "pixel_size", 10);
    const applied_grid = apply_crt_pixel_grid_uniform_from_widget(node, "grid_strength", 1.0);
    const applied_scanline = apply_crt_pixel_grid_uniform_from_widget(
        node,
        "scanline_strength",
        1.0,
    );

    assert.equal(applied_pixel_size, true);
    assert.equal(applied_grid, true);
    assert.equal(applied_scanline, true);
    assert.deepEqual(calls, [
        ["u_pixel_size", 10],
        ["u_grid_strength", 1.0],
        ["u_scanline_strength", 1.0],
    ]);
});
