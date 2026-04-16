import test from "node:test";
import assert from "node:assert/strict";

import {
    apply_text_overlay_animation,
    apply_text_overlay_position,
    map_animation_to_mode,
    map_position_to_anchor,
} from "../web/text_overlay_effect.js";

test("map_position_to_anchor resolves all supported positions", () => {
    assert.deepEqual(map_position_to_anchor("top-left"), [0.12, 0.88]);
    assert.deepEqual(map_position_to_anchor("top-center"), [0.5, 0.88]);
    assert.deepEqual(map_position_to_anchor("top-right"), [0.88, 0.88]);
    assert.deepEqual(map_position_to_anchor("center"), [0.5, 0.5]);
    assert.deepEqual(map_position_to_anchor("bottom-left"), [0.12, 0.12]);
    assert.deepEqual(map_position_to_anchor("bottom-center"), [0.5, 0.12]);
    assert.deepEqual(map_position_to_anchor("bottom-right"), [0.88, 0.12]);
});

test("map_position_to_anchor falls back to bottom-center for invalid values", () => {
    assert.deepEqual(map_position_to_anchor("invalid-value"), [0.5, 0.12]);
    assert.deepEqual(map_position_to_anchor(""), [0.5, 0.12]);
});

test("apply_text_overlay_position pushes anchor uniforms to preview controller", () => {
    const calls = [];
    const node = {
        __cool_text_overlay_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
        },
    };

    const applied = apply_text_overlay_position(node, "top-right");
    assert.equal(applied, true);
    assert.deepEqual(calls, [
        ["u_anchor_x", 0.88],
        ["u_anchor_y", 0.88],
    ]);
});

test("map_animation_to_mode resolves all supported animation styles", () => {
    assert.equal(map_animation_to_mode("none"), 0);
    assert.equal(map_animation_to_mode("fade_in"), 1);
    assert.equal(map_animation_to_mode("fade_in_out"), 2);
    assert.equal(map_animation_to_mode("slide_up"), 3);
    assert.equal(map_animation_to_mode("typewriter"), 4);
});

test("map_animation_to_mode falls back to fade_in for invalid values", () => {
    assert.equal(map_animation_to_mode("invalid"), 1);
    assert.equal(map_animation_to_mode(""), 1);
});

test("apply_text_overlay_animation pushes animation mode to preview controller", () => {
    const calls = [];
    const node = {
        __cool_text_overlay_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
        },
    };

    const applied = apply_text_overlay_animation(node, "slide_up");
    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_animation_mode", 3]]);
});
