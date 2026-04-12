const SHADER_LIST_ENDPOINT = "/cool_effects/shaders";

export async function listShaders() {
    const response = await fetch(SHADER_LIST_ENDPOINT);
    if (!response.ok) {
        throw new Error(`Failed to list shaders: ${response.status}`);
    }

    const payload = await response.json();
    if (Array.isArray(payload)) {
        return payload;
    }
    if (!payload || !Array.isArray(payload.shaders)) {
        throw new Error("Invalid shader list payload");
    }
    return payload.shaders;
}

export async function loadShader(name) {
    const response = await fetch(`/cool_effects/shaders/${encodeURIComponent(name)}`);
    if (!response.ok) {
        throw new Error(`Shader not found: ${name}`);
    }

    return response.text();
}
