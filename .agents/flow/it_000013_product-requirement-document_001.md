# Requirement: Nuevos nodos de efecto Zoom y Dolly

## Context
El proyecto necesita ampliar el set de efectos disponibles en ComfyUI-CoolEffects para cubrir movimientos de cámara básicos. Actualmente no existen nodos dedicados para zoom in, zoom out, dolly in y dolly out con su propio flujo de parámetros y previsualización.

## Goals
- Incorporar 4 nuevos nodos de efecto: Zoom In, Zoom Out, Dolly In y Dolly Out.
- Mantener consistencia con la arquitectura existente de `EFFECT_PARAMS`, shaders compartidos y widgets WebGL2.
- Permitir que los 4 efectos funcionen dentro de `CoolVideoGenerator` sin cambios manuales del usuario.

## User Stories
Each story must be small enough to implement in one focused session.

### US-001: Nodo Zoom In
**As a** usuario final de ComfyUI, **I want** un nodo Zoom In que emita `EFFECT_PARAMS` y tenga preview en vivo **so that** pueda aplicar acercamiento progresivo en mis composiciones.

**Acceptance Criteria:**
- [ ] Existe un nodo registrado como `CoolZoomInEffect` con nombre visible en UI.
- [ ] El nodo expone parámetros de zoom in editables y emite un único output `EFFECT_PARAMS`.
- [ ] El preview WebGL2 del nodo renderiza el efecto en tiempo real al cambiar parámetros.
- [ ] `CoolVideoGenerator` acepta la salida del nodo y renderiza video sin errores.
- [ ] Typecheck / lint passes
- [ ] **[UI stories only]** Visually verified in browser

### US-002: Nodo Zoom Out
**As a** usuario final de ComfyUI, **I want** un nodo Zoom Out que emita `EFFECT_PARAMS` y tenga preview en vivo **so that** pueda aplicar alejamiento progresivo en mis composiciones.

**Acceptance Criteria:**
- [ ] Existe un nodo registrado como `CoolZoomOutEffect` con nombre visible en UI.
- [ ] El nodo expone parámetros de zoom out editables y emite un único output `EFFECT_PARAMS`.
- [ ] El preview WebGL2 del nodo renderiza el efecto en tiempo real al cambiar parámetros.
- [ ] `CoolVideoGenerator` acepta la salida del nodo y renderiza video sin errores.
- [ ] Typecheck / lint passes
- [ ] **[UI stories only]** Visually verified in browser

### US-003: Nodo Dolly In
**As a** usuario final de ComfyUI, **I want** un nodo Dolly In que emita `EFFECT_PARAMS` y tenga preview en vivo **so that** pueda simular avance de cámara hacia la escena.

**Acceptance Criteria:**
- [ ] Existe un nodo registrado como `CoolDollyInEffect` con nombre visible en UI.
- [ ] El nodo expone parámetros de dolly in editables y emite un único output `EFFECT_PARAMS`.
- [ ] El preview WebGL2 del nodo renderiza el efecto en tiempo real al cambiar parámetros.
- [ ] `CoolVideoGenerator` acepta la salida del nodo y renderiza video sin errores.
- [ ] Typecheck / lint passes
- [ ] **[UI stories only]** Visually verified in browser

### US-004: Nodo Dolly Out
**As a** usuario final de ComfyUI, **I want** un nodo Dolly Out que emita `EFFECT_PARAMS` y tenga preview en vivo **so that** pueda simular retroceso de cámara desde la escena.

**Acceptance Criteria:**
- [ ] Existe un nodo registrado como `CoolDollyOutEffect` con nombre visible en UI.
- [ ] El nodo expone parámetros de dolly out editables y emite un único output `EFFECT_PARAMS`.
- [ ] El preview WebGL2 del nodo renderiza el efecto en tiempo real al cambiar parámetros.
- [ ] `CoolVideoGenerator` acepta la salida del nodo y renderiza video sin errores.
- [ ] Typecheck / lint passes
- [ ] **[UI stories only]** Visually verified in browser

### US-005: Compatibilidad end-to-end con Video Generator
**As a** usuario final de ComfyUI, **I want** encadenar los cuatro nuevos efectos en `CoolVideoGenerator` **so that** pueda producir un video final con movimientos de cámara combinados.

**Acceptance Criteria:**
- [ ] Los nuevos `EFFECT_PARAMS` son válidos en cualquiera de los slots `effect_params_N`.
- [ ] El pipeline renderiza sin excepciones cuando se combinan Zoom y Dolly en secuencia.
- [ ] El video generado mantiene formato de salida compatible con `CoolVideoPlayer`.
- [ ] Typecheck / lint passes

## Functional Requirements
- FR-1: Deben existir cuatro nuevos archivos de nodos Python (`zoom_in_effect.py`, `zoom_out_effect.py`, `dolly_in_effect.py`, `dolly_out_effect.py`) que sigan el patrón de nodos de efecto existente.
- FR-2: Deben existir cuatro extensiones frontend JS para preview en vivo, una por nodo, siguiendo el patrón de `web/*_effect.js`.
- FR-3: Deben añadirse shaders GLSL dedicados para zoom in, zoom out, dolly in y dolly out en `shaders/glsl/`.
- FR-4: Los cuatro nodos deben registrar sus clases y nombres en `NODE_CLASS_MAPPINGS` y `NODE_DISPLAY_NAME_MAPPINGS`.
- FR-5: Cada nodo debe construir salida `EFFECT_PARAMS` consistente con `build_effect_params()` y el contrato de uniforms (`u_image`, `u_time`, `u_resolution`).
- FR-6: `CoolVideoGenerator` debe aceptar y aplicar los nuevos effects sin rutas especiales ni flags adicionales.
- FR-7: El endpoint de shaders (`/cool_effects/shaders` y `/cool_effects/shaders/{name}`) debe exponer y servir correctamente los nuevos shaders.

## Non-Goals (Out of Scope)
- Crear un sistema nuevo de sincronización con audio para estos efectos.
- Rediseñar `CoolVideoGenerator` o cambiar su API pública.
- Introducir nuevas dependencias externas fuera del stack actual del proyecto.
- Agregar automatización de tests donde hoy el proyecto opera con validación manual.

## Open Questions
- None
