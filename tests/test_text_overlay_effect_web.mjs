import test from "node:test";
import assert from "node:assert/strict";

import {
    apply_text_overlay_position,
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
