import {
    apply_effect_widget_uniform_from_widget,
    mount_effect_node_widget,
    stop_effect_node_widget_preview,
} from "./effect_node_widget.js";
import { loadShader } from "./shaders/loader.js";

export const EXTENSION_NAME = "Comfy.CoolEffects.WaveformEffect";
const WAVEFORM_PARAM_SPECS = Object.freeze([
    Object.freeze({
        widget_name: "line_thickness",
        uniform_name: "u_line_thickness",
        default_value: 0.005,
    }),
    Object.freeze({
        widget_name: "waveform_height",
        uniform_name: "u_waveform_height",
        default_value: 0.2,
    }),
    Object.freeze({
        widget_name: "waveform_y",
        uniform_name: "u_waveform_y",
        default_value: 0.8,
    }),
    Object.freeze({
        widget_name: "opacity",
        uniform_name: "u_opacity",
        default_value: 0.85,
    }),
]);
const WAVEFORM_SAMPLE_COUNT = 256;

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
    return node?.__cool_waveform_widget_state?.preview_state?.preview_controller ?? null;
}

function parse_line_color(value) {
    if (typeof value !== "string") {
        return [1.0, 0.8, 0.2];
    }
    const parts = value.split(",").map((item) => Number(item.trim()));
    if (parts.length !== 3 || parts.some((part) => !Number.isFinite(part))) {
        return [1.0, 0.8, 0.2];
    }
    return parts;
}

function apply_line_color_uniform(node, line_color_text) {
    const preview_controller = get_preview_controller(node);
    if (!preview_controller) {
        return;
    }
    if (typeof preview_controller.set_uniform_array === "function") {
        preview_controller.set_uniform_array("u_line_color", parse_line_color(line_color_text));
    }
}

function stop_synthetic_preview_waveform(node, cancel_animation_frame) {
    const signal_state = node?.__cool_waveform_signal_state;
    if (!signal_state || !signal_state.running) {
        return;
    }
    signal_state.running = false;
    if (signal_state.animation_handle != null) {
        cancel_animation_frame(signal_state.animation_handle);
    }
}

function start_synthetic_preview_waveform({
    node,
    request_animation_frame,
    cancel_animation_frame,
    now,
}) {
    stop_synthetic_preview_waveform(node, cancel_animation_frame);
    const signal_state = {
        running: true,
        animation_handle: null,
    };
    node.__cool_waveform_signal_state = signal_state;

    const animate = () => {
        if (!signal_state.running) {
            return;
        }

        const preview_controller = get_preview_controller(node);
        if (preview_controller && typeof preview_controller.set_uniform_array === "function") {
            const u_time = now() / 1000.0;
            const waveform_values = new Array(WAVEFORM_SAMPLE_COUNT);
            for (let index = 0; index < WAVEFORM_SAMPLE_COUNT; index += 1) {
                waveform_values[index] = Math.sin(u_time * 4.0 + index / 40.0);
            }
            preview_controller.set_uniform_array("u_waveform[0]", waveform_values);
        }

        signal_state.animation_handle = request_animation_frame(animate);
    };

    signal_state.animation_handle = request_animation_frame(animate);
}

export async function mount_waveform_effect_widget_for_node({
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
    const widget_state = await mount_effect_node_widget(node, "waveform", WAVEFORM_PARAM_SPECS, {
        document_ref,
        shader_loader,
        request_animation_frame,
        cancel_animation_frame,
        now,
    });

    const line_color_widget = Array.isArray(node.widgets)
        ? node.widgets.find((widget) => widget?.name === "line_color")
        : null;
    apply_line_color_uniform(node, line_color_widget?.value ?? "1.0,0.8,0.2");

    start_synthetic_preview_waveform({
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
            if (nodeData?.name !== "CoolWaveformEffect") {
                return;
            }
            const previous_on_node_created = nodeType.prototype.onNodeCreated;
            const previous_on_removed = nodeType.prototype.onRemoved;
            const previous_on_widget_changed = nodeType.prototype.onWidgetChanged;

            nodeType.prototype.onNodeCreated = async function onNodeCreated() {
                if (typeof previous_on_node_created === "function") {
                    previous_on_node_created.apply(this, arguments);
                }
                await mount_waveform_effect_widget_for_node({
                    node: this,
                    document_ref,
                    shader_loader,
                    request_animation_frame,
                    cancel_animation_frame,
                    now,
                });
            };

            nodeType.prototype.onRemoved = function onRemoved() {
                stop_synthetic_preview_waveform(this, cancel_animation_frame);
                stop_effect_node_widget_preview(this, "waveform");
                if (typeof previous_on_removed === "function") {
                    previous_on_removed.apply(this, arguments);
                }
            };

            nodeType.prototype.onWidgetChanged = function onWidgetChanged() {
                if (typeof previous_on_widget_changed === "function") {
                    previous_on_widget_changed.apply(this, arguments);
                }
                const [widget_name, widget_value] = arguments;
                if (widget_name === "line_color") {
                    apply_line_color_uniform(this, widget_value);
                    return;
                }
                apply_effect_widget_uniform_from_widget(
                    this,
                    "waveform",
                    WAVEFORM_PARAM_SPECS,
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
