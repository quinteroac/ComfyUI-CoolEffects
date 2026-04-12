const SHADER_LIST_ENDPOINT = "/cool_effects/shaders";

export async function listShaders() {
    const response = await fetch(SHADER_LIST_ENDPOINT);
    if (!response.ok) {
        throw new Error(`Failed to list shaders: ${response.status}`);
    }

    return response.json();
}

export async function loadShader(name) {
    const shader_path = new URL(
        `../../shaders/glsl/${encodeURIComponent(name)}.frag`,
        import.meta.url,
    );
    const response = await fetch(shader_path);
    if (!response.ok) {
        throw new Error(`Shader not found: ${name}`);
    }

    return response.text();
}
