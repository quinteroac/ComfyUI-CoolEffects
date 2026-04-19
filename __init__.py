"""ComfyUI-CoolEffects package entrypoint."""

import importlib.util
import json
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent
WEB_DIRECTORY = "web"


def _load_module_from_path(module_name: str, module_path: Path):
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


_shader_loader_module = _load_module_from_path(
    "cool_effects_shader_loader_runtime", PACKAGE_ROOT / "shaders" / "loader.py"
)
list_shaders = _shader_loader_module.list_shaders

_lut_utils_module = _load_module_from_path(
    "cool_effects_lut_utils_runtime", PACKAGE_ROOT / "nodes" / "lut_utils.py"
)
parse_cube_lut_file = _lut_utils_module.parse_cube_lut_file
lut_strip_to_uint8 = _lut_utils_module.lut_strip_to_uint8

_effect_selector_module = _load_module_from_path(
    "cool_effects_effect_selector_runtime",
    PACKAGE_ROOT / "nodes" / "effect_selector.py",
)
CoolEffectSelector = _effect_selector_module.CoolEffectSelector

_glitch_effect_module = _load_module_from_path(
    "cool_effects_glitch_effect_runtime",
    PACKAGE_ROOT / "nodes" / "glitch_effect.py",
)
CoolGlitchEffect = _glitch_effect_module.CoolGlitchEffect

_vhs_effect_module = _load_module_from_path(
    "cool_effects_vhs_effect_runtime",
    PACKAGE_ROOT / "nodes" / "vhs_effect.py",
)
CoolVHSEffect = _vhs_effect_module.CoolVHSEffect

_zoom_pulse_effect_module = _load_module_from_path(
    "cool_effects_zoom_pulse_effect_runtime",
    PACKAGE_ROOT / "nodes" / "zoom_pulse_effect.py",
)
CoolZoomPulseEffect = _zoom_pulse_effect_module.CoolZoomPulseEffect

_zoom_in_effect_module = _load_module_from_path(
    "cool_effects_zoom_in_effect_runtime",
    PACKAGE_ROOT / "nodes" / "zoom_in_effect.py",
)
CoolZoomInEffect = _zoom_in_effect_module.CoolZoomInEffect

_zoom_out_effect_module = _load_module_from_path(
    "cool_effects_zoom_out_effect_runtime",
    PACKAGE_ROOT / "nodes" / "zoom_out_effect.py",
)
CoolZoomOutEffect = _zoom_out_effect_module.CoolZoomOutEffect

_dolly_in_effect_module = _load_module_from_path(
    "cool_effects_dolly_in_effect_runtime",
    PACKAGE_ROOT / "nodes" / "dolly_in_effect.py",
)
CoolDollyInEffect = _dolly_in_effect_module.CoolDollyInEffect

_dolly_out_effect_module = _load_module_from_path(
    "cool_effects_dolly_out_effect_runtime",
    PACKAGE_ROOT / "nodes" / "dolly_out_effect.py",
)
CoolDollyOutEffect = _dolly_out_effect_module.CoolDollyOutEffect

_bass_zoom_effect_module = _load_module_from_path(
    "cool_effects_bass_zoom_effect_runtime",
    PACKAGE_ROOT / "nodes" / "bass_zoom_effect.py",
)
CoolBassZoomEffect = _bass_zoom_effect_module.CoolBassZoomEffect

_beat_pulse_effect_module = _load_module_from_path(
    "cool_effects_beat_pulse_effect_runtime",
    PACKAGE_ROOT / "nodes" / "beat_pulse_effect.py",
)
CoolBeatPulseEffect = _beat_pulse_effect_module.CoolBeatPulseEffect

_freq_warp_effect_module = _load_module_from_path(
    "cool_effects_freq_warp_effect_runtime",
    PACKAGE_ROOT / "nodes" / "freq_warp_effect.py",
)
CoolFreqWarpEffect = _freq_warp_effect_module.CoolFreqWarpEffect

_water_drops_effect_module = _load_module_from_path(
    "cool_effects_water_drops_effect_runtime",
    PACKAGE_ROOT / "nodes" / "water_drops_effect.py",
)
CoolWaterDropsEffect = _water_drops_effect_module.CoolWaterDropsEffect

_frosted_glass_effect_module = _load_module_from_path(
    "cool_effects_frosted_glass_effect_runtime",
    PACKAGE_ROOT / "nodes" / "frosted_glass_effect.py",
)
CoolFrostedGlassEffect = _frosted_glass_effect_module.CoolFrostedGlassEffect

_fisheye_effect_module = _load_module_from_path(
    "cool_effects_fisheye_effect_runtime",
    PACKAGE_ROOT / "nodes" / "fisheye_effect.py",
)
CoolFisheyeEffect = _fisheye_effect_module.CoolFisheyeEffect

_vignette_effect_module = _load_module_from_path(
    "cool_effects_vignette_effect_runtime",
    PACKAGE_ROOT / "nodes" / "vignette_effect.py",
)
CoolVignetteEffect = _vignette_effect_module.CoolVignetteEffect

_pixelate_effect_module = _load_module_from_path(
    "cool_effects_pixelate_effect_runtime",
    PACKAGE_ROOT / "nodes" / "pixelate_effect.py",
)
CoolPixelateEffect = _pixelate_effect_module.CoolPixelateEffect

_crt_pixel_grid_effect_module = _load_module_from_path(
    "cool_effects_crt_pixel_grid_effect_runtime",
    PACKAGE_ROOT / "nodes" / "crt_pixel_grid_effect.py",
)
CoolCrtPixelGridEffect = _crt_pixel_grid_effect_module.CoolCrtPixelGridEffect

_dithering_effect_module = _load_module_from_path(
    "cool_effects_dithering_effect_runtime",
    PACKAGE_ROOT / "nodes" / "dithering_effect.py",
)
CoolDitheringEffect = _dithering_effect_module.CoolDitheringEffect

_tilt_shift_effect_module = _load_module_from_path(
    "cool_effects_tilt_shift_effect_runtime",
    PACKAGE_ROOT / "nodes" / "tilt_shift_effect.py",
)
CoolTiltShiftEffect = _tilt_shift_effect_module.CoolTiltShiftEffect

_pincushion_effect_module = _load_module_from_path(
    "cool_effects_pincushion_effect_runtime",
    PACKAGE_ROOT / "nodes" / "pincushion_effect.py",
)
CoolPincushionEffect = _pincushion_effect_module.CoolPincushionEffect

_chromatic_aberration_effect_module = _load_module_from_path(
    "cool_effects_chromatic_aberration_effect_runtime",
    PACKAGE_ROOT / "nodes" / "chromatic_aberration_effect.py",
)
CoolChromaticAberrationEffect = _chromatic_aberration_effect_module.CoolChromaticAberrationEffect

_brightness_contrast_effect_module = _load_module_from_path(
    "cool_effects_brightness_contrast_effect_runtime",
    PACKAGE_ROOT / "nodes" / "brightness_contrast_effect.py",
)
CoolBrightnessContrastEffect = _brightness_contrast_effect_module.CoolBrightnessContrastEffect

_hsl_effect_module = _load_module_from_path(
    "cool_effects_hsl_effect_runtime",
    PACKAGE_ROOT / "nodes" / "hsl_effect.py",
)
CoolHSLEffect = _hsl_effect_module.CoolHSLEffect

_color_temperature_effect_module = _load_module_from_path(
    "cool_effects_color_temperature_effect_runtime",
    PACKAGE_ROOT / "nodes" / "color_temperature_effect.py",
)
CoolColorTemperatureEffect = _color_temperature_effect_module.CoolColorTemperatureEffect

_color_balance_effect_module = _load_module_from_path(
    "cool_effects_color_balance_effect_runtime",
    PACKAGE_ROOT / "nodes" / "color_balance_effect.py",
)
CoolColorBalanceEffect = _color_balance_effect_module.CoolColorBalanceEffect

_color_quantization_effect_module = _load_module_from_path(
    "cool_effects_color_quantization_effect_runtime",
    PACKAGE_ROOT / "nodes" / "color_quantization_effect.py",
)
CoolColorQuantizationEffect = _color_quantization_effect_module.CoolColorQuantizationEffect

_curves_effect_module = _load_module_from_path(
    "cool_effects_curves_effect_runtime",
    PACKAGE_ROOT / "nodes" / "curves_effect.py",
)
CoolCurvesEffect = _curves_effect_module.CoolCurvesEffect

_lut_effect_module = _load_module_from_path(
    "cool_effects_lut_effect_runtime",
    PACKAGE_ROOT / "nodes" / "lut_effect.py",
)
CoolLUTEffect = _lut_effect_module.CoolLUTEffect

_tone_mapping_effect_module = _load_module_from_path(
    "cool_effects_tone_mapping_effect_runtime",
    PACKAGE_ROOT / "nodes" / "tone_mapping_effect.py",
)
CoolToneMappingEffect = _tone_mapping_effect_module.CoolToneMappingEffect

_waveform_effect_module = _load_module_from_path(
    "cool_effects_waveform_effect_runtime",
    PACKAGE_ROOT / "nodes" / "waveform_effect.py",
)
CoolWaveformEffect = _waveform_effect_module.CoolWaveformEffect

_text_overlay_effect_module = _load_module_from_path(
    "cool_effects_text_overlay_effect_runtime",
    PACKAGE_ROOT / "nodes" / "text_overlay_effect.py",
)
CoolTextOverlayEffect = _text_overlay_effect_module.CoolTextOverlayEffect

_pan_left_effect_module = _load_module_from_path(
    "cool_effects_pan_left_effect_runtime",
    PACKAGE_ROOT / "nodes" / "pan_left_effect.py",
)
CoolPanLeftEffect = _pan_left_effect_module.CoolPanLeftEffect

_pan_right_effect_module = _load_module_from_path(
    "cool_effects_pan_right_effect_runtime",
    PACKAGE_ROOT / "nodes" / "pan_right_effect.py",
)
CoolPanRightEffect = _pan_right_effect_module.CoolPanRightEffect

_pan_up_effect_module = _load_module_from_path(
    "cool_effects_pan_up_effect_runtime",
    PACKAGE_ROOT / "nodes" / "pan_up_effect.py",
)
CoolPanUpEffect = _pan_up_effect_module.CoolPanUpEffect

_pan_down_effect_module = _load_module_from_path(
    "cool_effects_pan_down_effect_runtime",
    PACKAGE_ROOT / "nodes" / "pan_down_effect.py",
)
CoolPanDownEffect = _pan_down_effect_module.CoolPanDownEffect

_pan_diagonal_effect_module = _load_module_from_path(
    "cool_effects_pan_diagonal_effect_runtime",
    PACKAGE_ROOT / "nodes" / "pan_diagonal_effect.py",
)
CoolPanDiagonalEffect = _pan_diagonal_effect_module.CoolPanDiagonalEffect

_audio_mixer_module = _load_module_from_path(
    "cool_effects_audio_mixer_runtime",
    PACKAGE_ROOT / "nodes" / "audio_mixer.py",
)
CoolAudioMixer = _audio_mixer_module.CoolAudioMixer

_video_mixer_module = _load_module_from_path(
    "cool_effects_video_mixer_runtime",
    PACKAGE_ROOT / "nodes" / "video_mixer.py",
)
CoolVideoMixer = _video_mixer_module.CoolVideoMixer

_video_player_module = _load_module_from_path(
    "cool_effects_video_player_runtime",
    PACKAGE_ROOT / "nodes" / "video_player.py",
)
CoolVideoPlayer = _video_player_module.CoolVideoPlayer

_video_generator_import_error = None
try:
    _video_generator_module = _load_module_from_path(
        "cool_effects_video_generator_runtime",
        PACKAGE_ROOT / "nodes" / "video_generator.py",
    )
except ModuleNotFoundError as error:
    _video_generator_module = None
    _video_generator_import_error = error
    CoolVideoGenerator = None
else:
    CoolVideoGenerator = _video_generator_module.CoolVideoGenerator

NODE_CLASS_MAPPINGS = {
    "CoolEffectSelector": CoolEffectSelector,
    "CoolGlitchEffect": CoolGlitchEffect,
    "CoolVHSEffect": CoolVHSEffect,
    "CoolZoomPulseEffect": CoolZoomPulseEffect,
    "CoolZoomInEffect": CoolZoomInEffect,
    "CoolZoomOutEffect": CoolZoomOutEffect,
    "CoolDollyInEffect": CoolDollyInEffect,
    "CoolDollyOutEffect": CoolDollyOutEffect,
    "CoolBassZoomEffect": CoolBassZoomEffect,
    "CoolBeatPulseEffect": CoolBeatPulseEffect,
    "CoolFreqWarpEffect": CoolFreqWarpEffect,
    "CoolWaterDropsEffect": CoolWaterDropsEffect,
    "CoolFrostedGlassEffect": CoolFrostedGlassEffect,
    "CoolFisheyeEffect": CoolFisheyeEffect,
    "CoolVignetteEffect": CoolVignetteEffect,
    "CoolPixelateEffect": CoolPixelateEffect,
    "CoolCrtPixelGridEffect": CoolCrtPixelGridEffect,
    "CoolDitheringEffect": CoolDitheringEffect,
    "CoolTiltShiftEffect": CoolTiltShiftEffect,
    "CoolPincushionEffect": CoolPincushionEffect,
    "CoolChromaticAberrationEffect": CoolChromaticAberrationEffect,
    "CoolBrightnessContrastEffect": CoolBrightnessContrastEffect,
    "CoolHSLEffect": CoolHSLEffect,
    "CoolColorTemperatureEffect": CoolColorTemperatureEffect,
    "CoolColorBalanceEffect": CoolColorBalanceEffect,
    "CoolColorQuantizationEffect": CoolColorQuantizationEffect,
    "CoolCurvesEffect": CoolCurvesEffect,
    "CoolLUTEffect": CoolLUTEffect,
    "CoolToneMappingEffect": CoolToneMappingEffect,
    "CoolWaveformEffect": CoolWaveformEffect,
    "CoolTextOverlayEffect": CoolTextOverlayEffect,
    "CoolPanLeftEffect": CoolPanLeftEffect,
    "CoolPanRightEffect": CoolPanRightEffect,
    "CoolPanUpEffect": CoolPanUpEffect,
    "CoolPanDownEffect": CoolPanDownEffect,
    "CoolPanDiagonalEffect": CoolPanDiagonalEffect,
    "CoolAudioMixer": CoolAudioMixer,
    "CoolVideoMixer": CoolVideoMixer,
    "CoolVideoPlayer": CoolVideoPlayer,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "CoolEffectSelector": "Cool Effect Selector",
    "CoolGlitchEffect": "Cool Glitch Effect",
    "CoolVHSEffect": "Cool VHS Effect",
    "CoolZoomPulseEffect": "Cool Zoom Pulse Effect",
    "CoolZoomInEffect": "Cool Zoom In Effect",
    "CoolZoomOutEffect": "Cool Zoom Out Effect",
    "CoolDollyInEffect": "Cool Dolly In Effect",
    "CoolDollyOutEffect": "Cool Dolly Out Effect",
    "CoolBassZoomEffect": "Cool Bass Zoom Effect",
    "CoolBeatPulseEffect": "Cool Beat Pulse Effect",
    "CoolFreqWarpEffect": "Cool Freq Warp Effect",
    "CoolWaterDropsEffect": "Cool Water Drops Effect",
    "CoolFrostedGlassEffect": "Cool Frosted Glass Effect",
    "CoolFisheyeEffect": "Cool Fisheye Effect",
    "CoolVignetteEffect": "Cool Vignette Effect",
    "CoolPixelateEffect": "Cool Pixelate Effect",
    "CoolCrtPixelGridEffect": "Cool CRT Pixel Grid Effect",
    "CoolDitheringEffect": "Cool Dithering Effect",
    "CoolTiltShiftEffect": "Cool Tilt-Shift Effect",
    "CoolPincushionEffect": "Cool Pincushion Effect",
    "CoolChromaticAberrationEffect": "Cool Chromatic Aberration Effect",
    "CoolBrightnessContrastEffect": "Cool Brightness / Contrast Effect",
    "CoolHSLEffect": "Cool HSL Effect",
    "CoolColorTemperatureEffect": "Cool Color Temperature Effect",
    "CoolColorBalanceEffect": "Cool Color Balance Effect",
    "CoolColorQuantizationEffect": "Cool Color Quantization Effect",
    "CoolCurvesEffect": "Cool Curves (Lift / Gamma / Gain) Effect",
    "CoolLUTEffect": "Cool LUT Effect",
    "CoolToneMappingEffect": "Cool Tone Mapping Effect",
    "CoolWaveformEffect": "Cool Waveform Effect",
    "CoolTextOverlayEffect": "Cool Text Overlay Effect",
    "CoolPanLeftEffect": "Cool Pan Left Effect",
    "CoolPanRightEffect": "Cool Pan Right Effect",
    "CoolPanUpEffect": "Cool Pan Up Effect",
    "CoolPanDownEffect": "Cool Pan Down Effect",
    "CoolPanDiagonalEffect": "Cool Pan Diagonal Effect",
    "CoolAudioMixer": "Cool Audio Mixer",
    "CoolVideoMixer": "Cool Video Mixer",
    "CoolVideoPlayer": "Cool Video Player",
}

if CoolVideoGenerator is not None:
    NODE_CLASS_MAPPINGS["CoolVideoGenerator"] = CoolVideoGenerator
    NODE_DISPLAY_NAME_MAPPINGS["CoolVideoGenerator"] = "Cool Video Generator"


class _JsonResponseFallback:
    def __init__(self, payload, status=200):
        self.status = status
        self.content_type = "application/json"
        self.text = json.dumps(payload)


_SHADERS_DIR = PACKAGE_ROOT / "shaders" / "glsl"


async def get_shaders(_request):
    payload = {"shaders": list_shaders()}

    try:
        from aiohttp import web
    except ImportError:
        return _JsonResponseFallback(payload)

    return web.json_response(payload)


async def get_shader(request):
    name = request.match_info.get("name", "")
    shader_path = _SHADERS_DIR / f"{name}.frag"

    try:
        from aiohttp import web
    except ImportError:

        class _TextResponse:
            def __init__(self, text, status=200):
                self.status = status
                self.content_type = "text/plain"
                self.text = text

        if not shader_path.exists():
            return _TextResponse(f"Shader not found: {name}", status=404)
        return _TextResponse(shader_path.read_text(encoding="utf-8"))

    if not shader_path.exists():
        raise web.HTTPNotFound(reason=f"Shader not found: {name}")
    return web.Response(text=shader_path.read_text(encoding="utf-8"), content_type="text/plain")


async def get_lut(request):
    lut_path = request.query.get("path", "")
    try:
        parsed_lut = parse_cube_lut_file(lut_path)
    except ValueError as error:
        try:
            from aiohttp import web
        except ImportError:
            return _JsonResponseFallback({"error": str(error)}, status=400)
        raise web.HTTPBadRequest(reason=str(error)) from error

    strip_uint8 = lut_strip_to_uint8(parsed_lut["strip"])
    strip_height = len(strip_uint8)
    strip_width = len(strip_uint8[0]) if strip_height > 0 else 0
    strip_flat = [channel for row in strip_uint8 for pixel in row for channel in pixel]
    payload = {
        "path": parsed_lut["resolved_path"],
        "size": parsed_lut["size"],
        "domain_min": list(parsed_lut["domain_min"]),
        "domain_max": list(parsed_lut["domain_max"]),
        "strip_width": strip_width,
        "strip_height": strip_height,
        "strip": strip_flat,
    }

    try:
        from aiohttp import web
    except ImportError:
        return _JsonResponseFallback(payload)
    return web.json_response(payload)


def _register_routes() -> None:
    try:
        from server import PromptServer
    except ImportError:
        return

    prompt_server = getattr(PromptServer, "instance", None)
    if prompt_server is None:
        return

    routes = getattr(prompt_server, "routes", None)
    if routes is None:
        return

    is_registered = getattr(routes, "_cool_effects_shader_list_registered", False)
    if is_registered:
        return

    routes.get("/cool_effects/shaders")(get_shaders)
    routes.get("/cool_effects/shaders/{name}")(get_shader)
    routes.get("/cool_effects/lut")(get_lut)
    setattr(routes, "_cool_effects_shader_list_registered", True)


_register_routes()
