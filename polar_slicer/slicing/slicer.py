"""Layer slicing algorithms.

:class:`LayerSlicer` is the abstraction; :class:`PlaneLayerSlicer` intersects
the mesh with horizontal planes and stitches the resulting segments into closed
contours.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from polar_slicer.config import SlicerConfig
from polar_slicer.mesh.model import Mesh
from polar_slicer.slicing.layer import Contour, Layer


class LayerSlicer(ABC):
    """Interface turning a mesh into an ordered list of layers (bottom-up)."""

    @abstractmethod
    def slice(self, mesh: Mesh, config: SlicerConfig) -> list[Layer]:
        """Slice ``mesh`` into layers according to ``config``."""


class PlaneLayerSlicer(LayerSlicer):
    """Slice a mesh with evenly spaced horizontal planes.

    Layers are centred inside each slab: the first plane sits half a layer
    height above the mesh floor, avoiding degenerate slices exactly on a face.
    """

    def __init__(self, weld_tolerance: float = 1e-4) -> None:
        # Endpoints closer than this are treated as the same vertex when
        # stitching segments into loops.
        self._tol = weld_tolerance

    def slice(self, mesh: Mesh, config: SlicerConfig) -> list[Layer]:
        if mesh.is_empty:
            return []

        layers: list[Layer] = []
        z = mesh.z_min + config.layer_height / 2.0
        while z < mesh.z_max:
            segments = self._intersect_plane(mesh.triangles, z)
            contours = self._stitch(segments)
            layers.append(Layer(z=z, contours=contours))
            z += config.layer_height
        return layers

    def _intersect_plane(self, triangles: np.ndarray, z: float) -> np.ndarray:
        """Return an ``(S, 2, 2)`` array of intersection segments at height ``z``."""
        # Signed distance of each vertex to the plane.
        dist = triangles[:, :, 2] - z  # (N, 3)
        above = dist > 0.0

        # A triangle contributes a segment iff its vertices are not all on the
        # same side (count of "above" is 1 or 2).
        n_above = above.sum(axis=1)
        crossing = (n_above == 1) | (n_above == 2)
        tris = triangles[crossing]
        d = dist[crossing]
        if tris.shape[0] == 0:
            return np.empty((0, 2, 2), dtype=np.float64)

        segments = np.empty((tris.shape[0], 2, 2), dtype=np.float64)
        # For each triangle, the plane crosses exactly the two edges whose
        # endpoints straddle the plane. Iterate the three edges and collect the
        # two crossings per triangle.
        edges = ((0, 1), (1, 2), (2, 0))
        found = np.zeros(tris.shape[0], dtype=np.int64)
        for a, b in edges:
            da = d[:, a]
            db = d[:, b]
            straddle = (da > 0.0) != (db > 0.0)
            if not np.any(straddle):
                continue
            t = da[straddle] / (da[straddle] - db[straddle])
            pa = tris[straddle][:, a, :2]
            pb = tris[straddle][:, b, :2]
            pts = pa + (pb - pa) * t[:, None]
            idx = np.nonzero(straddle)[0]
            for local, tri_i in enumerate(idx):
                segments[tri_i, found[tri_i]] = pts[local]
                found[tri_i] += 1
        return segments

    def _stitch(self, segments: np.ndarray) -> list[Contour]:
        """Join unordered segments into closed contours by endpoint matching."""
        if segments.shape[0] == 0:
            return []

        # Map a quantized point -> list of (segment_index, endpoint_index).
        buckets: dict[tuple[int, int], list[tuple[int, int]]] = {}

        def key(p: np.ndarray) -> tuple[int, int]:
            return (round(p[0] / self._tol), round(p[1] / self._tol))

        for i in range(segments.shape[0]):
            for j in (0, 1):
                buckets.setdefault(key(segments[i, j]), []).append((i, j))

        used = np.zeros(segments.shape[0], dtype=bool)
        contours: list[Contour] = []

        for start in range(segments.shape[0]):
            if used[start]:
                continue
            loop: list[np.ndarray] = []
            seg_i, end_j = start, 0
            while not used[seg_i]:
                used[seg_i] = True
                p_from = segments[seg_i, end_j]
                p_to = segments[seg_i, 1 - end_j]
                loop.append(p_from)
                # Find an unused segment sharing the arrival point.
                candidates = buckets.get(key(p_to), [])
                nxt = None
                for cand_i, cand_j in candidates:
                    if not used[cand_i]:
                        nxt = (cand_i, cand_j)
                        break
                if nxt is None:
                    loop.append(p_to)  # open contour; keep the trailing point
                    break
                seg_i, end_j = nxt
            if len(loop) >= 3:
                contours.append(Contour(np.array(loop, dtype=np.float64)))
        return contours
