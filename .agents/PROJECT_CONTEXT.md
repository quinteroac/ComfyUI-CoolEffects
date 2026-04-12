# Project Context

<!-- Created or updated by `nvst create project-context`. Cap: 250 lines. -->

## Conventions
- Naming: `snake_case` for Python files/functions/variables; kebab-case for JS files
- Shader files: lowercase with underscores, `.frag` extension (e.g. `glitch.frag`)
- Node registration keys: PascalCase strings in `NODE_CLASS_MAPPINGS` (e.g. `"CoolVideoGenerator"`)
- Git flow: feature branches per iteration (`feature/it_XXXXXX`), commits to `main`
- No inline GLSL strings in node code — all shaders loaded via `shaders/loader.py`

## Tech Stack
- Language(s): Python (backend nodes), JavaScript (frontend widgets)
- Runtime: ComfyUI custom_nodes environment (Python 3.x, aiohttp server)
- Frameworks: ModernGL (headless OpenGL rendering), Three.js + React Three Fiber + drei (frontend preview)
- Key libraries: `moderngl`, `torch`, `numpy`, `aiohttp` (ComfyUI's PromptServer)
- Package manager: `pip` / `requirements.txt` (Python); no bundler for JS — plain ES modules via `fetch`
- Build / tooling: No build step; JS loaded as native ES modules through ComfyUI's extension system

## Code Standards
- Python style: PEP 8; paths resolved with `Path(__file__).parent` (never relative to CWD)
- GL resource cleanup: always in a `try/finally` block — release ctx, texture, program, fbo, vbo
- Error handling: raise `ValueError` (missing shader config), propagate `FileNotFoundError` from `load_shader`
- No ffmpeg or external video-encoding dependencies — output IMAGE batch tensors only
- Shader uniforms contract (all shaders must accept): `uniform sampler2D u_image`, `uniform float u_time`, `uniform vec2 u_resolution`

## Testing Strategy
- Approach: critical-paths only (no TDD mandate in PRDs)
- Runner: `pytest` (standard Python ecosystem)
- Coverage targets: shader loader (`load_shader`, `list_shaders`), tensor shape/dtype assertions
- Test location convention: `tests/` at package root

## Product Architecture
- ComfyUI-CoolEffects is a custom node package that applies GLSL effects to images
- **Effect Selector Node** (`CoolEffectSelector`): IMAGE → IMAGE + EFFECT_NAME (STRING); live preview in node widget via Three.js/R3F
- **Video Generator Node** (`CoolVideoGenerator`): IMAGE + EFFECT_NAME + fps + duration → renders N frames via ModernGL → IMAGE batch `[N, H, W, 3]`
- Shared shader library (`shaders/glsl/*.frag`) is the single source of truth for both Python backend and JS frontend
- HTTP endpoint `GET /cool_effects/shaders` exposes available shader names to the frontend at runtime (no caching)

## Modular Structure
- `__init__.py`: package entry-point; registers nodes and `/cool_effects/shaders` endpoint via `PromptServer.instance.routes`
- `nodes/effect_selector.py`: `CoolEffectSelector` node class
- `nodes/video_generator.py`: `CoolVideoGenerator` node class; renders frames via ModernGL
- `shaders/loader.py`: `load_shader(name) -> str`, `list_shaders() -> list[str]`
- `shaders/glsl/`: GLSL fragment shader files; initial set: `glitch.frag`, `vhs.frag`, `zoom_pulse.frag`
- `shaders/README.md`: uniforms contract documentation for adding new shaders
- `web/effect_selector.js`: ComfyUI frontend extension; React widget with R3F canvas
- `web/shaders/loader.js`: `loadShader(name)`, `listShaders()` — async, uses `fetch`
- `requirements.txt`: must list `moderngl`

## Rendering Pipeline (Video Generator)
- `moderngl.create_standalone_context()` — no display required
- Full-screen quad: two triangles covering NDC `[-1, 1]`
- Per frame `i`: `u_time = i / fps`, bind input image as texture, render to FBO
- Read back: `fbo.read(components=3)` → numpy array → stack into `torch.Tensor [N, H, W, 3]` float32 `[0, 1]`
- Frame count: `round(duration * fps)`
- Node inputs: `fps` (INT, default 30, min 1, max 60), `duration` (FLOAT, default 3.0, min 0.5, max 60.0, step 0.5)

## Implemented Capabilities
<!-- Updated at the end of each iteration by nvst create project-context -->
- (none yet — populated after first iteration Refactor)
