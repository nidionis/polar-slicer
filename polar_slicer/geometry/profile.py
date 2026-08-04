"""Radial profiles: the polar description of a layer's cross-section.

Perimeter and infill generation for a rotative printer are naturally expressed
in polar coordinates about the part's central axis. A :class:`RadialProfile`
captures, for a fixed set of angles, the outer radius of the layer at that
angle. :class:`RaycastProfileBuilder` builds one from a Cartesian
:class:`~polar_slicer.slicing.layer.Layer` by casting a ray per angle and taking
the farthest contour crossing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from polar_slicer.config import SlicerConfig
from polar_slicer.geometry.converter import CoordinateConverter
from polar_slicer.slicing.layer import Layer


@dataclass(frozen=True)
class RadialProfile:
    """Outer radius of a layer sampled at evenly spaced angles.

    Attributes
    ----------
    z:
        Height of the layer.
    thetas:
        ``(K,)`` array of angles in radians, evenly spaced over ``[-pi, pi)``.
    radii:
        ``(K,)`` array of outer radii, aligned with ``thetas``. A radius of
        ``0`` means the ray did not hit the cross-section at that angle.
    center:
        The ``(cx, cy)`` axis the radii are measured from.
    """

    z: float
    thetas: np.ndarray
    radii: np.ndarray
    center: tuple[float, float]

    @property
    def max_radius(self) -> float:
        return float(self.radii.max()) if self.radii.size else 0.0

    def is_empty(self) -> bool:
        return self.radii.size == 0 or self.max_radius <= 0.0


class RadialProfileBuilder(ABC):
    """Interface converting a Cartesian layer into a polar radial profile."""

    @abstractmethod
    def build(
        self,
        layer: Layer,
        converter: CoordinateConverter,
        config: SlicerConfig,
    ) -> RadialProfile:
        """Build the radial profile of ``layer`` about ``converter``'s axis."""


class RaycastProfileBuilder(RadialProfileBuilder):
    """Build a radial profile by ray-casting from the central axis outward."""

    def build(
        self,
        layer: Layer,
        converter: CoordinateConverter,
        config: SlicerConfig,
    ) -> RadialProfile:
        cx, cy = self._center(converter)
        thetas = np.linspace(-np.pi, np.pi, config.angular_steps, endpoint=False)
        radii = np.zeros_like(thetas)

        # Collect every contour edge as origin/direction pairs, shifted so the
        # central axis is the origin.
        edges = self._edges(layer, cx, cy)
        if edges.size == 0:
            return RadialProfile(layer.z, thetas, radii, (cx, cy))

        p1 = edges[:, 0, :]  # (E, 2)
        p2 = edges[:, 1, :]
        seg = p2 - p1  # (E, 2)

        for i, theta in enumerate(thetas):
            d = np.array([np.cos(theta), np.sin(theta)])
            radii[i] = self._farthest_hit(p1, seg, d)

        return RadialProfile(layer.z, thetas, radii, (cx, cy))

    @staticmethod
    def _center(converter: CoordinateConverter) -> tuple[float, float]:
        # PolarConverter exposes its center; fall back to origin otherwise.
        return getattr(converter, "center", (0.0, 0.0))

    @staticmethod
    def _edges(layer: Layer, cx: float, cy: float) -> np.ndarray:
        """Return all contour edges as ``(E, 2, 2)`` relative to the axis."""
        chunks = []
        for contour in layer.contours:
            pts = contour.points - np.array([cx, cy])
            nxt = np.roll(pts, -1, axis=0)
            chunks.append(np.stack([pts, nxt], axis=1))
        if not chunks:
            return np.empty((0, 2, 2), dtype=np.float64)
        return np.concatenate(chunks, axis=0)

    @staticmethod
    def _farthest_hit(p1: np.ndarray, seg: np.ndarray, d: np.ndarray) -> float:
        """Largest ``r >= 0`` where ray ``r*d`` meets any segment ``p1+s*seg``.

        Solving ``r*d = p1 + s*seg`` for each edge via a 2x2 system. Edges are
        parallel to the ray (zero determinant) or hit outside ``s in [0, 1]`` or
        behind the origin (``r < 0``) are ignored.
        """
        # Determinant of [d, -seg] per edge.
        det = -d[0] * seg[:, 1] + d[1] * seg[:, 0]
        nonzero = np.abs(det) > 1e-12
        if not np.any(nonzero):
            return 0.0

        det = det[nonzero]
        p = p1[nonzero]
        s = seg[nonzero]

        # Solve  r*d - u*seg = p  for each edge via Cramer's rule.
        r = (s[:, 0] * p[:, 1] - s[:, 1] * p[:, 0]) / det
        u = (d[0] * p[:, 1] - d[1] * p[:, 0]) / det

        valid = (r >= 0.0) & (u >= 0.0) & (u <= 1.0)
        if not np.any(valid):
            return 0.0
        return float(r[valid].max())
