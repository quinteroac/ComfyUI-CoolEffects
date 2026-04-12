# Lessons Learned — Iteration 000001

## US-001 — Package Discovery

**Summary:** Implemented a minimal package entrypoint by adding `__init__.py` exports for `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`, and added discovery-focused tests for import safety and exported mappings.

**Key Decisions:** Kept `__init__.py` intentionally side-effect free (no ComfyUI-only imports) so package discovery works reliably in both ComfyUI and standalone test environments.

**Pitfalls Encountered:** The repository started as scaffolding-only, so tests had to import `__init__.py` directly from file path rather than a standard package import.

**Useful Context for Future Agents:** For early user stories, import-path based tests (`importlib.util.spec_from_file_location`) are a robust pattern when the custom node directory name includes hyphens and is not importable as a normal Python package name.

