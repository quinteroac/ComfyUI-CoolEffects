import {
    apply_effect_widget_uniform_from_widget,
    mount_effect_node_widget,
    stop_effect_node_widget_preview,
} from "./effect_node_widget.js";
import { loadShader } from "./shaders/loader.js";

export const EXTENSION_NAME = "Comfy.CoolEffects.TextOverlayEffect";
const EFFECT_NAME = "text_overlay";
const TEXT_OVERLAY_STATE_KEY = "__cool_text_overlay_widget_state";

const TEXT_OVERLAY_PARAM_SPECS = Object.freeze([
    Object.freeze({
        widget_name: "font_size",
        uniform_name: "u_font_size",
        default_value: 48.0,
    }),
    Object.freeze({
        widget_name: "color_r",
        uniform_name: "u_color_r",
        default_value: 1.0,
    }),
    Object.freeze({
        widget_name: "color_g",
        uniform_name: "u_color_g",
        default_value: 1.0,
    }),
    Object.freeze({
        widget_name: "color_b",
        uniform_name: "u_color_b",
        default_value: 1.0,
    }),
    Object.freeze({
        widget_name: "opacity",
        uniform_name: "u_opacity",
        default_value: 1.0,
    }),
    Object.freeze({
        widget_name: "offset_x",
        uniform_name: "u_offset_x",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "offset_y",
        uniform_name: "u_offset_y",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "animation_duration",
        uniform_name: "u_animation_duration",
        default_value: 0.5,
    }),
]);

const POSITION_ANCHORS = Object.freeze({
    "top-left": Object.freeze([0.12, 0.88]),
    "top-center": Object.freeze([0.5, 0.88]),
    "top-right": Object.freeze([0.88, 0.88]),
    center: Object.freeze([0.5, 0.5]),
    "bottom-left": Object.freeze([0.12, 0.12]),
    "bottom-center": Object.freeze([0.5, 0.12]),
    "bottom-right": Object.freeze([0.88, 0.12]),
});

const ANIMATION_MODES = Object.freeze({
    none: 0,
    fade_in: 1,
    fade_in_out: 2,
    slide_up: 3,
    typewriter: 4,
});

function get_preview_controller(node) {
    return node?.[TEXT_OVERLAY_STATE_KEY]?.preview_state?.preview_controller ?? null;
}

function get_node_widget_value(node, widget_name, fallback_value = null) {
    const widgets = Array.isArray(node?.widgets) ? node.widgets : [];
    const widget = widgets.find((item) => item?.name === widget_name);
    return widget?.value ?? fallback_value;
}

export function map_position_to_anchor(position) {
    const position_key = typeof position === "string" ? position : "";
    return POSITION_ANCHORS[position_key] ?? POSITION_ANCHORS["bottom-center"];
}

export function apply_text_overlay_position(node, position) {
    const preview_controller = get_preview_controller(node);
    if (!preview_controller || typeof preview_controller.set_uniform !== "function") {
        return false;
    }
    const [anchor_x, anchor_y] = map_position_to_anchor(position);
    preview_controller.set_uniform("u_anchor_x", anchor_x);
    preview_controller.set_uniform("u_anchor_y", anchor_y);
    return true;
}

export function map_animation_to_mode(animation) {
    const animation_key = typeof animation === "string" ? animation : "";
    return ANIMATION_MODES[animation_key] ?? ANIMATION_MODES.fade_in;
}

export function apply_text_overlay_animation(node, animation) {
    const preview_controller = get_preview_controller(node);
    if (!preview_controller || typeof preview_controller.set_uniform !== "function") {
        return false;
    }
    preview_controller.set_uniform("u_animation_mode", map_animation_to_mode(animation));
    return true;
}

export async function mount_text_overlay_effect_widget_for_node({
    node,
    document_ref = globalThis.document,
    shader_loader = loadShader,
    request_animation_frame = globalThis.requestAnimationFrame,
    cancel_animation_frame = globalThis.cancelAnimationFrame,
    now = () =>
        globalThis.performance && typeof globalThis.performance.now === "function"
            ? globalThis.performance.now()
            : Date.now(),
}) {
    const widget_state = await mount_effect_node_widget(
        node,
        EFFECT_NAME,
        TEXT_OVERLAY_PARAM_SPECS,
        {
            document_ref,
            shader_loader,
            request_animation_frame,
            cancel_animation_frame,
            now,
        },
    );
    if (!widget_state) {
        return widget_state;
    }

    const position_value = get_node_widget_value(node, "position", "bottom-center");
    apply_text_overlay_position(node, position_value);
    const animation_value = get_node_widget_value(node, "animation", "fade_in");
    apply_text_overlay_animation(node, animation_value);
    const preview_controller = get_preview_controller(node);
    if (preview_controller && typeof preview_controller.set_uniform === "function") {
        preview_controller.set_uniform("u_duration", 3.0);
        preview_controller.set_uniform("u_has_text_texture", 0.0);
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
            if (nodeData?.name !== "CoolTextOverlayEffect") {
                return;
            }

            const previous_on_node_created = nodeType.prototype.onNodeCreated;
            const previous_on_removed = nodeType.prototype.onRemoved;
            const previous_on_widget_changed = nodeType.prototype.onWidgetChanged;

            nodeType.prototype.onNodeCreated = async function onNodeCreated() {
                if (typeof previous_on_node_created === "function") {
                    previous_on_node_created.apply(this, arguments);
                }
                await mount_text_overlay_effect_widget_for_node({
                    node: this,
                    document_ref,
                    shader_loader,
                    request_animation_frame,
                    cancel_animation_frame,
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
                if (widget_name === "position") {
                    apply_text_overlay_position(this, widget_value);
                    return;
                }
                if (widget_name === "animation") {
                    apply_text_overlay_animation(this, widget_value);
                    return;
                }

                apply_effect_widget_uniform_from_widget(
                    this,
                    EFFECT_NAME,
                    TEXT_OVERLAY_PARAM_SPECS,
                    widget_name,
                    widget_value,
                );
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
