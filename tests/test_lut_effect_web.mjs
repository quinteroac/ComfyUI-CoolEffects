import test from "node:test";
import assert from "node:assert/strict";

import {
    LUT_PARAM_SPECS,
    apply_lut_path_to_preview,
    apply_lut_uniform_from_widget,
    build_lut_strip_canvas,
    fetch_lut_payload,
} from "../web/lut_effect.js";

function create_fake_canvas_document() {
    let last_image_data = null;
    const context = {
        createImageData(width, height) {
            return {
                width,
                height,
                data: new Uint8ClampedArray(width * height * 4),
            };
        },
        putImageData(image_data) {
            last_image_data = image_data;
        },
    };
    const canvas = {
        width: 0,
        height: 0,
        getContext(type) {
            if (type !== "2d") {
                return null;
            }
            return context;
        },
    };
    const document_ref = {
        createElement(name) {
            if (name !== "canvas") {
                throw new Error(`Unsupported element: ${name}`);
            }
            return canvas;
        },
    };
    return {
        document_ref,
        canvas,
        get_image_data() {
            return last_image_data;
        },
    };
}

test("lut param specs map controls to uniforms", () => {
    assert.deepEqual(LUT_PARAM_SPECS, [
        {
            widget_name: "intensity",
            uniform_name: "u_intensity",
            default_value: 1.0,
        },
    ]);
});

test("apply_lut_uniform_from_widget updates intensity uniform", () => {
    const calls = [];
    const node = {
        __cool_lut_widget_state: {
            preview_state: {
                preview_controller: {
                    set_uniform(name, value) {
                        calls.push([name, value]);
                    },
                },
            },
            param_specs: LUT_PARAM_SPECS,
        },
    };

    const applied = apply_lut_uniform_from_widget(node, "intensity", 0.42);

    assert.equal(applied, true);
    assert.deepEqual(calls, [["u_intensity", 0.42]]);
});

test("fetch_lut_payload validates successful payloads", async () => {
    const payload = await fetch_lut_payload("tests/fixtures/sample_lut.cube", {
        fetch_impl: async () => ({
            ok: true,
            async json() {
                return {
                    size: 2,
                    domain_min: [0, 0, 0],
                    domain_max: [1, 1, 1],
                    strip: [0, 0, 0, 255, 255, 255, 127, 127, 127, 64, 64, 64],
                };
            },
        }),
    });

    assert.equal(payload.size, 2);
    assert.deepEqual(payload.domain_min, [0, 0, 0]);
    assert.deepEqual(payload.domain_max, [1, 1, 1]);
});

test("build_lut_strip_canvas builds RGBA texture data", () => {
    const { document_ref, canvas, get_image_data } = create_fake_canvas_document();
    const payload = {
        size: 2,
        strip: [
            0, 10, 20,
            30, 40, 50,
            60, 70, 80,
            90, 100, 110,
            120, 130, 140,
            150, 160, 170,
            180, 190, 200,
            210, 220, 230,
        ],
    };

    build_lut_strip_canvas(payload, document_ref);

    assert.equal(canvas.width, 4);
    assert.equal(canvas.height, 2);
    const image_data = get_image_data();
    assert.ok(image_data);
    assert.deepEqual(Array.from(image_data.data.slice(0, 8)), [0, 10, 20, 255, 30, 40, 50, 255]);
});

test("apply_lut_path_to_preview sets texture and LUT uniforms", async () => {
    const calls = [];
    const { document_ref } = create_fake_canvas_document();
    const node = {
        __cool_lut_widget_state: {
            preview_state: {
                preview_controller: {
                    set_texture(name, texture_source) {
                        calls.push(["set_texture", name, Boolean(texture_source)]);
                    },
                    set_uniform(name, value) {
                        calls.push(["set_uniform", name, value]);
                    },
                    set_uniform_array(name, value) {
                        calls.push(["set_uniform_array", name, value]);
                    },
                },
            },
        },
    };

    const applied = await apply_lut_path_to_preview(node, "tests/fixtures/sample_lut.cube", {
        document_ref,
        fetch_impl: async () => ({
            ok: true,
            async json() {
                return {
                    size: 2,
                    domain_min: [0.0, 0.0, 0.0],
                    domain_max: [1.0, 1.0, 1.0],
                    strip: [
                        0, 0, 0,
                        255, 0, 0,
                        0, 255, 0,
                        255, 255, 0,
                        0, 0, 255,
                        255, 0, 255,
                        0, 255, 255,
                        255, 255, 255,
                    ],
                };
            },
        }),
    });

    assert.equal(applied, true);
    assert.deepEqual(calls, [
        ["set_texture", "u_lut_texture", true],
        ["set_uniform", "u_lut_size", 2],
        ["set_uniform_array", "u_domain_min", [0.0, 0.0, 0.0]],
        ["set_uniform_array", "u_domain_max", [1.0, 1.0, 1.0]],
    ]);
});
