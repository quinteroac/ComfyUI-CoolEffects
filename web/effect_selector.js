import { listShaders, loadShader } from "./shaders/loader.js";

const GLOBAL_RESIZE_CALLBACKS = new Set();
let GLOBAL_RESIZE_LISTENER = null;
export const EXTENSION_NAME = "Comfy.CoolEffects.EffectSelector";

const WEBGL2_VERTEX_SOURCE = `#version 300 es
in vec2 a_pos;
out vec2 v_uv;
void main() {
    v_uv = (a_pos + 1.0) * 0.5;
    gl_Position = vec4(a_pos, 0.0, 1.0);
}`;

const WEBGL2_FALLBACK_FRAGMENT = `#version 300 es
precision highp float;
precision highp sampler2D;
uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
out vec4 fragColor;
void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    fragColor = texture(u_image, uv);
}`;

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
    Object.assign(select_element.style, {
        width: "100%",
        padding: "4px 8px",
        background: "#1a1a1a",
        color: "#ddd",
        border: "1px solid #444",
        borderRadius: "4px",
        fontSize: "13px",
        cursor: "pointer",
        boxSizing: "border-box",
    });
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
    Object.assign(root_element.style, {
        position: "relative",
        width: "100%",
        borderRadius: "4px",
        overflow: "hidden",
        background: "#111",
    });

    const canvas_element = document_ref.createElement("canvas");
    canvas_element.width = 200;
    canvas_element.height = 200;
    canvas_element.setAttribute("data-renderer", "webgl2");
    canvas_element.setAttribute("aria-label", "Live GLSL preview");
    Object.assign(canvas_element.style, {
        display: "block",
        width: "100%",
        height: "auto",
        aspectRatio: "1",
    });
    root_element.appendChild(canvas_element);

    const overlay_element = document_ref.createElement("div");
    overlay_element.setAttribute("data-preview-overlay", "cool-effects");
    overlay_element.setAttribute("aria-live", "polite");
    overlay_element.setAttribute("role", "status");
    Object.assign(overlay_element.style, {
        position: "absolute",
        bottom: "4px",
        left: "4px",
        right: "4px",
        color: "#ff4444",
        fontSize: "11px",
        lineHeight: "1.3",
        pointerEvents: "none",
        textShadow: "0 1px 2px rgba(0,0,0,0.8)",
    });
    overlay_element.textContent = "";
    root_element.appendChild(overlay_element);

    return { root_element, canvas_element, overlay_element };
}

export function create_placeholder_texture(document_ref, size = 512) {
    if (!document_ref || typeof document_ref.createElement !== "function") {
        throw new Error("Missing document reference for placeholder texture");
    }

    const resolved_size =
        Number(size) > 0 ? Math.round(Number(size)) : 512;
    const canvas_element = document_ref.createElement("canvas");
    canvas_element.width = resolved_size;
    canvas_element.height = resolved_size;
    const context =
        typeof canvas_element.getContext === "function"
            ? canvas_element.getContext("2d")
            : null;
    if (!context) {
        return canvas_element;
    }

    const base_gradient = context.createLinearGradient(
        0,
        0,
        resolved_size,
        resolved_size,
    );
    base_gradient.addColorStop(0, "rgb(22, 58, 122)");
    base_gradient.addColorStop(1, "rgb(187, 214, 255)");
    context.fillStyle = base_gradient;
    context.fillRect(0, 0, resolved_size, resolved_size);

    const checker_size = Math.max(16, Math.floor(resolved_size / 16));
    for (let y = 0; y < resolved_size; y += checker_size) {
        for (let x = 0; x < resolved_size; x += checker_size) {
            if (((x + y) / checker_size) % 2 === 0) {
                context.fillStyle = "rgba(255, 255, 255, 0.1)";
                context.fillRect(x, y, checker_size, checker_size);
            }
        }
    }

    context.strokeStyle = "rgba(255, 255, 255, 0.4)";
    context.lineWidth = Math.max(1, Math.floor(resolved_size / 256));
    context.beginPath();
    context.moveTo(0, resolved_size * 0.5);
    context.lineTo(resolved_size, resolved_size * 0.5);
    context.moveTo(resolved_size * 0.5, 0);
    context.lineTo(resolved_size * 0.5, resolved_size);
    context.stroke();

    return canvas_element;
}

export function create_preview_descriptor({
    fragment_shader_source,
    effect_name,
    input_image,
    canvas_element,
    renderer_mode = "webgl2",
}) {
    const [width, height] = get_element_size(canvas_element);
    return {
        renderer: renderer_mode,
        effect_name,
        fragment_shader_source,
        uniforms: {
            u_image: input_image ?? null,
            u_time: 0,
            u_resolution: [width, height],
        },
    };
}

function adapt_fragment_for_webgl2(source) {
    const stripped = source.replace(/^\s*#version\s+\d+([^\S\n]+\w+)?\s*$/m, "");
    const has_float_precision = /precision\s+\w+\s+float/.test(stripped);
    const has_sampler_precision = /precision\s+\w+\s+sampler2D/.test(stripped);
    const float_line = has_float_precision ? "" : "precision highp float;\n";
    const sampler_line = has_sampler_precision ? "" : "precision highp sampler2D;\n";
    return `#version 300 es\n${float_line}${sampler_line}${stripped}`;
}

function compile_webgl2_shader(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        const log = gl.getShaderInfoLog(shader) || "Shader compile failed";
        gl.deleteShader(shader);
        throw new Error(log);
    }
    return shader;
}

function link_webgl2_program(gl, vert_shader, frag_shader) {
    const program = gl.createProgram();
    gl.attachShader(program, vert_shader);
    gl.attachShader(program, frag_shader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        const log = gl.getProgramInfoLog(program) || "Program link failed";
        gl.deleteProgram(program);
        throw new Error(log);
    }
    return program;
}

export function create_webgl2_renderer(canvas_element) {
    const gl =
        typeof canvas_element.getContext === "function"
            ? canvas_element.getContext("webgl2")
            : null;
    if (!gl) return null;

    const quad_verts = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
    const vbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(gl.ARRAY_BUFFER, quad_verts, gl.STATIC_DRAW);

    let program = null;
    let a_pos_loc = -1;
    let u_time_loc = null;
    let u_resolution_loc = null;
    let u_image_loc = null;
    let gl_texture = null;
    const uniform_location_cache = new Map();

    const get_uniform_location = (name) => {
        if (!program) {
            return null;
        }
        if (uniform_location_cache.has(name)) {
            return uniform_location_cache.get(name);
        }
        const location = gl.getUniformLocation(program, name);
        uniform_location_cache.set(name, location);
        return location;
    };

    const build_program = (frag_source) => {
        const vert_shader = compile_webgl2_shader(
            gl,
            gl.VERTEX_SHADER,
            WEBGL2_VERTEX_SOURCE,
        );
        const frag_shader = compile_webgl2_shader(
            gl,
            gl.FRAGMENT_SHADER,
            frag_source,
        );
        const new_program = link_webgl2_program(gl, vert_shader, frag_shader);
        gl.deleteShader(vert_shader);
        gl.deleteShader(frag_shader);
        if (program) gl.deleteProgram(program);
        program = new_program;
        uniform_location_cache.clear();
        gl.useProgram(program);
        a_pos_loc = gl.getAttribLocation(program, "a_pos");
        u_time_loc = get_uniform_location("u_time");
        u_resolution_loc = get_uniform_location("u_resolution");
        u_image_loc = get_uniform_location("u_image");
    };

    const set_fragment_shader = (raw_source) => {
        const adapted = adapt_fragment_for_webgl2(raw_source);
        build_program(adapted);
    };

    const set_image_texture = (image_source) => {
        if (!image_source) return;
        if (gl_texture) gl.deleteTexture(gl_texture);
        gl_texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, gl_texture);
        gl.texImage2D(
            gl.TEXTURE_2D,
            0,
            gl.RGBA,
            gl.RGBA,
            gl.UNSIGNED_BYTE,
            image_source,
        );
        gl.generateMipmap(gl.TEXTURE_2D);
        gl.texParameteri(
            gl.TEXTURE_2D,
            gl.TEXTURE_MIN_FILTER,
            gl.LINEAR_MIPMAP_LINEAR,
        );
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    };

    const set_uniform = (name, value) => {
        if (!program) return;
        const numeric_value = Number(value);
        if (!Number.isFinite(numeric_value)) return;
        const uniform_location = get_uniform_location(name);
        if (uniform_location === null) return;
        gl.useProgram(program);
        gl.uniform1f(uniform_location, numeric_value);
    };

    const set_uniform_array = (name, values) => {
        if (!program) return;
        if (!Array.isArray(values) && !ArrayBuffer.isView(values)) return;
        const uniform_location = get_uniform_location(name);
        if (uniform_location === null) return;

        const typed_values = new Float32Array(values.length);
        for (let index = 0; index < values.length; index += 1) {
            const numeric_value = Number(values[index]);
            typed_values[index] = Number.isFinite(numeric_value) ? numeric_value : 0;
        }

        gl.useProgram(program);
        gl.uniform1fv(uniform_location, typed_values);
    };

    const render = (time_secs) => {
        if (!program) return;
        const w = canvas_element.width;
        const h = canvas_element.height;
        gl.viewport(0, 0, w, h);
        gl.useProgram(program);
        gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
        gl.enableVertexAttribArray(a_pos_loc);
        gl.vertexAttribPointer(a_pos_loc, 2, gl.FLOAT, false, 0, 0);
        if (u_time_loc !== null) gl.uniform1f(u_time_loc, time_secs);
        if (u_resolution_loc !== null) gl.uniform2f(u_resolution_loc, w, h);
        if (u_image_loc !== null && gl_texture) {
            gl.activeTexture(gl.TEXTURE0);
            gl.bindTexture(gl.TEXTURE_2D, gl_texture);
            gl.uniform1i(u_image_loc, 0);
        }
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    };

    const dispose = () => {
        if (program) gl.deleteProgram(program);
        if (gl_texture) gl.deleteTexture(gl_texture);
        gl.deleteBuffer(vbo);
    };

    // Load fallback shader so canvas renders immediately
    build_program(WEBGL2_FALLBACK_FRAGMENT);

    return {
        set_fragment_shader,
        set_image_texture,
        set_uniform,
        set_uniform_array,
        render,
        dispose,
        gl,
    };
}

export async function create_live_glsl_preview({
    document_ref,
    container_element,
    effect_name,
    input_image = null,
    preview_state = {},
    keep_webgl_error_on_shader_load = false,
    now = default_now,
    shader_loader = loadShader,
    request_animation_frame = default_request_animation_frame,
    cancel_animation_frame = default_cancel_animation_frame,
}) {
    const { root_element, canvas_element, overlay_element } =
        create_canvas_preview_surface(document_ref);
    container_element.appendChild(root_element);

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
        overlay_element.textContent = preview_state.preview_error || "";
    };

    const renderer = create_webgl2_renderer(canvas_element);

    if (!renderer) {
        preview_state.preview_error = "WebGL2 not available";
        update_overlay_message();
    }

    if (renderer && input_image) {
        renderer.set_image_texture(input_image);
    }

    let active_shader_request_id = 0;
    const load_shader_for_effect = async (next_effect_name) => {
        const request_id = active_shader_request_id + 1;
        active_shader_request_id = request_id;
        const start_ms = now();
        try {
            const frag_source = await shader_loader(next_effect_name);
            if (request_id !== active_shader_request_id) return;
            preview_descriptor.fragment_shader_source = frag_source;
            if (renderer) {
                renderer.set_fragment_shader(frag_source);
                if (input_image) renderer.set_image_texture(input_image);
            }
            if (renderer || !keep_webgl_error_on_shader_load) {
                preview_state.preview_error = "";
            }
        } catch (error) {
            if (request_id !== active_shader_request_id) return;
            if (renderer || !keep_webgl_error_on_shader_load) {
                preview_state.preview_error = `Shader error: ${error.message}`;
            }
        } finally {
            if (request_id === active_shader_request_id) {
                preview_state.last_shader_load_ms = now() - start_ms;
                update_overlay_message();
            }
        }
    };

    await load_shader_for_effect(safe_effect_name);

    const unsubscribe_resize = subscribe_global_resize(() => {
        const [width, height] = get_element_size(canvas_element);
        preview_descriptor.uniforms.u_resolution = [width, height];
    });

    const start_time = now();
    let animation_handle = null;
    let stopped = false;

    const animate = () => {
        if (stopped) return;
        const time_secs = (now() - start_time) / 1000;
        preview_descriptor.uniforms.u_time = time_secs;
        if (renderer) renderer.render(time_secs);
        animation_handle = request_animation_frame(animate);
    };
    animation_handle = request_animation_frame(animate);

    const controller = {
        canvas_element,
        overlay_element,
        preview_descriptor,
        set_uniform(uniform_name, value) {
            const numeric_value = Number(value);
            if (
                typeof uniform_name !== "string" ||
                uniform_name.length === 0 ||
                !Number.isFinite(numeric_value)
            ) {
                return;
            }
            preview_descriptor.uniforms[uniform_name] = numeric_value;
            if (renderer) {
                renderer.set_uniform(uniform_name, numeric_value);
            }
        },
        set_uniform_array(uniform_name, values) {
            if (
                typeof uniform_name !== "string" ||
                uniform_name.length === 0 ||
                (!Array.isArray(values) && !ArrayBuffer.isView(values))
            ) {
                return;
            }
            const numeric_values = Array.from(values, (value) => {
                const numeric_value = Number(value);
                return Number.isFinite(numeric_value) ? numeric_value : 0;
            });
            preview_descriptor.uniforms[uniform_name] = numeric_values;
            if (renderer) {
                renderer.set_uniform_array(uniform_name, numeric_values);
            }
        },
        set_input_image(next_image) {
            preview_descriptor.uniforms.u_image = next_image ?? null;
            if (renderer && next_image) renderer.set_image_texture(next_image);
            update_overlay_message();
        },
        async set_effect(next_effect_name) {
            preview_descriptor.effect_name = next_effect_name;
            preview_state.effect_name = next_effect_name;
            await load_shader_for_effect(next_effect_name);
            update_overlay_message();
        },
        resize(width, height) {
            if (Number(width) > 0) canvas_element.width = Number(width);
            if (Number(height) > 0) canvas_element.height = Number(height);
            const [w, h] = get_element_size(canvas_element);
            preview_descriptor.uniforms.u_resolution = [w, h];
        },
        stop() {
            stopped = true;
            if (animation_handle != null) {
                cancel_animation_frame(animation_handle);
            }
            unsubscribe_resize();
            if (renderer) renderer.dispose();
        },
    };

    preview_state.preview_controller = controller;
    preview_state.preview_descriptor = preview_descriptor;
    preview_state.effect_name = effect_name;
    preview_state.render_backend = "webgl2";
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

function hide_builtin_combo_widget(node) {
    const widgets = Array.isArray(node.widgets) ? node.widgets : [];
    // The built-in COMBO widget ComfyUI generates from INPUT_TYPES has type "combo"
    // and is not a DOM widget. Hide it so only our custom dropdown shows.
    const combo_widget = widgets.find(
        (w) => w?.name === "effect_name" && w?.type !== "div",
    );
    if (!combo_widget) return;
    combo_widget.hidden = true;
    combo_widget.computeSize = () => [0, -4];
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

    // Hide the auto-generated COMBO widget from ComfyUI so only our dropdown shows
    hide_builtin_combo_widget(node);

    const container_element = document_ref.createElement("div");
    container_element.setAttribute("data-widget", "cool-effects");
    Object.assign(container_element.style, {
        display: "flex",
        flexDirection: "column",
        gap: "6px",
        padding: "6px 8px 8px",
        boxSizing: "border-box",
        width: "100%",
    });
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
    const placeholder_texture = create_placeholder_texture(document_ref, 512);
    await create_live_glsl_preview({
        document_ref,
        container_element,
        effect_name: preview_state.effect_name,
        input_image: placeholder_texture,
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
