import { listShaders, loadShader } from "./shaders/loader.js";

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
}) {
    const [width, height] = get_element_size(canvas_element);
    return {
        renderer: "r3f",
        three_canvas: true,
        mesh: "plane",
        effect_name,
        fragment_shader_source,
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

    try {
        preview_descriptor.fragment_shader_source = await shader_loader(
            safe_effect_name,
        );
    } catch (error) {
        overlay_element.textContent = `Shader load error: ${error.message}`;
        preview_state.preview_error = overlay_element.textContent;
    }

    const update_resolution = () => {
        const [width, height] = get_element_size(canvas_element);
        preview_descriptor.uniforms.u_resolution = [width, height];
    };

    const resize_listener = () => {
        update_resolution();
    };
    if (typeof globalThis.addEventListener === "function") {
        globalThis.addEventListener("resize", resize_listener);
    }

    if (input_image) {
        canvas_element.style.background = "transparent";
        overlay_element.textContent = "";
    } else {
        canvas_element.style.background = "rgb(128, 128, 128)";
        overlay_element.textContent = "Connect an image to preview this effect.";
    }

    let animation_handle = null;
    let stopped = false;
    const animate = () => {
        if (stopped) {
            return;
        }
        preview_descriptor.uniforms.u_time = (now() - start_time) / 1000;
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
            overlay_element.textContent = next_image
                ? ""
                : "Connect an image to preview this effect.";
        },
        async set_effect(next_effect_name) {
            preview_descriptor.effect_name = next_effect_name;
            preview_state.effect_name = next_effect_name;
            overlay_element.textContent = "";
            try {
                preview_descriptor.fragment_shader_source = await shader_loader(
                    next_effect_name,
                );
                preview_state.preview_error = "";
            } catch (error) {
                overlay_element.textContent = `Shader load error: ${error.message}`;
                preview_state.preview_error = overlay_element.textContent;
            }
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
            if (typeof globalThis.removeEventListener === "function") {
                globalThis.removeEventListener("resize", resize_listener);
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
            preview_controller.set_effect(effect_name);
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
