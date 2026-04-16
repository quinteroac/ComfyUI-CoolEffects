import test from "node:test";
import assert from "node:assert/strict";

import {
    apply_text_overlay_animation,
    apply_text_overlay_position,
    build_text_overlay_preview_texture,
    map_animation_to_mode,
    map_position_to_anchor,
    sync_text_overlay_preview_content,
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

test("build_text_overlay_preview_texture draws text at requested anchor", () => {
    const draw_calls = [];
    const fake_context = {
        clearRect() {},
        fillStyle: "",
        font: "",
        textAlign: "",
        textBaseline: "",
        measureText(text) {
            return { width: text.length * 24 };
        },
        fillText(text, x, y, max_width) {
            draw_calls.push({ text, x, y, max_width });
        },
    };
    const fake_canvas = {
        width: 0,
        height: 0,
        getContext(type) {
            return type === "2d" ? fake_context : null;
        },
    };
    const fake_document = {
        createElement(tag_name) {
            assert.equal(tag_name, "canvas");
            return fake_canvas;
        },
    };

    const texture = build_text_overlay_preview_texture(fake_document, {
        text: "Overlay",
        font: "dejavu_sans.ttf",
        font_size: 56,
        position: "top-right",
        offset_x: -0.1,
        offset_y: 0.05,
    });

    assert.equal(texture, fake_canvas);
    assert.equal(fake_canvas.width, 512);
    assert.equal(fake_canvas.height, 512);
    assert.equal(draw_calls.length, 1);
    assert.ok(draw_calls[0].x > 0);
    assert.ok(draw_calls[0].y > 0);
});

test("sync_text_overlay_preview_content pushes text texture and enable flag", () => {
    const texture_calls = [];
    const uniform_calls = [];
    const fake_context = {
        clearRect() {},
        fillStyle: "",
        font: "",
        textAlign: "",
        textBaseline: "",
        measureText(text) {
            return { width: text.length * 18 };
        },
        fillText() {},
    };
    const fake_canvas = {
        width: 0,
        height: 0,
        getContext(type) {
            return type === "2d" ? fake_context : null;
        },
    };
    const fake_document = {
        createElement() {
            return fake_canvas;
        },
    };
    const node = {
        widgets: [
            { name: "text", value: "Real-time preview" },
            { name: "font", value: "dejavu_sans.ttf" },
            { name: "font_size", value: 48 },
            { name: "position", value: "bottom-center" },
            { name: "offset_x", value: 0 },
            { name: "offset_y", value: 0 },
        ],
        __cool_text_overlay_widget_state: {
            preview_state: {
                preview_controller: {
                    set_texture(name, value) {
                        texture_calls.push([name, value]);
                    },
                    set_uniform(name, value) {
                        uniform_calls.push([name, value]);
                    },
                },
            },
        },
    };

    const applied = sync_text_overlay_preview_content(node, fake_document);

    assert.equal(applied, true);
    assert.equal(texture_calls.length, 1);
    assert.equal(texture_calls[0][0], "u_text_texture");
    assert.equal(texture_calls[0][1], fake_canvas);
    assert.deepEqual(uniform_calls, [["u_has_text_texture", 1]]);
});
