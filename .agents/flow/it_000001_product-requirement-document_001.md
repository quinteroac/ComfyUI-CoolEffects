# Package Scaffold + GLSL Shader Library

## Context

ComfyUI-CoolEffects is a new custom node package that generates image batches from
a single image using GLSL effects. Before any node can be built, the project needs a
clean package structure and a shared shader library that both the Python backend
(ModernGL) and the JavaScript frontend (Three.js) can consume. Centralising shaders
in one place prevents drift between the preview and the final render.

A lightweight HTTP endpoint registered via ComfyUI's `PromptServer` exposes the list
of available shaders so the frontend can populate its dropdown dynamically at load time
without any static codegen step.

## Goals

- Establish the canonical directory layout for the package.
- Provide a Python shader loader that reads `.frag` files from the shaders directory.
- Provide a JavaScript shader loader that reads the same `.frag` files at runtime via fetch.
- Expose a `/cool_effects/shaders` HTTP endpoint listing available shader names.
- Ship 3–5 initial GLSL fragment shader effects as working examples.
- Register the package with ComfyUI so it is discoverable.

## User Stories

### US-001: Package Discovery
**As a** ComfyUI user, **I want** the ComfyUI-CoolEffects package to load without errors
**so that** I can see it listed in the ComfyUI node browser even before any nodes are wired.

**Acceptance Criteria:**
- [ ] ComfyUI starts without Python errors when ComfyUI-CoolEffects is present in `custom_nodes/`.
- [ ] `__init__.py` exports `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` (both can be empty dicts initially).
- [ ] ComfyUI server log shows no import errors for this package.

### US-002: Python Shader Loader
**As a** backend node developer, **I want** to call `load_shader("glitch")` and receive the
GLSL source string **so that** I can pass it directly to ModernGL without path manipulation.

**Acceptance Criteria:**
- [ ] `shaders/loader.py` exports a `load_shader(name: str) -> str` function.
- [ ] `load_shader("glitch")` returns the full text of `shaders/glsl/glitch.frag`.
- [ ] `load_shader("nonexistent")` raises `FileNotFoundError` with a message that includes the shader name.
- [ ] The loader resolves paths relative to its own file location, not the CWD.
- [ ] `shaders/loader.py` exports a `list_shaders() -> list[str]` function that returns shader names (without extension) sorted alphabetically.

### US-003: Shader List Endpoint
**As a** frontend widget, **I want** to fetch `GET /cool_effects/shaders` and receive a
JSON array of shader names **so that** the effect dropdown is always in sync with shaders
on disk without a server restart.

**Acceptance Criteria:**
- [ ] The endpoint is registered via `PromptServer.instance.routes` at package import time.
- [ ] `GET /cool_effects/shaders` returns HTTP 200 with `Content-Type: application/json`
  and body `{"shaders": ["glitch", "vhs", "zoom_pulse", ...]}` — names sorted alphabetically.
- [ ] The response reflects the actual `.frag` files in `shaders/glsl/` at the time of the
  request (no caching between requests).

### US-004: JavaScript Shader Loader
**As a** frontend node developer, **I want** to `import { loadShader, listShaders } from "../shaders/loader.js"`
**so that** I can populate the dropdown and feed GLSL source to Three.js without duplicating code.

**Acceptance Criteria:**
- [ ] `web/shaders/loader.js` exports `listShaders()` — async, fetches `GET /cool_effects/shaders`,
  returns the `shaders` array.
- [ ] `web/shaders/loader.js` exports `loadShader(name)` — async, fetches the `.frag` file
  from the package's web directory, returns its text.
- [ ] If `listShaders()` receives a non-200 response, it throws `Error("Failed to list shaders: <status>")`.
- [ ] If `loadShader(name)` receives a non-200 response, it throws `Error("Shader not found: <name>")`.

### US-005: Initial Shader Effects
**As a** developer, **I want** at least 3 working GLSL fragment shaders available **so that**
I can verify the loader and demonstrate the package's range of effects.

**Acceptance Criteria:**
- [ ] The following shader files exist and compile without GLSL errors when loaded by ModernGL:
  `shaders/glsl/glitch.frag`, `shaders/glsl/vhs.frag`, `shaders/glsl/zoom_pulse.frag`.
- [ ] Each shader accepts: `uniform sampler2D u_image`, `uniform float u_time`,
  `uniform vec2 u_resolution`, and writes a colour to `fragColor`.
- [ ] A `shaders/README.md` documents the required uniforms contract for adding new shaders.

---

## Functional Requirements

- FR-1: The package root must contain `__init__.py`, `requirements.txt`, and `README.md`.
- FR-2: The directory `shaders/glsl/` must hold all `.frag` shader files.
- FR-3: `shaders/loader.py` must locate shader files using `Path(__file__).parent` as the base.
- FR-4: The `/cool_effects/shaders` endpoint must be registered in `__init__.py` using `PromptServer.instance.routes.get`.
- FR-5: `web/shaders/loader.js` must use `fetch` to retrieve both the shader list and shader source — no bundling step required.
- FR-6: Each shader must follow the uniforms contract: `u_image` (sampler2D), `u_time` (float), `u_resolution` (vec2).
- FR-7: `requirements.txt` must list `moderngl` as a dependency.

## Non-Goals

- Implementing any ComfyUI node with inputs/outputs (covered in PRDs 002 and 003).
- Three.js or React integration (covered in PRD 002).
- Video encoding or ffmpeg integration (explicitly out of scope for the whole package).
- Hot-reload of shaders during development.
- Authentication or rate-limiting on the shaders endpoint.

## Open Questions

- Should shaders also expose a `u_intensity` uniform as a standard parameter, or leave
  per-effect parameters to individual shader files?
