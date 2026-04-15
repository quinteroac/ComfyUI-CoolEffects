import { afterEach, describe, expect, test } from "bun:test";

import {
    PRETEXT_CDN_URL,
    PRETEXT_VENDOR_URL,
    load_pretext_rich_inline_module,
    mount_text_overlay_widget,
    normalize_overlay_fragments,
    patch_preview_widget_callbacks,
    read_fragment_editor_fragments,
    render_overlay_text,
    render_preview_frame,
    serialize_fragment_editor_fragments,
    set_pretext_dynamic_import_for_tests,
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

function create_mock_fragment_editor_document() {
    class MockElement {
        constructor(tag_name) {
            this.tagName = String(tag_name).toUpperCase();
            this.children = [];
            this.style = {};
            this.attributes = {};
            this.listeners = new Map();
            this.dataset = {};
            this.value = "";
            this._textContent = "";
            this.type = "";
            this.disabled = false;
        }

        append(...nodes) {
            this.children.push(...nodes);
        }

        setAttribute(name, value) {
            this.attributes[name] = String(value);
        }

        addEventListener(name, callback) {
            if (!this.listeners.has(name)) {
                this.listeners.set(name, []);
            }
            this.listeners.get(name).push(callback);
        }

        dispatch(name) {
            for (const callback of this.listeners.get(name) ?? []) {
                callback({ target: this });
            }
        }

        click() {
            this.dispatch("click");
        }

        get textContent() {
            return this._textContent;
        }

        set textContent(value) {
            this._textContent = String(value ?? "");
            if (this._textContent.length === 0) {
                this.children = [];
            }
        }

        queryByDataField(field_name) {
            if (this.attributes["data-fragment-field"] === field_name) {
                return this;
            }
            for (const child of this.children) {
                const found = child?.queryByDataField?.(field_name);
                if (found) {
                    return found;
                }
            }
            return null;
        }
    }

    return {
        createElement(tag_name) {
            const element = new MockElement(tag_name);
            if (String(tag_name).toLowerCase() === "canvas") {
                const { ctx } = create_mock_canvas_context();
                element.getContext = () => ctx;
            }
            if (String(tag_name).toLowerCase() === "video") {
                element.readyState = 0;
                element.videoWidth = 0;
                element.videoHeight = 0;
                element.load = () => {};
                element.pause = () => {};
            }
            return element;
        },
    };
}

function create_mock_dom_node(overrides = {}) {
    const node = create_mock_node(overrides);
    node.addDOMWidget = function (_name, _type, container) {
        return { element: container, computeSize: null };
    };
    return node;
}

describe("CoolTextOverlay widget preview", () => {
    test("US-002-AC01: pretext rich-inline module loads from CDN with vendor fallback", async () => {
        const attempted = [];
        const fake_module = { prepareRichInline() {} };
        const loaded = await load_pretext_rich_inline_module(async (source_url) => {
            attempted.push(source_url);
            if (source_url === PRETEXT_CDN_URL) {
                throw new Error("cdn unavailable");
            }
            if (source_url === PRETEXT_VENDOR_URL) {
                return fake_module;
            }
            throw new Error(`Unexpected import URL: ${source_url}`);
        });

        expect(loaded).toBe(fake_module);
        expect(attempted).toEqual([PRETEXT_CDN_URL, PRETEXT_VENDOR_URL]);
    });

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

    test("US-002-AC02/AC03/AC04: prepareRichInline widths drive centered fragment layout", async () => {
        const prepare_calls = [];
        set_pretext_dynamic_import_for_tests(async (source_url) => {
            if (source_url !== PRETEXT_CDN_URL) {
                throw new Error("expected CDN URL first");
            }
            return {
                prepareRichInline(specs, context) {
                    prepare_calls.push({ specs, context });
                    return { specs };
                },
                layoutNextRichInlineLineRange(prepared) {
                    return {
                        fragments: prepared.specs.map((item) => ({
                            occupiedWidth: item.text === "AA" ? 50 : 30,
                        })),
                    };
                },
            };
        });

        const { ctx, calls } = create_mock_canvas_context();
        const canvas = { width: 200, height: 100, style: {} };
        const node = create_mock_node({
            align: "center",
            pos_x: 0.5,
            pos_y: 0.5,
            fragments: '[{"text":"AA","color":"#ff0000"},{"text":"B","color":"#00ff00"}]',
        });
        const state = {
            node,
            canvas_element: canvas,
            context: ctx,
            status_element: { textContent: "" },
            video_element: { readyState: 4, videoWidth: 200, videoHeight: 100 },
        };

        await load_pretext_rich_inline_module();
        render_overlay_text(state);

        expect(prepare_calls).toHaveLength(1);
        expect(prepare_calls[0].specs).toEqual([
            { text: "AA", font: "normal 48px arial" },
            { text: "B", font: "normal 48px arial" },
        ]);
        expect(prepare_calls[0].context).toBe(ctx);
        expect(calls.fillText).toHaveLength(2);
        expect(calls.fillText[0].x).toBe(60);
        expect(calls.fillText[1].x).toBe(110);
    });

    test("US-003-AC01: fragment editor renders rows with all fragment field inputs", () => {
        const document_ref = create_mock_fragment_editor_document();
        const node = create_mock_dom_node({
            fragments:
                '[{"text":"One","color":"#ff0000","font_size":32,"font_family":"serif","font_weight":"bold"},' +
                '{"text":"Two","color":"#00ff00","font_size":28,"font_family":"sans","font_weight":"normal"}]',
        });

        const state = mount_text_overlay_widget({ node, document_ref, api_ref: null });
        const rows = state.fragment_rows_container.children;

        expect(rows).toHaveLength(2);
        const first_row = rows[0];
        expect(first_row.queryByDataField("text")).not.toBeNull();
        expect(first_row.queryByDataField("color")).not.toBeNull();
        expect(first_row.queryByDataField("font_size")).not.toBeNull();
        expect(first_row.queryByDataField("font_family")).not.toBeNull();
        expect(first_row.queryByDataField("font_weight")).not.toBeNull();
        expect(first_row.queryByDataField("remove")).not.toBeNull();
    });

    test("US-003-AC02: Add fragment appends defaults from node-level style controls", () => {
        const document_ref = create_mock_fragment_editor_document();
        const node = create_mock_dom_node({
            text: "Node Default",
            font_family: "serif",
            font_size: 64,
            color: "#00ff00",
            font_weight: "bold",
            fragments: '[{"text":"Existing","color":"#ffffff","font_size":40,"font_family":"arial","font_weight":"normal"}]',
        });

        const state = mount_text_overlay_widget({ node, document_ref, api_ref: null });
        state.fragment_add_button.click();

        expect(state.fragment_rows).toHaveLength(2);
        const appended = state.fragment_rows[1];
        expect(appended).toEqual({
            text: "Node Default",
            font_size: 64,
            font_family: "serif",
            font_weight: "bold",
            color: "#00ff00",
        });
    });

    test("US-003-AC03: Remove deletes fragments but enforces minimum row count of one", () => {
        const document_ref = create_mock_fragment_editor_document();
        const node = create_mock_dom_node({
            fragments:
                '[{"text":"A","color":"#ffffff","font_size":48,"font_family":"arial","font_weight":"normal"},' +
                '{"text":"B","color":"#ffffff","font_size":48,"font_family":"arial","font_weight":"normal"}]',
        });

        const state = mount_text_overlay_widget({ node, document_ref, api_ref: null });
        const first_remove = state.fragment_rows_container.children[0].queryByDataField("remove");
        first_remove.click();
        expect(state.fragment_rows).toHaveLength(1);

        const only_remove = state.fragment_rows_container.children[0].queryByDataField("remove");
        only_remove.click();
        expect(state.fragment_rows).toHaveLength(1);
        expect(only_remove.disabled).toBe(true);
    });

    test("US-003-AC04/AC05: editing fragment fields serializes JSON to widget and triggers preview refresh", () => {
        const document_ref = create_mock_fragment_editor_document();
        let fragment_callback_count = 0;
        const node = create_mock_dom_node({
            fragments: '[{"text":"A","color":"#ffffff","font_size":48,"font_family":"arial","font_weight":"normal"}]',
        });
        const fragment_widget = node.widgets.find((widget) => widget.name === "fragments");
        fragment_widget.callback = () => {
            fragment_callback_count += 1;
        };

        const state = mount_text_overlay_widget({ node, document_ref, api_ref: null });
        const text_input = state.fragment_rows_container.children[0].queryByDataField("text");
        text_input.value = "Updated";
        const before_dirty = node.dirty_calls;
        text_input.dispatch("input");

        const serialized = fragment_widget.value;
        const parsed = JSON.parse(serialized);
        expect(parsed[0].text).toBe("Updated");
        expect(fragment_callback_count).toBeGreaterThan(0);
        expect(node.dirty_calls).toBeGreaterThan(before_dirty);
    });

    test("fragment editor read/serialize helpers normalize malformed fragment payloads", () => {
        const node = create_mock_node({
            text: "Fallback",
            font_family: "arial",
            font_size: 48,
            color: "#ffffff",
            font_weight: "normal",
            fragments: '[{"text":"X","font_size":"bad","font_weight":"invalid","color":"nope"}]',
        });
        const rows = read_fragment_editor_fragments(node);
        expect(rows).toEqual([
            {
                text: "X",
                font_size: 48,
                font_family: "arial",
                font_weight: "normal",
                color: "#ffffff",
            },
        ]);
        expect(serialize_fragment_editor_fragments(rows)).toBe(
            '[{"text":"X","font_size":48,"font_family":"arial","font_weight":"normal","color":"#ffffff"}]',
        );
    });
});

afterEach(() => {
    set_pretext_dynamic_import_for_tests(null);
});
