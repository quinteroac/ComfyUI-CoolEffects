from pathlib import Path


SHADERS_DIR = Path(__file__).parent / "glsl"


def load_shader(name: str) -> str:
    shader_path = SHADERS_DIR / f"{name}.frag"
    return shader_path.read_text(encoding="utf-8")


def list_shaders() -> list[str]:
    shader_names = [shader_path.stem for shader_path in SHADERS_DIR.glob("*.frag")]
    return sorted(shader_names)
