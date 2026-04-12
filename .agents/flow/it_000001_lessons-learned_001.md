# Lessons Learned — Iteration 000001

## US-001 — Package Discovery

**Summary:** Implemented a minimal package entrypoint by adding `__init__.py` exports for `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`, and added discovery-focused tests for import safety and exported mappings.

**Key Decisions:** Kept `__init__.py` intentionally side-effect free (no ComfyUI-only imports) so package discovery works reliably in both ComfyUI and standalone test environments.

**Pitfalls Encountered:** The repository started as scaffolding-only, so tests had to import `__init__.py` directly from file path rather than a standard package import.

**Useful Context for Future Agents:** For early user stories, import-path based tests (`importlib.util.spec_from_file_location`) are a robust pattern when the custom node directory name includes hyphens and is not importable as a normal Python package name.

## US-002 — Python Shader Loader

**Summary:** Added `shaders/loader.py` with `load_shader(name)` and `list_shaders()`, created initial GLSL shader assets under `shaders/glsl/`, and added pytest coverage for loader behavior and path handling.

**Key Decisions:** Kept loader pathing anchored to `Path(__file__).parent` via a module-level `SHADERS_DIR`; relied on `Path.read_text()` so missing shader behavior naturally propagates as `FileNotFoundError`; used import-by-file tests to match repository import conventions.

**Pitfalls Encountered:** `pytest` was not available as a direct shell command in this environment, so test execution should use `python3 -m pytest` when the pytest module is installed.

**Useful Context for Future Agents:** The shader loader intentionally has no CWD dependence; tests use `monkeypatch.chdir(tmp_path)` to enforce this and can be reused for future filesystem-related utilities.

## US-003 — Shader List Endpoint

**Summary:** Added a package-import-time route registration for `GET /cool_effects/shaders`, implemented an async JSON endpoint handler backed by `list_shaders()`, and added endpoint-focused tests for registration, response metadata, and runtime freshness.

**Key Decisions:** Kept import-by-path loading for the shader loader in `__init__.py` so behavior remains stable regardless of package name/import mode; made route registration idempotent with a guard flag on `PromptServer.instance.routes`; resolved endpoint output at request time by calling `list_shaders()` inside the handler.

**Pitfalls Encountered:** The environment still lacks a runnable pytest installation (`python3 -m pytest` unavailable, `pip`/`ensurepip` unavailable), so verification could not be executed with the normal test runner.

**Useful Context for Future Agents:** For ComfyUI route tests, injecting a temporary `server` module into `sys.modules` with a fake `PromptServer.instance.routes.get` decorator works well to verify import-time registration without requiring a live Comfy runtime.

## US-004 — JavaScript Shader Loader

**Summary:** Added `web/shaders/loader.js` exporting async `listShaders()` and `loadShader(name)` for frontend reuse, plus tests that validate fetch URLs, successful payload handling, and required error messages for non-200 responses.

**Key Decisions:** Used `new URL("../../shaders/glsl/<name>.frag", import.meta.url)` so shader file resolution is tied to module location rather than runtime CWD or hardcoded extension paths; kept error messages exactly aligned to the story AC text.

**Pitfalls Encountered:** JavaScript behavior is easiest to verify through Node ESM subprocess tests from pytest, but this environment still lacks a runnable pytest module, so only direct module import sanity checks could be executed here.

**Useful Context for Future Agents:** The JS loader now centralizes both endpoint listing and GLSL source loading; frontend widgets can import from `../shaders/loader.js` and avoid duplicate fetch/error logic.

## US-005 — Initial Shader Effects

**Summary:** Upgraded `glitch.frag`, `vhs.frag`, and `zoom_pulse.frag` to distinct GLSL effects that compile under ModernGL, added `shaders/README.md` documenting the uniform contract, and added AC-focused shader tests.

**Key Decisions:** Standardized all fragment shaders on `#version 330` with `out vec4 frag_color` for ModernGL compatibility and used a shared test vertex shader to compile each fragment shader in isolation.

**Pitfalls Encountered:** ModernGL standalone context availability can vary by environment/backend, so the compile test intentionally skips when no compatible context can be created.

**Useful Context for Future Agents:** Keep shader source files explicit about required uniform declarations (`u_image`, `u_time`, `u_resolution`); this ensures compatibility for both loader validation and future rendering nodes that swap shaders dynamically.
