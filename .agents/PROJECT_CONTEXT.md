# Project Context

<!-- Created or updated by `nvst create project-context`. Cap: 250 lines. -->

## Conventions
- Naming: `snake_case` for Python files/functions/variables; kebab-case for JS files
- Shader files: lowercase with underscores — `.frag` for fragment shaders, `.vert` for vertex shaders
- Node registration keys: PascalCase strings in `NODE_CLASS_MAPPINGS` (e.g. `"CoolGlitchEffect"`)
- Git flow: feature branches per iteration (`feature/it_XXXXXX`), commits to `main`
- No inline GLSL strings in node code — all shaders loaded via `shaders/loader.py`
- Node modules loaded via `importlib.util.spec_from_file_location` (not standard `import`) in `__init__.py`
- Each effect has its own Python node file (`nodes/<effect>_effect.py`) and JS extension file (`web/<effect>_effect.js`)

## Tech Stack
- Language(s): Python (backend nodes), JavaScript (frontend widgets)
- Runtime: ComfyUI custom_nodes environment (Python 3.x, aiohttp server)
- Frameworks: ModernGL + EGL (headless OpenGL rendering); WebGL2 canvas directly (frontend preview, no Three.js/R3F)
- Key libraries: `moderngl`, `torch`, `numpy`, `aiohttp` (ComfyUI's PromptServer), `comfy_api.latest` (VIDEO assembly)
- Package manager: `pip` / `requirements.txt` (Python); no bundler for JS — plain ES modules
- Build / tooling: No build step; JS loaded as native ES modules through ComfyUI's extension system
- JS tests: `bun` runner (`tests/bun-smoke.test.js`)

## Code Standards
- Python style: PEP 8; paths resolved with `Path(__file__).resolve().parent` (never relative to CWD)
- GL resource cleanup: always in a `try/finally` block — release vao, vbo, fbo, renderbuffer, texture, program, ctx in that order
- Error handling: raise `ValueError` (bad params/shader config); `try/except ImportError` guards optional deps (`moderngl`, `folder_paths`, `aiohttp`)
- `CoolVideoGenerator` is registered only when `moderngl` import succeeds; missing dep is a soft failure
- Shader uniforms contract (all fragment shaders must accept): `uniform sampler2D u_image`, `uniform float u_time`, `uniform vec2 u_resolution`
- EFFECT_PARAMS custom type: `{"effect_name": str, "params": dict}` — built by `build_effect_params()`, merged by `merge_params()`

## Testing Strategy
- Approach: critical-paths only (no TDD mandate in PRDs)
- Runner: `pytest` (Python), `bun` (JavaScript smoke tests)
- Coverage targets: shader loader (`load_shader`, `load_vertex_shader`, `list_shaders`), tensor shape/dtype assertions, effect node EFFECT_PARAMS contract
- Test location convention: `tests/` at package root

## Product Architecture
- ComfyUI-CoolEffects is a custom node package that applies GLSL effects to images and produces videos
- **Effect Parameter Nodes** (e.g. `CoolGlitchEffect`, `CoolVHSEffect`, `CoolZoomPulseEffect`, pan nodes): parameterised inputs → `EFFECT_PARAMS` output; live WebGL2 preview in node widget
- **Effect Selector Node** (`CoolEffectSelector`): IMAGE → IMAGE + EFFECT_NAME (STRING); WebGL2 live preview via canvas widget
- **Video Generator Node** (`CoolVideoGenerator`): IMAGE + one or more `EFFECT_PARAMS` + fps + duration (+ optional AUDIO) → VIDEO; effects applied sequentially; canvas video preview in node
- **Video Player Node** (`CoolVideoPlayer`): VIDEO input → no outputs (OUTPUT_NODE); renders inline video preview in node widget
- Shared shader library (`shaders/glsl/*.frag`) is the single source of truth for both Python backend and JS frontend
- HTTP endpoints: `GET /cool_effects/shaders` → JSON list of shader names; `GET /cool_effects/shaders/{name}` → raw GLSL text

## Modular Structure
- `__init__.py`: package entry-point; loads all node modules via `importlib`; registers all nodes and HTTP routes
- `nodes/effect_params.py`: `EFFECT_PARAMS` type constant, `DEFAULT_PARAMS` dict, `build_effect_params()`, `merge_params()`
- `nodes/effect_selector.py`: `CoolEffectSelector` node class
- `nodes/glitch_effect.py`, `nodes/vhs_effect.py`, `nodes/zoom_pulse_effect.py`: dedicated effect parameter nodes
- `nodes/pan_left_effect.py`, `nodes/pan_right_effect.py`, `nodes/pan_up_effect.py`, `nodes/pan_down_effect.py`, `nodes/pan_diagonal_effect.py`: pan effect nodes (speed, origin_x, origin_y, zoom inputs)
- `nodes/video_generator.py`: `CoolVideoGenerator`; renders frames via ModernGL/EGL; assembles VIDEO via `comfy_api.latest`
- `nodes/video_player.py`: `CoolVideoPlayer`; OUTPUT_NODE; normalises VIDEO payload and exposes preview URL
- `shaders/loader.py`: `load_shader(name) -> str`, `load_vertex_shader(name) -> str`, `list_shaders() -> list[str]`
- `shaders/glsl/`: fragment shaders (`glitch.frag`, `vhs.frag`, `zoom_pulse.frag`, `pan_*.frag`) + `fullscreen_quad.vert`
- `web/effect_selector.js`: ComfyUI extension for `CoolEffectSelector`; WebGL2 canvas widget with `create_live_glsl_preview`
- `web/effect_node_widget.js`: shared factory (`mount_effect_node_widget`, `apply_effect_widget_uniform_from_widget`) used by all per-effect JS extensions
- `web/glitch_effect.js`, `web/vhs_effect.js`, `web/zoom_pulse_effect.js`, `web/pan_*_effect.js`: per-effect frontend extensions
- `web/video_generator.js`: frontend extension for `CoolVideoGenerator`; canvas video preview widget
- `web/video_player.js`: frontend extension for `CoolVideoPlayer`; canvas video preview widget
- `web/shaders/loader.js`: `loadShader(name)`, `listShaders()` — async, uses `fetch`
- `requirements.txt`: lists `moderngl`

## Rendering Pipeline (Video Generator)
- `moderngl.create_standalone_context(backend="egl")` — headless, no display required
- Vertex shader loaded from `shaders/glsl/fullscreen_quad.vert`; full-screen quad via two triangles
- Per frame `i`: set `u_time = i / fps`, update per-effect uniforms from merged params, render to FBO
- Multi-effect chaining: output tensor of effect N becomes input image for effect N+1
- Read back: `fbo.read(components=3)` → numpy → `torch.Tensor [N, H, W, 3]` float32 `[0, 1]`
- Frame count: `round(duration * fps)`; `effect_count` input (1–8) controls how many `effect_params_N` slots are active
- VIDEO assembled via `comfy_api.latest.InputImpl.VideoFromComponents` with optional audio track

## Implemented Capabilities
- GLSL effect parameter nodes: Glitch, VHS, Zoom Pulse (it_000003–it_000005)
- Pan effect nodes: Pan Left, Pan Right, Pan Up, Pan Down, Pan Diagonal (it_000006)
- Effect Selector node with WebGL2 live preview (it_000003)
- Video Generator node: multi-effect chaining, AUDIO input, VIDEO output, canvas preview (it_000007–it_000008)
- Video Player node: VIDEO input → inline canvas video preview with download (it_000008)
- Shared `effect_node_widget.js` factory for per-effect WebGL2 previews (it_000005–it_000006)
- HTTP endpoints for shader discovery and source fetching (`/cool_effects/shaders`, `/cool_effects/shaders/{name}`)
