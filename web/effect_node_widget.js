import {
    create_live_glsl_preview,
    create_placeholder_texture,
} from "./effect_selector.js";
import { loadShader } from "./shaders/loader.js";

const EFFECT_DEFAULT_UNIFORMS = Object.freeze({
    glitch: Object.freeze({
        u_wave_freq: 120.0,
        u_wave_amp: 0.0025,
        u_speed: 10.0,
    }),
    vhs: Object.freeze({
        u_scanline_intensity: 0.04,
        u_jitter_amount: 0.0018,
        u_chroma_shift: 0.002,
    }),
    zoom_pulse: Object.freeze({
        u_pulse_amp: 0.06,
        u_pulse_speed: 3.0,
    }),
    bass_zoom: Object.freeze({
        u_zoom_strength: 0.3,
        u_smoothing: 0.5,
        u_bass: 0.0,
    }),
    beat_pulse: Object.freeze({
        u_pulse_intensity: 0.5,
        u_zoom_amount: 0.05,
        u_decay: 0.3,
        u_beat: 0.0,
        u_rms: 0.0,
    }),
    freq_warp: Object.freeze({
        u_warp_intensity: 0.4,
        u_warp_frequency: 8.0,
        u_mid_weight: 0.6,
        u_treble_weight: 0.4,
        u_mid: 0.0,
        u_treble: 0.0,
    }),
    pan_left: Object.freeze({
        u_speed: 0.2,
        u_origin_x: 0.0,
        u_origin_y: 0.0,
        u_zoom: 0.0,
    }),
    pan_right: Object.freeze({
        u_speed: 0.2,
        u_origin_x: 0.0,
        u_origin_y: 0.0,
        u_zoom: 0.0,
    }),
    pan_up: Object.freeze({
        u_speed: 0.2,
        u_origin_x: 0.0,
        u_origin_y: 0.0,
        u_zoom: 0.0,
    }),
    pan_down: Object.freeze({
        u_speed: 0.2,
        u_origin_x: 0.0,
        u_origin_y: 0.0,
        u_zoom: 0.0,
    }),
    pan_diagonal: Object.freeze({
        u_speed: 0.2,
        u_origin_x: 0.0,
        u_origin_y: 0.0,
        u_dir_x: 0.7071,
        u_dir_y: 0.7071,
        u_zoom: 0.0,
    }),
    water_drops: Object.freeze({
        u_drop_density: 60.0,
        u_drop_size: 0.08,
        u_fall_speed: 1.0,
        u_refraction_strength: 0.3,
        u_gravity: 1.0,
        u_wind: 0.0,
    }),
    frosted_glass: Object.freeze({
        u_frost_intensity: 0.5,
        u_blur_radius: 0.015,
        u_uniformity: 0.6,
        u_tint_temperature: 0.0,
        u_condensation_rate: 0.0,
    }),
});

function default_now() {
    if (globalThis.performance && typeof globalThis.performance.now === "function") {
        return globalThis.performance.now();
    }
    return Date.now();
}

function to_effect_key(effect_name) {
    if (typeof effect_name !== "string" || effect_name.length === 0) {
        throw new Error("effect_name must be a non-empty string");
    }
    return effect_name.replace(/[^a-zA-Z0-9_]/g, "_");
}

function to_state_key(effect_name) {
    return `__cool_${to_effect_key(effect_name)}_widget_state`;
}

function normalize_param_specs(effect_name, param_specs) {
    if (!Array.isArray(param_specs) || param_specs.length === 0) {
        throw new Error("param_specs must be a non-empty array");
    }

    const default_uniforms = EFFECT_DEFAULT_UNIFORMS[effect_name] ?? {};

    return param_specs.map((param_spec) => {
        const widget_name =
            typeof param_spec?.widget_name === "string" ? param_spec.widget_name : "";
        const uniform_name =
            typeof param_spec?.uniform_name === "string" ? param_spec.uniform_name : "";

        if (widget_name.length === 0 || uniform_name.length === 0) {
            throw new Error("Each param spec must define widget_name and uniform_name");
        }

        const explicit_default = Number(param_spec.default_value);
        const fallback_default = Number(default_uniforms[uniform_name]);
        const default_value = Number.isFinite(explicit_default)
            ? explicit_default
            : Number.isFinite(fallback_default)
              ? fallback_default
              : 0;

        return {
            widget_name,
            uniform_name,
            default_value,
        };
    });
}

function get_controller_from_state(widget_state) {
    return widget_state?.preview_state?.preview_controller ?? null;
}

export function stop_effect_node_widget_preview(node, effect_name) {
    const widget_state = node?.[to_state_key(effect_name)];
    const preview_controller = get_controller_from_state(widget_state);
    if (preview_controller && typeof preview_controller.stop === "function") {
        preview_controller.stop();
    }
}

export async function mount_effect_node_widget(
    node,
    effect_name,
    param_specs,
    {
        document_ref = globalThis.document,
        shader_loader = loadShader,
        request_animation_frame = globalThis.requestAnimationFrame,
        cancel_animation_frame = globalThis.cancelAnimationFrame,
        now = default_now,
    } = {},
) {
    if (!node || typeof node.addDOMWidget !== "function") {
        return null;
    }
    if (!document_ref || typeof document_ref.createElement !== "function") {
        throw new Error("Missing document reference for effect widget");
    }

    const effect_key = to_effect_key(effect_name);
    const state_key = to_state_key(effect_name);
    stop_effect_node_widget_preview(node, effect_name);

    const resolved_param_specs = normalize_param_specs(effect_name, param_specs);
    const container_element = document_ref.createElement("div");
    container_element.setAttribute(
        "data-widget",
        `cool-${effect_key.replace(/_/g, "-")}-effect`,
    );
    Object.assign(container_element.style, {
        display: "flex",
        flexDirection: "column",
        padding: "6px 8px 8px",
        boxSizing: "border-box",
        width: "100%",
    });

    const widget = node.addDOMWidget(`${effect_key}_preview`, "div", container_element, {
        serialize: false,
        hideOnZoom: false,
    });

    const preview_state = {};
    node[state_key] = {
        preview_state,
        widget,
        container_element,
        effect_name,
        param_specs: resolved_param_specs,
    };

    const placeholder_texture = create_placeholder_texture(document_ref, 512);
    await create_live_glsl_preview({
        document_ref,
        container_element,
        effect_name,
        input_image: placeholder_texture,
        preview_state,
        keep_webgl_error_on_shader_load: true,
        shader_loader,
        request_animation_frame,
        cancel_animation_frame,
        now,
    });

    const preview_controller = get_controller_from_state(node[state_key]);
    if (preview_controller && typeof preview_controller.set_uniform === "function") {
        resolved_param_specs.forEach((param_spec) => {
            preview_controller.set_uniform(
                param_spec.uniform_name,
                param_spec.default_value,
            );
        });
    }

    return node[state_key];
}

export function apply_effect_widget_uniform_from_widget(
    node,
    effect_name,
    param_specs,
    widget_name,
    widget_value,
) {
    const state_key = to_state_key(effect_name);
    const widget_state = node?.[state_key];
    const preview_controller = get_controller_from_state(widget_state);
    if (!preview_controller || typeof preview_controller.set_uniform !== "function") {
        return false;
    }

    const resolved_param_specs = Array.isArray(widget_state?.param_specs)
        ? widget_state.param_specs
        : normalize_param_specs(effect_name, param_specs);
    const param_spec = resolved_param_specs.find(
        (item) => item.widget_name === widget_name,
    );
    if (!param_spec) {
        return false;
    }

    const numeric_value = Number(widget_value);
    if (!Number.isFinite(numeric_value)) {
        return false;
    }

    preview_controller.set_uniform(param_spec.uniform_name, numeric_value);
    return true;
}
