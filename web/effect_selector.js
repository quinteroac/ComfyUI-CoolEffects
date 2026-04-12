import { listShaders } from "./shaders/loader.js";

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
