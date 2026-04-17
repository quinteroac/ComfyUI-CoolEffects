"""Utilities for parsing .cube LUT files and preparing texture payloads."""

from __future__ import annotations

from pathlib import Path


_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_DOMAIN_MIN = (0.0, 0.0, 0.0)
_DEFAULT_DOMAIN_MAX = (1.0, 1.0, 1.0)


def resolve_lut_path(lut_path: str | Path) -> Path:
    path_value = str(lut_path).strip()
    if not path_value:
        raise ValueError("lut_path must be a non-empty string")

    normalized_path = Path(path_value).expanduser()
    if normalized_path.suffix.lower() != ".cube":
        raise ValueError(f"Expected a .cube LUT file, got: {path_value}")

    candidates: list[Path]
    if normalized_path.is_absolute():
        candidates = [normalized_path]
    else:
        candidates = [
            (Path.cwd() / normalized_path).resolve(),
            (_PACKAGE_ROOT / normalized_path).resolve(),
        ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise ValueError(f"LUT file not found: {path_value}")


def _parse_triplet(tokens: list[str], directive_name: str, line_number: int) -> tuple[float, float, float]:
    if len(tokens) != 4:
        raise ValueError(
            f"{directive_name} must have exactly 3 values (line {line_number})"
        )
    try:
        return (float(tokens[1]), float(tokens[2]), float(tokens[3]))
    except ValueError as error:
        raise ValueError(
            f"Invalid float in {directive_name} declaration (line {line_number})"
        ) from error


def _parse_size(tokens: list[str], line_number: int) -> int:
    if len(tokens) != 2:
        raise ValueError(f"LUT_3D_SIZE must have exactly one value (line {line_number})")
    try:
        size = int(tokens[1])
    except ValueError as error:
        raise ValueError(f"Invalid LUT_3D_SIZE value (line {line_number})") from error
    if size < 2:
        raise ValueError(f"LUT_3D_SIZE must be >= 2 (line {line_number})")
    return size


def flatten_lut_to_strip(lut_values: list[tuple[float, float, float]], size: int) -> list[list[list[float]]]:
    expected_rows = size**3
    if len(lut_values) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} LUT rows for size {size}, got {len(lut_values)}"
        )

    strip: list[list[list[float]]] = [
        [[0.0, 0.0, 0.0] for _ in range(size * size)]
        for _ in range(size)
    ]
    index = 0
    for blue in range(size):
        for green in range(size):
            x_offset = green * size
            for red in range(size):
                row = lut_values[index]
                if len(row) != 3:
                    raise ValueError("Each LUT row must contain 3 channels")
                strip[blue][x_offset + red] = [float(row[0]), float(row[1]), float(row[2])]
                index += 1
    return strip


def create_identity_lut_strip(size: int) -> list[list[list[float]]]:
    if size < 2:
        raise ValueError("size must be >= 2")
    values: list[tuple[float, float, float]] = []
    scale = float(size - 1)
    for blue in range(size):
        for green in range(size):
            for red in range(size):
                values.append((red / scale, green / scale, blue / scale))
    return flatten_lut_to_strip(values, size)


def lut_strip_to_uint8(lut_strip: list[list[list[float]]]) -> list[list[list[int]]]:
    if not isinstance(lut_strip, list):
        raise ValueError("lut_strip must be a list")
    output: list[list[list[int]]] = []
    for row in lut_strip:
        if not isinstance(row, list):
            raise ValueError("Each LUT strip row must be a list")
        output_row: list[list[int]] = []
        for pixel in row:
            if not isinstance(pixel, list) or len(pixel) != 3:
                raise ValueError("Each LUT strip pixel must be [r, g, b]")
            output_row.append(
                [
                    max(0, min(255, int(round(float(pixel[0]) * 255.0)))),
                    max(0, min(255, int(round(float(pixel[1]) * 255.0)))),
                    max(0, min(255, int(round(float(pixel[2]) * 255.0)))),
                ]
            )
        output.append(output_row)
    return output


def parse_cube_lut_file(lut_path: str | Path) -> dict:
    resolved_path = resolve_lut_path(lut_path)

    lut_size: int | None = None
    domain_min = _DEFAULT_DOMAIN_MIN
    domain_max = _DEFAULT_DOMAIN_MAX
    lut_rows: list[tuple[float, float, float]] = []

    for line_number, raw_line in enumerate(
        resolved_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        tokens = line.split()
        directive = tokens[0].upper()

        if directive == "TITLE":
            continue
        if directive == "LUT_3D_SIZE":
            lut_size = _parse_size(tokens, line_number)
            continue
        if directive == "DOMAIN_MIN":
            domain_min = _parse_triplet(tokens, "DOMAIN_MIN", line_number)
            continue
        if directive == "DOMAIN_MAX":
            domain_max = _parse_triplet(tokens, "DOMAIN_MAX", line_number)
            continue

        if len(tokens) != 3:
            raise ValueError(
                f"Invalid LUT row at line {line_number}; expected 3 numeric values"
            )

        try:
            lut_rows.append((float(tokens[0]), float(tokens[1]), float(tokens[2])))
        except ValueError as error:
            raise ValueError(
                f"Invalid LUT row at line {line_number}; expected numeric values"
            ) from error

    if lut_size is None:
        raise ValueError("LUT_3D_SIZE declaration is required in .cube files")

    lut_strip = flatten_lut_to_strip(lut_rows, lut_size)

    return {
        "resolved_path": str(resolved_path),
        "size": lut_size,
        "domain_min": domain_min,
        "domain_max": domain_max,
        "values": lut_rows,
        "strip": lut_strip,
    }
