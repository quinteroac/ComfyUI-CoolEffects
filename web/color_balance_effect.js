import {
    apply_effect_widget_uniform_from_widget,
    mount_effect_node_widget,
    stop_effect_node_widget_preview,
} from "./effect_node_widget.js";
import { loadShader } from "./shaders/loader.js";

export const EXTENSION_NAME = "Comfy.CoolEffects.ColorBalanceEffect";
export const COLOR_BALANCE_PARAM_SPECS = Object.freeze([
    Object.freeze({
        widget_name: "shadows_r",
        uniform_name: "u_shadows_r",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "shadows_g",
        uniform_name: "u_shadows_g",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "shadows_b",
        uniform_name: "u_shadows_b",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "midtones_r",
        uniform_name: "u_midtones_r",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "midtones_g",
        uniform_name: "u_midtones_g",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "midtones_b",
        uniform_name: "u_midtones_b",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "highlights_r",
        uniform_name: "u_highlights_r",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "highlights_g",
        uniform_name: "u_highlights_g",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "highlights_b",
        uniform_name: "u_highlights_b",
        default_value: 0.0,
    }),
]);

export function apply_color_balance_uniform_from_widget(node, widget_name, widget_value) {
    return apply_effect_widget_uniform_from_widget(
        node,
        "color_balance",
        COLOR_BALANCE_PARAM_SPECS,
        widget_name,
        widget_value,
    );
}

export async function mount_color_balance_effect_widget_for_node({
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
    return mount_effect_node_widget(node, "color_balance", COLOR_BALANCE_PARAM_SPECS, {
        document_ref,
        shader_loader,
        request_animation_frame,
        cancel_animation_frame,
        now,
    });
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
            if (nodeData?.name !== "CoolColorBalanceEffect") {
                return;
            }
            const previous_on_node_created = nodeType.prototype.onNodeCreated;
            const previous_on_removed = nodeType.prototype.onRemoved;
            const previous_on_widget_changed = nodeType.prototype.onWidgetChanged;

            nodeType.prototype.onNodeCreated = async function onNodeCreated() {
                if (typeof previous_on_node_created === "function") {
                    previous_on_node_created.apply(this, arguments);
                }
                await mount_color_balance_effect_widget_for_node({
                    node: this,
                    document_ref,
                    shader_loader,
                    request_animation_frame,
                    cancel_animation_frame,
                    now,
                });
            };

            nodeType.prototype.onRemoved = function onRemoved() {
                stop_effect_node_widget_preview(this, "color_balance");
                if (typeof previous_on_removed === "function") {
                    previous_on_removed.apply(this, arguments);
                }
            };

            nodeType.prototype.onWidgetChanged = function onWidgetChanged() {
                if (typeof previous_on_widget_changed === "function") {
                    previous_on_widget_changed.apply(this, arguments);
                }
                const [widget_name, widget_value] = arguments;
                apply_color_balance_uniform_from_widget(this, widget_name, widget_value);
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
