"""Perimeter generation.

Perimeters are the contour lines that trace a layer's boundary. Working in the
polar domain, each perimeter is a ring at ``R_outer(theta) - k * width`` for
``k`` in ``range(perimeters)`` — concentric loops offset inward by one extrusion
width each.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from polar_slicer.config import SlicerConfig
from polar_slicer.geometry.points import PolarPoint
from polar_slicer.geometry.profile import RadialProfile
from polar_slicer.toolpath.path import PathRole, ToolPath


class PerimeterGenerator(ABC):
    """Interface generating the perimeter toolpaths of a single layer."""

    @abstractmethod
    def generate(
        self, profile: RadialProfile, config: SlicerConfig
    ) -> list[ToolPath]:
        """Return ``config.perimeters`` perimeter loops for ``profile``."""


class ConcentricPerimeterGenerator(PerimeterGenerator):
    """Concentric rings offset inward from the layer boundary by one width each."""

    def generate(
        self, profile: RadialProfile, config: SlicerConfig
    ) -> list[ToolPath]:
        if profile.is_empty() or config.perimeters == 0:
            return []

        width = config.extrusion_width
        paths: list[ToolPath] = []
        for k in range(config.perimeters):
            # Ring k sits half a width inside the previous edge so extrusions
            # sit flush against each other.
            offset = (k + 0.5) * width
            radii = profile.radii - offset
            loop = self._ring(profile, radii)
            if loop is not None:
                paths.append(loop)
        return paths

    @staticmethod
    def _ring(profile: RadialProfile, radii: np.ndarray) -> ToolPath | None:
        """Build a closed ring, dropping angles whose radius collapsed to <= 0."""
        mask = radii > 0.0
        if mask.sum() < 3:
            return None
        points = [
            PolarPoint(r=float(r), theta=float(t), z=profile.z)
            for t, r in zip(profile.thetas[mask], radii[mask])
        ]
        return ToolPath(role=PathRole.PERIMETER, points=points, closed=True)
