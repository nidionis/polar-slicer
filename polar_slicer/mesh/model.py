"""Triangle-soup mesh model.

The mesh is stored as a plain ``(N, 3, 3)`` array of triangle vertices. This is
deliberately format-agnostic: whatever loader produced it, the rest of the
pipeline only ever sees this structure.
"""

from __future__ import annotations

import numpy as np


class Mesh:
    """An immutable collection of triangles.

    Parameters
    ----------
    triangles:
        Array of shape ``(N, 3, 3)``: ``N`` triangles, each with 3 vertices,
        each vertex an ``(x, y, z)`` triple.
    """

    def __init__(self, triangles: np.ndarray) -> None:
        triangles = np.asarray(triangles, dtype=np.float64)
        if triangles.ndim != 3 or triangles.shape[1:] != (3, 3):
            raise ValueError(
                f"triangles must have shape (N, 3, 3), got {triangles.shape}"
            )
        # Copy + lock so the mesh is effectively immutable to consumers.
        self._triangles = triangles.copy()
        self._triangles.flags.writeable = False

    @property
    def triangles(self) -> np.ndarray:
        """The ``(N, 3, 3)`` read-only vertex array."""
        return self._triangles

    def __len__(self) -> int:
        return int(self._triangles.shape[0])

    @property
    def is_empty(self) -> bool:
        return len(self) == 0

    @property
    def min_bound(self) -> np.ndarray:
        """Per-axis minimum ``(x, y, z)`` of all vertices."""
        return self._triangles.reshape(-1, 3).min(axis=0)

    @property
    def max_bound(self) -> np.ndarray:
        """Per-axis maximum ``(x, y, z)`` of all vertices."""
        return self._triangles.reshape(-1, 3).max(axis=0)

    @property
    def z_min(self) -> float:
        return float(self.min_bound[2])

    @property
    def z_max(self) -> float:
        return float(self.max_bound[2])

    @property
    def xy_centroid(self) -> tuple[float, float]:
        """Centroid of the mesh in the XY plane (the natural rotation axis)."""
        verts = self._triangles.reshape(-1, 3)
        return (float(verts[:, 0].mean()), float(verts[:, 1].mean()))
