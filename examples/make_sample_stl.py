"""Generate small sample STL files (a cylinder and a cube) for demos and tests.

Run directly to drop ``cylinder.stl`` next to this script, or import
:func:`cylinder_triangles` / :func:`cube_triangles` / :func:`write_binary_stl`
to build meshes programmatically.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np


def cylinder_triangles(
    radius: float = 10.0,
    height: float = 5.0,
    segments: int = 48,
) -> np.ndarray:
    """Return the ``(N, 3, 3)`` triangles of a closed cylinder about the Z axis."""
    angles = np.linspace(0.0, 2.0 * np.pi, segments, endpoint=False)
    bottom = np.column_stack(
        [radius * np.cos(angles), radius * np.sin(angles), np.zeros(segments)]
    )
    top = bottom + np.array([0.0, 0.0, height])
    center_bottom = np.array([0.0, 0.0, 0.0])
    center_top = np.array([0.0, 0.0, height])

    tris: list[list[np.ndarray]] = []
    for i in range(segments):
        j = (i + 1) % segments
        # Side wall (two triangles per quad).
        tris.append([bottom[i], bottom[j], top[j]])
        tris.append([bottom[i], top[j], top[i]])
        # Bottom and top caps.
        tris.append([center_bottom, bottom[j], bottom[i]])
        tris.append([center_top, top[i], top[j]])
    return np.array(tris, dtype=np.float64)


def cube_triangles(size: float = 10.0) -> np.ndarray:
    """Return the ``(12, 3, 3)`` triangles of an axis-aligned cube at the origin."""
    s = size
    v = np.array(
        [
            [0, 0, 0], [s, 0, 0], [s, s, 0], [0, s, 0],
            [0, 0, s], [s, 0, s], [s, s, s], [0, s, s],
        ],
        dtype=np.float64,
    )
    faces = [
        (0, 1, 2), (0, 2, 3),  # bottom
        (4, 6, 5), (4, 7, 6),  # top
        (0, 5, 1), (0, 4, 5),  # front
        (1, 6, 2), (1, 5, 6),  # right
        (2, 7, 3), (2, 6, 7),  # back
        (3, 4, 0), (3, 7, 4),  # left
    ]
    return np.array([[v[a], v[b], v[c]] for a, b, c in faces], dtype=np.float64)


def write_binary_stl(path: str | Path, triangles: np.ndarray) -> None:
    """Write ``triangles`` as a binary STL file."""
    triangles = np.asarray(triangles, dtype=np.float32)
    with open(path, "wb") as fh:
        fh.write(b"\x00" * 80)  # header
        fh.write(struct.pack("<I", triangles.shape[0]))
        for tri in triangles:
            normal = _triangle_normal(tri)
            fh.write(struct.pack("<3f", *normal))
            for vertex in tri:
                fh.write(struct.pack("<3f", *vertex))
            fh.write(struct.pack("<H", 0))


def write_ascii_stl(path: str | Path, triangles: np.ndarray, name: str = "mesh") -> None:
    """Write ``triangles`` as an ASCII STL file."""
    lines = [f"solid {name}"]
    for tri in np.asarray(triangles, dtype=np.float64):
        nx, ny, nz = _triangle_normal(tri)
        lines.append(f"  facet normal {nx} {ny} {nz}")
        lines.append("    outer loop")
        for vertex in tri:
            lines.append(f"      vertex {vertex[0]} {vertex[1]} {vertex[2]}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    Path(path).write_text("\n".join(lines) + "\n")


def _triangle_normal(tri: np.ndarray) -> tuple[float, float, float]:
    n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
    norm = np.linalg.norm(n)
    if norm > 0:
        n = n / norm
    return float(n[0]), float(n[1]), float(n[2])


if __name__ == "__main__":
    out = Path(__file__).with_name("cylinder.stl")
    write_binary_stl(out, cylinder_triangles())
    print(f"Wrote {out}")
