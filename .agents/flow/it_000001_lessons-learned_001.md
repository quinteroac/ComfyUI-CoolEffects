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
