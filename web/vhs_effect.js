import { loadShader } from "./shaders/loader.js";
import {
    create_live_glsl_preview,
    create_placeholder_texture,
} from "./effect_selector.js";

export const EXTENSION_NAME = "Comfy.CoolEffects.VHSEffect";
const VHS_WIDGET_UNIFORM_MAP = Object.freeze({
    scanline_intensity: "u_scanline_intensity",
    jitter_amount: "u_jitter_amount",
    chroma_shift: "u_chroma_shift",
});

function apply_uniform_from_widget(node, widget_name, widget_value) {
    const uniform_name = VHS_WIDGET_UNIFORM_MAP[widget_name];
    if (!uniform_name) {
        return;
    }
    const preview_controller =
        node?.__cool_vhs_widget_state?.preview_state?.preview_controller;
    if (!preview_controller || typeof preview_controller.set_uniform !== "function") {
        return;
    }
    const numeric_value = Number(widget_value);
    if (!Number.isFinite(numeric_value)) {
        return;
    }
    preview_controller.set_uniform(uniform_name, numeric_value);
}

export async function mount_vhs_effect_widget_for_node({
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
    if (!node || typeof node.addDOMWidget !== "function") {
        return null;
    }
    if (!document_ref || typeof document_ref.createElement !== "function") {
        throw new Error("Missing document reference for vhs effect widget");
    }

    if (node.__cool_vhs_widget_state?.preview_controller) {
        node.__cool_vhs_widget_state.preview_controller.stop();
    }

    const container_element = document_ref.createElement("div");
    container_element.setAttribute("data-widget", "cool-vhs-effect");
    Object.assign(container_element.style, {
        display: "flex",
        flexDirection: "column",
        padding: "6px 8px 8px",
        boxSizing: "border-box",
        width: "100%",
    });

    const widget = node.addDOMWidget("vhs_preview", "div", container_element, {
        serialize: false,
        hideOnZoom: false,
    });

    const preview_state = {};
    node.__cool_vhs_widget_state = {
        preview_state,
        widget,
        container_element,
    };

    const placeholder_texture = create_placeholder_texture(document_ref, 512);
    await create_live_glsl_preview({
        document_ref,
        container_element,
        effect_name: "vhs",
        input_image: placeholder_texture,
        preview_state,
        keep_webgl_error_on_shader_load: true,
        shader_loader,
        request_animation_frame,
        cancel_animation_frame,
        now,
    });

    return node.__cool_vhs_widget_state;
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
            if (nodeData?.name !== "CoolVHSEffect") {
                return;
            }
            const previous_on_node_created = nodeType.prototype.onNodeCreated;
            const previous_on_removed = nodeType.prototype.onRemoved;
            const previous_on_widget_changed = nodeType.prototype.onWidgetChanged;

            nodeType.prototype.onNodeCreated = async function onNodeCreated() {
                if (typeof previous_on_node_created === "function") {
                    previous_on_node_created.apply(this, arguments);
                }
                await mount_vhs_effect_widget_for_node({
                    node: this,
                    document_ref,
                    shader_loader,
                    request_animation_frame,
                    cancel_animation_frame,
                    now,
                });
            };

            nodeType.prototype.onRemoved = function onRemoved() {
                const preview_controller =
                    this.__cool_vhs_widget_state?.preview_state?.preview_controller;
                if (
                    preview_controller &&
                    typeof preview_controller.stop === "function"
                ) {
                    preview_controller.stop();
                }
                if (typeof previous_on_removed === "function") {
                    previous_on_removed.apply(this, arguments);
                }
            };

            nodeType.prototype.onWidgetChanged = function onWidgetChanged() {
                if (typeof previous_on_widget_changed === "function") {
                    previous_on_widget_changed.apply(this, arguments);
                }
                const [widget_name, widget_value] = arguments;
                apply_uniform_from_widget(this, widget_name, widget_value);
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
