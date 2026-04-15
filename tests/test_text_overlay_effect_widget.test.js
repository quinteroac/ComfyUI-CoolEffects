import { describe, expect, test } from "bun:test";

import {
    normalize_overlay_fragments,
    patch_preview_widget_callbacks,
    render_overlay_text,
    render_preview_frame,
    update_preview_layout,
} from "../web/text_overlay_effect.js";

function create_mock_node(overrides = {}) {
    const widget_values = {
        text: "Cool Text",
        font_family: "arial",
        font_size: 48,
        color: "#ffffff",
        font_weight: "normal",
        pos_x: 0.5,
        pos_y: 0.1,
        align: "center",
        opacity: 1.0,
        fragments: "[]",
        ...overrides,
    };
    const widgets = Object.entries(widget_values).map(([name, value]) => ({
        name,
        value,
        callback: null,
    }));

    const node = {
        widgets,
        inputs: [{ name: "video", link: 1 }],
        size: [400, 240],
        dirty_calls: 0,
        setDirtyCanvas() {
            this.dirty_calls += 1;
        },
        setSize(size) {
            this.size = size;
        },
    };
    return node;
}

function create_mock_canvas_context() {
    const calls = {
        drawImage: 0,
        fillText: [],
        clearRect: 0,
    };
    const ctx = {
        globalAlpha: 1,
        textBaseline: "alphabetic",
        font: "",
        fillStyle: "",
        measureText(text) {
            return { width: String(text).length * 10 };
        },
        fillText(text, x, y) {
            calls.fillText.push({ text, x, y, font: this.font, fillStyle: this.fillStyle });
        },
        drawImage() {
            calls.drawImage += 1;
        },
        clearRect() {
            calls.clearRect += 1;
        },
        save() {},
        restore() {},
    };
    return { ctx, calls };
}

describe("CoolTextOverlay widget preview", () => {
    test("US-001-AC01: renders first video frame as preview background", () => {
        const node = create_mock_node();
        const { ctx, calls } = create_mock_canvas_context();
        const canvas = { width: 0, height: 0, style: {} };
        const state = {
            node,
            canvas_element: canvas,
            context: ctx,
            status_element: { textContent: "" },
            video_element: {
                readyState: 4,
                videoWidth: 640,
                videoHeight: 360,
            },
        };

        const rendered = render_preview_frame(state);

        expect(rendered).toBe(true);
        expect(calls.drawImage).toBe(1);
        expect(canvas.width).toBe(640);
        expect(canvas.height).toBe(360);
    });

    test("US-001-AC02: draws single text and rich inline fragments on top", () => {
        const { ctx, calls } = create_mock_canvas_context();
        const single_state = {
            node: create_mock_node({ text: "SINGLE", fragments: "[]" }),
            canvas_element: { width: 640, height: 360 },
            context: ctx,
        };
        render_overlay_text(single_state);
        expect(calls.fillText.length).toBe(1);
        expect(calls.fillText[0].text).toBe("SINGLE");

        const { ctx: rich_context, calls: rich_calls } = create_mock_canvas_context();
        const rich_state = {
            node: create_mock_node({
                text: "fallback",
                fragments: '[{"text":"A","color":"#ff0000"},{"text":"B","color":"#00ff00"}]',
            }),
            canvas_element: { width: 640, height: 360 },
            context: rich_context,
        };
        render_overlay_text(rich_state);
        expect(rich_calls.fillText.map((entry) => entry.text)).toEqual(["A", "B"]);
    });

    test("US-001-AC03: widget value changes trigger immediate rerender", () => {
        const node = create_mock_node();
        const state = {
            node,
            context: {
                globalAlpha: 1,
                textBaseline: "alphabetic",
                font: "",
                fillStyle: "",
                measureText() {
                    return { width: 1 };
                },
                fillText() {},
                clearRect() {},
                drawImage() {},
                save() {},
                restore() {},
            },
            canvas_element: { width: 16, height: 9, style: {} },
            video_element: { readyState: 4, videoWidth: 16, videoHeight: 9 },
            status_element: { textContent: "" },
        };

        patch_preview_widget_callbacks(node, state);
        const text_widget = node.widgets.find((widget) => widget.name === "text");
        expect(typeof text_widget.callback).toBe("function");

        const before = node.dirty_calls;
        text_widget.callback("Updated");
        expect(node.dirty_calls).toBeGreaterThan(before);
    });

    test("US-001-AC04: preview keeps source aspect ratio and scales to node width", () => {
        const node = create_mock_node();
        const state = {
            node,
            canvas_element: { style: {} },
            widget: { computeSize: null },
        };

        update_preview_layout(state, 1920, 1080);
        const size = state.widget.computeSize();

        expect(state.canvas_element.style.aspectRatio).toBe("1920 / 1080");
        expect(size[0]).toBeGreaterThanOrEqual(180);
        const expected_height = Math.max(100, Math.round((size[0] * 1080) / 1920)) + 44;
        expect(size[1]).toBe(expected_height);
    });

    test("normalize_overlay_fragments falls back on invalid JSON", () => {
        const node = create_mock_node({
            text: "Fallback",
            fragments: "{not-json",
        });
        const fragments = normalize_overlay_fragments(node);
        expect(fragments).toHaveLength(1);
        expect(fragments[0].text).toBe("Fallback");
    });
});
