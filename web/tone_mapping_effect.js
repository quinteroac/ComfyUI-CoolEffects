import {
    apply_effect_widget_uniform_from_widget,
    mount_effect_node_widget,
    stop_effect_node_widget_preview,
} from "./effect_node_widget.js";
import { loadShader } from "./shaders/loader.js";

export const EXTENSION_NAME = "Comfy.CoolEffects.ToneMappingEffect";
export const MODE_UNIFORM_VALUES = Object.freeze({
    none: 0.0,
    bw: 1.0,
    sepia: 2.0,
    duotone: 3.0,
});
export const TONE_MAPPING_PARAM_SPECS = Object.freeze([
    Object.freeze({
        widget_name: "mode",
        uniform_name: "u_mode",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "intensity",
        uniform_name: "u_intensity",
        default_value: 1.0,
    }),
    Object.freeze({
        widget_name: "shadow_r",
        uniform_name: "u_shadow_r",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "shadow_g",
        uniform_name: "u_shadow_g",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "shadow_b",
        uniform_name: "u_shadow_b",
        default_value: 0.0,
    }),
    Object.freeze({
        widget_name: "highlight_r",
        uniform_name: "u_highlight_r",
        default_value: 1.0,
    }),
    Object.freeze({
        widget_name: "highlight_g",
        uniform_name: "u_highlight_g",
        default_value: 1.0,
    }),
    Object.freeze({
        widget_name: "highlight_b",
        uniform_name: "u_highlight_b",
        default_value: 1.0,
    }),
]);

export function map_mode_to_uniform_value(mode) {
    const mode_key = typeof mode === "string" ? mode.trim().toLowerCase() : "";
    return MODE_UNIFORM_VALUES[mode_key] ?? MODE_UNIFORM_VALUES.none;
}

export function apply_tone_mapping_mode_from_widget(node, mode) {
    const preview_controller =
        node?.__cool_tone_mapping_widget_state?.preview_state?.preview_controller ?? null;
    if (!preview_controller || typeof preview_controller.set_uniform !== "function") {
        return false;
    }
    preview_controller.set_uniform("u_mode", map_mode_to_uniform_value(mode));
    return true;
}

export function apply_tone_mapping_uniform_from_widget(node, widget_name, widget_value) {
    if (widget_name === "mode") {
        return apply_tone_mapping_mode_from_widget(node, widget_value);
    }
    return apply_effect_widget_uniform_from_widget(
        node,
        "tone_mapping",
        TONE_MAPPING_PARAM_SPECS,
        widget_name,
        widget_value,
    );
}

export async function mount_tone_mapping_effect_widget_for_node({
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
    return mount_effect_node_widget(node, "tone_mapping", TONE_MAPPING_PARAM_SPECS, {
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
            if (nodeData?.name !== "CoolToneMappingEffect") {
                return;
            }
            const previous_on_node_created = nodeType.prototype.onNodeCreated;
            const previous_on_removed = nodeType.prototype.onRemoved;
            const previous_on_widget_changed = nodeType.prototype.onWidgetChanged;

            nodeType.prototype.onNodeCreated = async function onNodeCreated() {
                if (typeof previous_on_node_created === "function") {
                    previous_on_node_created.apply(this, arguments);
                }
                await mount_tone_mapping_effect_widget_for_node({
                    node: this,
                    document_ref,
                    shader_loader,
                    request_animation_frame,
                    cancel_animation_frame,
                    now,
                });
            };

            nodeType.prototype.onRemoved = function onRemoved() {
                stop_effect_node_widget_preview(this, "tone_mapping");
                if (typeof previous_on_removed === "function") {
                    previous_on_removed.apply(this, arguments);
                }
            };

            nodeType.prototype.onWidgetChanged = function onWidgetChanged() {
                if (typeof previous_on_widget_changed === "function") {
                    previous_on_widget_changed.apply(this, arguments);
                }
                const [widget_name, widget_value] = arguments;
                apply_tone_mapping_uniform_from_widget(this, widget_name, widget_value);
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
