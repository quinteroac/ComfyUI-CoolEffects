import { listShaders, loadShader } from "./shaders/loader.js";

const GLOBAL_RESIZE_CALLBACKS = new Set();
let GLOBAL_RESIZE_LISTENER = null;
export const EXTENSION_NAME = "Comfy.CoolEffects.EffectSelector";
const VERTEX_SHADER_SOURCE = `
varying vec2 v_uv;
void main() {
    v_uv = uv;
    gl_Position = vec4(position, 1.0);
}
`;
const FALLBACK_FRAGMENT_SHADER = `
precision mediump float;
varying vec2 v_uv;
uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
void main() {
    vec4 sampled = texture2D(u_image, v_uv);
    gl_FragColor = vec4(sampled.rgb, 1.0);
}
`;

function subscribe_global_resize(callback) {
    if (typeof callback !== "function") {
        throw new Error("Expected resize callback function");
    }

    GLOBAL_RESIZE_CALLBACKS.add(callback);
    if (
        GLOBAL_RESIZE_LISTENER === null &&
        typeof globalThis.addEventListener === "function"
    ) {
        GLOBAL_RESIZE_LISTENER = () => {
            GLOBAL_RESIZE_CALLBACKS.forEach((registered_callback) => {
                registered_callback();
            });
        };
        globalThis.addEventListener("resize", GLOBAL_RESIZE_LISTENER);
    }

    return () => {
        GLOBAL_RESIZE_CALLBACKS.delete(callback);
        if (
            GLOBAL_RESIZE_CALLBACKS.size === 0 &&
            GLOBAL_RESIZE_LISTENER !== null &&
            typeof globalThis.removeEventListener === "function"
        ) {
            globalThis.removeEventListener("resize", GLOBAL_RESIZE_LISTENER);
            GLOBAL_RESIZE_LISTENER = null;
        }
    };
}

function default_now() {
    if (globalThis.performance && typeof globalThis.performance.now === "function") {
        return globalThis.performance.now();
    }
    return Date.now();
}

export function create_effect_dropdown_widget(
    document_ref,
    shader_names,
    selected_effect_name,
    on_change,
) {
    if (!Array.isArray(shader_names) || shader_names.length == 0) {
        throw new Error("No shaders available for effect selector");
    }

    const select_element = document_ref.createElement("select");
    select_element.setAttribute("aria-label", "Effect");
    shader_names.forEach((shader_name) => {
        const option_element = document_ref.createElement("option");
        option_element.value = shader_name;
        option_element.textContent = shader_name;
        option_element.selected = shader_name === selected_effect_name;
        select_element.appendChild(option_element);
    });
    select_element.value = selected_effect_name;
    select_element.addEventListener("change", () => {
        if (on_change) {
            on_change(select_element.value);
        }
    });
    return select_element;
}

export function update_preview_effect(preview_state, effect_name) {
    preview_state.effect_name = effect_name;
}

function default_request_animation_frame(callback) {
    if (typeof globalThis.requestAnimationFrame === "function") {
        return globalThis.requestAnimationFrame(callback);
    }
    return globalThis.setTimeout(() => callback(default_now()), 16);
}

function default_cancel_animation_frame(handle) {
    if (typeof globalThis.cancelAnimationFrame === "function") {
        globalThis.cancelAnimationFrame(handle);
        return;
    }
    globalThis.clearTimeout(handle);
}

function get_element_size(canvas_element) {
    const width =
        Number(canvas_element.clientWidth) ||
        Number(canvas_element.width) ||
        1;
    const height =
        Number(canvas_element.clientHeight) ||
        Number(canvas_element.height) ||
        1;
    return [width, height];
}

export function create_canvas_preview_surface(document_ref) {
    const root_element = document_ref.createElement("div");
    root_element.setAttribute("data-preview-root", "cool-effects");

    const canvas_element = document_ref.createElement("canvas");
    canvas_element.width = 512;
    canvas_element.height = 512;
    canvas_element.setAttribute("data-renderer", "r3f");
    canvas_element.setAttribute("aria-label", "Live GLSL preview");
    canvas_element.style = canvas_element.style || {};
    canvas_element.style.background = "rgb(128, 128, 128)";
    root_element.appendChild(canvas_element);

    const overlay_element = document_ref.createElement("div");
    overlay_element.setAttribute("data-preview-overlay", "cool-effects");
    overlay_element.setAttribute("aria-live", "polite");
    overlay_element.setAttribute("role", "status");
    overlay_element.style = overlay_element.style || {};
    overlay_element.textContent = "";
    root_element.appendChild(overlay_element);

    return { root_element, canvas_element, overlay_element };
}

export function create_preview_descriptor({
    fragment_shader_source,
    effect_name,
    input_image,
    canvas_element,
    shader_material = null,
    r3f_root = null,
    renderer_mode = "descriptor",
}) {
    const [width, height] = get_element_size(canvas_element);
    return {
        renderer: renderer_mode,
        three_canvas: true,
        mesh: "plane",
        effect_name,
        fragment_shader_source,
        shader_material,
        r3f_root,
        uniforms: {
            u_image: input_image ?? null,
            u_time: 0,
            u_resolution: [width, height],
        },
    };
}

export async function create_live_glsl_preview({
    document_ref,
    container_element,
    effect_name,
    input_image = null,
    preview_state = {},
    now = default_now,
    shader_loader = loadShader,
    three_stack_loader = async () => {
        const [THREE, react_three_fiber, react_three_drei] = await Promise.all([
            import("three"),
            import("@react-three/fiber"),
            import("@react-three/drei"),
        ]);
        return { THREE, react_three_fiber, react_three_drei };
    },
    request_animation_frame = default_request_animation_frame,
    cancel_animation_frame = default_cancel_animation_frame,
}) {
    const { root_element, canvas_element, overlay_element } =
        create_canvas_preview_surface(document_ref);
    container_element.appendChild(root_element);

    const start_time = now();
    const safe_effect_name =
        typeof effect_name === "string" && effect_name.length > 0
            ? effect_name
            : "glitch";
    const preview_descriptor = create_preview_descriptor({
        fragment_shader_source: "",
        effect_name: safe_effect_name,
        input_image,
        canvas_element,
    });
    preview_state.preview_error = "";

    const update_overlay_message = () => {
        if (preview_state.preview_error) {
            overlay_element.textContent = preview_state.preview_error;
            return;
        }
        overlay_element.textContent = preview_descriptor.uniforms.u_image
            ? ""
            : "Connect an image to preview this effect.";
    };

    let three_stack = null;
    try {
        three_stack = await three_stack_loader();
    } catch (_error) {
        three_stack = null;
    }
    const has_r3f = Boolean(three_stack?.react_three_fiber?.createRoot);
    const has_drei = Boolean(three_stack?.react_three_drei);
    preview_descriptor.renderer = has_r3f && has_drei ? "r3f" : "descriptor";

    let shader_material = null;
    if (three_stack?.THREE?.ShaderMaterial) {
        shader_material = new three_stack.THREE.ShaderMaterial({
            vertexShader: VERTEX_SHADER_SOURCE,
            fragmentShader: FALLBACK_FRAGMENT_SHADER,
            uniforms: {
                u_image: { value: input_image ?? null },
                u_time: { value: 0 },
                u_resolution: {
                    value: new three_stack.THREE.Vector2(
                        preview_descriptor.uniforms.u_resolution[0],
                        preview_descriptor.uniforms.u_resolution[1],
                    ),
                },
            },
        });
    }
    preview_descriptor.shader_material = shader_material;
    preview_state.render_backend = preview_descriptor.renderer;

    let active_shader_request_id = 0;
    const load_shader_for_effect = async (next_effect_name) => {
        const request_id = active_shader_request_id + 1;
        active_shader_request_id = request_id;
        const start_ms = now();
        try {
            const fragment_shader_source = await shader_loader(next_effect_name);
            if (request_id !== active_shader_request_id) {
                return;
            }
            preview_descriptor.fragment_shader_source = fragment_shader_source;
            if (shader_material) {
                shader_material.fragmentShader = fragment_shader_source;
                shader_material.needsUpdate = true;
            }
            preview_state.preview_error = "";
        } catch (error) {
            if (request_id !== active_shader_request_id) {
                return;
            }
            preview_state.preview_error = `Shader load error: ${error.message}`;
        } finally {
            if (request_id === active_shader_request_id) {
                preview_state.last_shader_load_ms = now() - start_ms;
            }
        }
    };
    await load_shader_for_effect(safe_effect_name);

    const update_resolution = () => {
        const [width, height] = get_element_size(canvas_element);
        preview_descriptor.uniforms.u_resolution = [width, height];
        if (shader_material) {
            const resolution_uniform = shader_material.uniforms.u_resolution.value;
            if (
                resolution_uniform &&
                typeof resolution_uniform.set === "function"
            ) {
                resolution_uniform.set(width, height);
            }
        }
    };

    const unsubscribe_resize = subscribe_global_resize(update_resolution);

    if (input_image) {
        canvas_element.style.background = "transparent";
    } else {
        canvas_element.style.background = "rgb(128, 128, 128)";
    }
    update_overlay_message();

    let animation_handle = null;
    let stopped = false;
    const animate = () => {
        if (stopped) {
            return;
        }
        preview_descriptor.uniforms.u_time = (now() - start_time) / 1000;
        if (shader_material) {
            shader_material.uniforms.u_time.value = preview_descriptor.uniforms.u_time;
            shader_material.uniforms.u_image.value =
                preview_descriptor.uniforms.u_image;
        }
        animation_handle = request_animation_frame(animate);
    };
    animation_handle = request_animation_frame(animate);

    const controller = {
        canvas_element,
        overlay_element,
        preview_descriptor,
        set_input_image(next_image) {
            preview_descriptor.uniforms.u_image = next_image ?? null;
            canvas_element.style.background = next_image
                ? "transparent"
                : "rgb(128, 128, 128)";
            update_overlay_message();
        },
        async set_effect(next_effect_name) {
            preview_descriptor.effect_name = next_effect_name;
            preview_state.effect_name = next_effect_name;
            await load_shader_for_effect(next_effect_name);
            update_overlay_message();
        },
        resize(width, height) {
            if (Number(width) > 0) {
                canvas_element.width = Number(width);
                canvas_element.clientWidth = Number(width);
            }
            if (Number(height) > 0) {
                canvas_element.height = Number(height);
                canvas_element.clientHeight = Number(height);
            }
            update_resolution();
        },
        stop() {
            stopped = true;
            if (animation_handle != null) {
                cancel_animation_frame(animation_handle);
            }
            unsubscribe_resize();
            if (shader_material && typeof shader_material.dispose === "function") {
                shader_material.dispose();
            }
        },
    };

    preview_state.preview_controller = controller;
    preview_state.preview_descriptor = preview_descriptor;
    preview_state.effect_name = effect_name;
    preview_state.preview_error = preview_state.preview_error || "";
    return controller;
}

export function create_effect_change_handler(
    preview_state,
    on_effect_selected,
    now = default_now,
) {
    return (effect_name) => {
        const start_time = now();
        update_preview_effect(preview_state, effect_name);
        if (on_effect_selected) {
            on_effect_selected(effect_name);
        }
        const preview_controller = preview_state.preview_controller;
        if (
            preview_controller &&
            typeof preview_controller.set_effect === "function"
        ) {
            const set_effect_result = preview_controller.set_effect(effect_name);
            if (
                set_effect_result &&
                typeof set_effect_result.then === "function"
            ) {
                set_effect_result.finally(() => {
                    preview_state.last_preview_update_ms = now() - start_time;
                });
                return set_effect_result;
            }
        }
        const elapsed_ms = now() - start_time;
        preview_state.last_preview_update_ms = elapsed_ms;
        return elapsed_ms;
    };
}

export async function initialize_effect_dropdown({
    document_ref,
    container_element,
    preview_state,
    on_effect_selected,
    now = default_now,
    shader_names_loader = listShaders,
}) {
    const shader_names = await shader_names_loader();
    const available_shader_names = shader_names.filter(
        (shader_name) => typeof shader_name === "string" && shader_name.length > 0,
    );
    if (available_shader_names.length == 0) {
        throw new Error("No shaders available for effect selector");
    }
    const selected_effect_name = available_shader_names[0];
    const handle_change = create_effect_change_handler(
        preview_state,
        on_effect_selected,
        now,
    );
    const select_element = create_effect_dropdown_widget(
        document_ref,
        available_shader_names,
        selected_effect_name,
        handle_change,
    );
    container_element.appendChild(select_element);
    handle_change(selected_effect_name);
    return { select_element, shader_names: available_shader_names };
}

function sync_effect_name_output(node, effect_name) {
    if (!node || typeof node !== "object") {
        return;
    }
    if (!node.properties || typeof node.properties !== "object") {
        node.properties = {};
    }
    node.properties.effect_name = effect_name;
    const widgets = Array.isArray(node.widgets) ? node.widgets : [];
    const effect_widget = widgets.find((widget) => widget?.name === "effect_name");
    if (effect_widget) {
        effect_widget.value = effect_name;
    }
    if (typeof node.setDirtyCanvas === "function") {
        node.setDirtyCanvas(true, true);
    }
}

export async function mount_effect_selector_widget_for_node({
    node,
    document_ref = globalThis.document,
    shader_names_loader = listShaders,
    shader_loader = loadShader,
    now = default_now,
    request_animation_frame = default_request_animation_frame,
    cancel_animation_frame = default_cancel_animation_frame,
}) {
    if (!node || typeof node.addDOMWidget !== "function") {
        return null;
    }
    if (!document_ref || typeof document_ref.createElement !== "function") {
        throw new Error("Missing document reference for effect selector widget");
    }

    if (node.__cool_effects_widget_state?.preview_controller) {
        node.__cool_effects_widget_state.preview_controller.stop();
    }

    const container_element = document_ref.createElement("div");
    container_element.setAttribute("data-widget", "cool-effects");
    const widget = node.addDOMWidget(
        "effect_selector",
        "div",
        container_element,
        {
            serialize: false,
            hideOnZoom: false,
        },
    );
    const preview_state = {};
    node.__cool_effects_widget_state = {
        preview_state,
        widget,
        container_element,
    };

    await initialize_effect_dropdown({
        document_ref,
        container_element,
        preview_state,
        shader_names_loader,
        on_effect_selected: (effect_name) => {
            sync_effect_name_output(node, effect_name);
        },
        now,
    });
    await create_live_glsl_preview({
        document_ref,
        container_element,
        effect_name: preview_state.effect_name,
        preview_state,
        shader_loader,
        request_animation_frame,
        cancel_animation_frame,
        now,
    });
    sync_effect_name_output(node, preview_state.effect_name);
    return node.__cool_effects_widget_state;
}

export function register_comfy_extension(
    app_ref,
    {
        document_ref = globalThis.document,
        shader_names_loader = listShaders,
        shader_loader = loadShader,
        now = default_now,
        request_animation_frame = default_request_animation_frame,
        cancel_animation_frame = default_cancel_animation_frame,
    } = {},
) {
    if (!app_ref || typeof app_ref.registerExtension !== "function") {
        return false;
    }

    app_ref.registerExtension({
        name: EXTENSION_NAME,
        async beforeRegisterNodeDef(nodeType, nodeData) {
            if (nodeData?.name !== "CoolEffectSelector") {
                return;
            }
            const previous_on_node_created = nodeType.prototype.onNodeCreated;
            const previous_on_removed = nodeType.prototype.onRemoved;

            nodeType.prototype.onNodeCreated = async function onNodeCreated() {
                if (typeof previous_on_node_created === "function") {
                    previous_on_node_created.apply(this, arguments);
                }
                await mount_effect_selector_widget_for_node({
                    node: this,
                    document_ref,
                    shader_names_loader,
                    shader_loader,
                    now,
                    request_animation_frame,
                    cancel_animation_frame,
                });
            };

            nodeType.prototype.onRemoved = function onRemoved() {
                const preview_controller =
                    this.__cool_effects_widget_state?.preview_state
                        ?.preview_controller;
                if (preview_controller && typeof preview_controller.stop === "function") {
                    preview_controller.stop();
                }
                if (typeof previous_on_removed === "function") {
                    previous_on_removed.apply(this, arguments);
                }
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
