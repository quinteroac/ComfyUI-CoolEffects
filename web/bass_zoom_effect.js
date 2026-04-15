import {
    apply_effect_widget_uniform_from_widget,
    mount_effect_node_widget,
    stop_effect_node_widget_preview,
} from "./effect_node_widget.js";
import { loadShader } from "./shaders/loader.js";

export const EXTENSION_NAME = "Comfy.CoolEffects.BassZoomEffect";
const BASS_ZOOM_PARAM_SPECS = Object.freeze([
    Object.freeze({
        widget_name: "zoom_strength",
        uniform_name: "u_zoom_strength",
        default_value: 0.3,
    }),
    Object.freeze({
        widget_name: "smoothing",
        uniform_name: "u_smoothing",
        default_value: 0.5,
    }),
]);
const SYNTHETIC_BPM = 60;

function default_request_animation_frame(callback) {
    if (typeof globalThis.requestAnimationFrame === "function") {
        return globalThis.requestAnimationFrame(callback);
    }
    return globalThis.setTimeout(() => callback(Date.now()), 16);
}

function default_cancel_animation_frame(handle) {
    if (typeof globalThis.cancelAnimationFrame === "function") {
        globalThis.cancelAnimationFrame(handle);
        return;
    }
    globalThis.clearTimeout(handle);
}

function get_preview_controller(node) {
    return node?.__cool_bass_zoom_widget_state?.preview_state?.preview_controller ?? null;
}

function stop_synthetic_preview_bass(node, cancel_animation_frame) {
    const signal_state = node?.__cool_bass_zoom_signal_state;
    if (!signal_state || !signal_state.running) {
        return;
    }
    signal_state.running = false;
    if (signal_state.animation_handle != null) {
        cancel_animation_frame(signal_state.animation_handle);
    }
}

function get_synthetic_bass_pulse(now_ms) {
    const beat_period_ms = 60000 / SYNTHETIC_BPM;
    const normalized_phase =
        (((now_ms % beat_period_ms) + beat_period_ms) % beat_period_ms) /
        beat_period_ms;
    const pulse = Math.exp(-10.0 * normalized_phase);
    const bass = Math.min(1.0, 0.08 + pulse * 0.92);
    return bass;
}

function start_synthetic_preview_bass({
    node,
    request_animation_frame,
    cancel_animation_frame,
    now,
}) {
    stop_synthetic_preview_bass(node, cancel_animation_frame);
    const signal_state = {
        running: true,
        animation_handle: null,
    };
    node.__cool_bass_zoom_signal_state = signal_state;

    const animate = () => {
        if (!signal_state.running) {
            return;
        }

        const preview_controller = get_preview_controller(node);
        if (preview_controller && typeof preview_controller.set_uniform === "function") {
            preview_controller.set_uniform("u_bass", get_synthetic_bass_pulse(now()));
        }

        signal_state.animation_handle = request_animation_frame(animate);
    };

    signal_state.animation_handle = request_animation_frame(animate);
}

export async function mount_bass_zoom_effect_widget_for_node({
    node,
    document_ref = globalThis.document,
    shader_loader = loadShader,
    request_animation_frame = default_request_animation_frame,
    cancel_animation_frame = default_cancel_animation_frame,
    now = () =>
        globalThis.performance && typeof globalThis.performance.now === "function"
            ? globalThis.performance.now()
            : Date.now(),
}) {
    const widget_state = await mount_effect_node_widget(node, "bass_zoom", BASS_ZOOM_PARAM_SPECS, {
        document_ref,
        shader_loader,
        request_animation_frame,
        cancel_animation_frame,
        now,
    });

    start_synthetic_preview_bass({
        node,
        request_animation_frame,
        cancel_animation_frame,
        now,
    });

    return widget_state;
}

export function register_comfy_extension(
    app_ref,
    {
        document_ref = globalThis.document,
        shader_loader = loadShader,
        request_animation_frame = default_request_animation_frame,
        cancel_animation_frame = default_cancel_animation_frame,
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
            if (nodeData?.name !== "CoolBassZoomEffect") {
                return;
            }
            const previous_on_node_created = nodeType.prototype.onNodeCreated;
            const previous_on_removed = nodeType.prototype.onRemoved;
            const previous_on_widget_changed = nodeType.prototype.onWidgetChanged;

            nodeType.prototype.onNodeCreated = async function onNodeCreated() {
                if (typeof previous_on_node_created === "function") {
                    previous_on_node_created.apply(this, arguments);
                }
                await mount_bass_zoom_effect_widget_for_node({
                    node: this,
                    document_ref,
                    shader_loader,
                    request_animation_frame,
                    cancel_animation_frame,
                    now,
                });
            };

            nodeType.prototype.onRemoved = function onRemoved() {
                stop_synthetic_preview_bass(this, cancel_animation_frame);
                stop_effect_node_widget_preview(this, "bass_zoom");
                if (typeof previous_on_removed === "function") {
                    previous_on_removed.apply(this, arguments);
                }
            };

            nodeType.prototype.onWidgetChanged = function onWidgetChanged() {
                if (typeof previous_on_widget_changed === "function") {
                    previous_on_widget_changed.apply(this, arguments);
                }
                const [widget_name, widget_value] = arguments;
                apply_effect_widget_uniform_from_widget(
                    this,
                    "bass_zoom",
                    BASS_ZOOM_PARAM_SPECS,
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
