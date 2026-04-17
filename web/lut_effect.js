import {
    apply_effect_widget_uniform_from_widget,
    mount_effect_node_widget,
    stop_effect_node_widget_preview,
} from "./effect_node_widget.js";
import { loadShader } from "./shaders/loader.js";

export const EXTENSION_NAME = "Comfy.CoolEffects.LUTEffect";
const EFFECT_NAME = "lut";
const LUT_STATE_KEY = "__cool_lut_widget_state";
const LUT_ENDPOINT = "/cool_effects/lut";

export const LUT_PARAM_SPECS = Object.freeze([
    Object.freeze({
        widget_name: "intensity",
        uniform_name: "u_intensity",
        default_value: 1.0,
    }),
]);

function get_preview_controller(node) {
    return node?.[LUT_STATE_KEY]?.preview_state?.preview_controller ?? null;
}

function get_node_widget_value(node, widget_name, fallback_value = null) {
    const widgets = Array.isArray(node?.widgets) ? node.widgets : [];
    const widget = widgets.find((item) => item?.name === widget_name);
    return widget?.value ?? fallback_value;
}

function clamp_byte(value) {
    const normalized_value = Number(value);
    if (!Number.isFinite(normalized_value)) {
        return 0;
    }
    return Math.min(255, Math.max(0, Math.round(normalized_value)));
}

export async function fetch_lut_payload(
    lut_path,
    { fetch_impl = globalThis.fetch } = {},
) {
    const normalized_path = typeof lut_path === "string" ? lut_path.trim() : "";
    if (!normalized_path) {
        throw new Error("lut_path must be a non-empty string");
    }
    if (typeof fetch_impl !== "function") {
        throw new Error("fetch implementation is required for LUT loading");
    }

    const response = await fetch_impl(
        `${LUT_ENDPOINT}?path=${encodeURIComponent(normalized_path)}`,
    );
    if (!response.ok) {
        throw new Error(`Failed to load LUT: ${response.status}`);
    }

    const payload = await response.json();
    if (
        !payload ||
        typeof payload.size !== "number" ||
        !Array.isArray(payload.domain_min) ||
        !Array.isArray(payload.domain_max) ||
        !Array.isArray(payload.strip)
    ) {
        throw new Error("Invalid LUT payload");
    }
    return payload;
}

export function build_lut_strip_canvas(payload, document_ref = globalThis.document) {
    if (!document_ref || typeof document_ref.createElement !== "function") {
        throw new Error("Missing document reference for LUT texture");
    }

    const size = Number(payload?.size);
    if (!Number.isFinite(size) || size < 2) {
        throw new Error("Invalid LUT size");
    }

    const width = Math.round(size * size);
    const height = Math.round(size);
    const expected_rgb_count = width * height * 3;
    if (!Array.isArray(payload.strip) || payload.strip.length !== expected_rgb_count) {
        throw new Error("Invalid LUT strip length");
    }

    const canvas = document_ref.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    if (typeof canvas.getContext !== "function") {
        throw new Error("Canvas context unavailable for LUT texture");
    }

    const context = canvas.getContext("2d");
    if (!context || typeof context.createImageData !== "function") {
        throw new Error("2D canvas context unavailable for LUT texture");
    }

    const image_data = context.createImageData(width, height);
    for (let source_index = 0, target_index = 0; source_index < payload.strip.length; source_index += 3) {
        image_data.data[target_index] = clamp_byte(payload.strip[source_index]);
        image_data.data[target_index + 1] = clamp_byte(payload.strip[source_index + 1]);
        image_data.data[target_index + 2] = clamp_byte(payload.strip[source_index + 2]);
        image_data.data[target_index + 3] = 255;
        target_index += 4;
    }
    context.putImageData(image_data, 0, 0);
    return canvas;
}

export async function apply_lut_path_to_preview(
    node,
    lut_path,
    {
        document_ref = globalThis.document,
        fetch_impl = globalThis.fetch,
    } = {},
) {
    const preview_controller = get_preview_controller(node);
    if (!preview_controller || typeof preview_controller.set_texture !== "function") {
        return false;
    }

    const normalized_path = typeof lut_path === "string" ? lut_path.trim() : "";
    if (!normalized_path) {
        return false;
    }

    const payload = await fetch_lut_payload(normalized_path, { fetch_impl });
    const lut_canvas = build_lut_strip_canvas(payload, document_ref);

    preview_controller.set_texture("u_lut_texture", lut_canvas);
    preview_controller.set_uniform("u_lut_size", Number(payload.size));
    if (typeof preview_controller.set_uniform_array === "function") {
        preview_controller.set_uniform_array("u_domain_min", payload.domain_min);
        preview_controller.set_uniform_array("u_domain_max", payload.domain_max);
    }

    return true;
}

function clear_lut_preview(node) {
    const preview_controller = get_preview_controller(node);
    if (!preview_controller || typeof preview_controller.set_texture !== "function") {
        return false;
    }
    preview_controller.set_texture("u_lut_texture", null);
    preview_controller.set_uniform("u_lut_size", 2.0);
    if (typeof preview_controller.set_uniform_array === "function") {
        preview_controller.set_uniform_array("u_domain_min", [0.0, 0.0, 0.0]);
        preview_controller.set_uniform_array("u_domain_max", [1.0, 1.0, 1.0]);
    }
    return true;
}

async function refresh_lut_preview(node, lut_path, { document_ref, fetch_impl } = {}) {
    try {
        await apply_lut_path_to_preview(node, lut_path, {
            document_ref,
            fetch_impl,
        });
    } catch (_error) {
        clear_lut_preview(node);
    }
}

export function apply_lut_uniform_from_widget(node, widget_name, widget_value) {
    return apply_effect_widget_uniform_from_widget(
        node,
        EFFECT_NAME,
        LUT_PARAM_SPECS,
        widget_name,
        widget_value,
    );
}

export async function mount_lut_effect_widget_for_node({
    node,
    document_ref = globalThis.document,
    shader_loader = loadShader,
    request_animation_frame = globalThis.requestAnimationFrame,
    cancel_animation_frame = globalThis.cancelAnimationFrame,
    fetch_impl = globalThis.fetch,
    now = () =>
        globalThis.performance && typeof globalThis.performance.now === "function"
            ? globalThis.performance.now()
            : Date.now(),
}) {
    const widget_state = await mount_effect_node_widget(node, EFFECT_NAME, LUT_PARAM_SPECS, {
        document_ref,
        shader_loader,
        request_animation_frame,
        cancel_animation_frame,
        now,
    });
    if (!widget_state) {
        return widget_state;
    }

    clear_lut_preview(node);

    const initial_lut_path = get_node_widget_value(node, "lut_path", "");
    if (typeof initial_lut_path === "string" && initial_lut_path.trim().length > 0) {
        await refresh_lut_preview(node, initial_lut_path, {
            document_ref,
            fetch_impl,
        });
    }
    return widget_state;
}

export function register_comfy_extension(
    app_ref,
    {
        document_ref = globalThis.document,
        shader_loader = loadShader,
        request_animation_frame = globalThis.requestAnimationFrame,
        cancel_animation_frame = globalThis.cancelAnimationFrame,
        fetch_impl = globalThis.fetch,
        now = () =>
            globalThis.performance && typeof globalThis.performance.now === "function"
                ? globalThis.performance.now()
                : Date.now(),
    } = {},
) {
    if (!app_ref || typeof app_ref.registerExtension !== "function") {
        return false;
    }

    app_ref.registerExtension({
        name: EXTENSION_NAME,
        async beforeRegisterNodeDef(nodeType, nodeData) {
            if (nodeData?.name !== "CoolLUTEffect") {
                return;
            }
            const previous_on_node_created = nodeType.prototype.onNodeCreated;
            const previous_on_removed = nodeType.prototype.onRemoved;
            const previous_on_widget_changed = nodeType.prototype.onWidgetChanged;

            nodeType.prototype.onNodeCreated = async function onNodeCreated() {
                if (typeof previous_on_node_created === "function") {
                    previous_on_node_created.apply(this, arguments);
                }
                await mount_lut_effect_widget_for_node({
                    node: this,
                    document_ref,
                    shader_loader,
                    request_animation_frame,
                    cancel_animation_frame,
                    fetch_impl,
                    now,
                });
            };

            nodeType.prototype.onRemoved = function onRemoved() {
                stop_effect_node_widget_preview(this, EFFECT_NAME);
                if (typeof previous_on_removed === "function") {
                    previous_on_removed.apply(this, arguments);
                }
            };

            nodeType.prototype.onWidgetChanged = function onWidgetChanged() {
                if (typeof previous_on_widget_changed === "function") {
                    previous_on_widget_changed.apply(this, arguments);
                }
                const [widget_name, widget_value] = arguments;
                if (widget_name === "lut_path") {
                    void refresh_lut_preview(this, widget_value, {
                        document_ref,
                        fetch_impl,
                    });
                    return;
                }
                apply_lut_uniform_from_widget(this, widget_name, widget_value);
            };
        },
    });

    return true;
}

export async function auto_register_comfy_extension() {
    let app_ref = globalThis.app;
    if (!app_ref) {
        try {
            const app_module = await import("../../scripts/app.js");
            app_ref = app_module.app;
        } catch (_error) {
            app_ref = null;
        }
    }
    if (app_ref) {
        register_comfy_extension(app_ref);
    }
}

void auto_register_comfy_extension();
