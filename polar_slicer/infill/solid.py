"""Solid ("Plein") infill: touching concentric rings filling the interior."""

from __future__ import annotations

import numpy as np

from polar_slicer.config import SlicerConfig
from polar_slicer.geometry.points import PolarPoint
from polar_slicer.geometry.profile import RadialProfile
from polar_slicer.infill.strategy import InfillStrategy
from polar_slicer.toolpath.path import PathRole, ToolPath


class SolidInfill(InfillStrategy):
    """Fill the interior with concentric rings spaced by one extrusion width.

    Rings start at the infill boundary and step inward by ``extrusion_width``
    (so adjacent rings just touch — "jointives") down to the central axis.
    """

    def generate(
        self, profile: RadialProfile, config: SlicerConfig
    ) -> list[ToolPath]:
        if profile.is_empty():
            return []

        interior = self.interior_radii(profile, config)
        boundary = float(interior.max())
        if boundary <= 0.0:
            return []

        step = config.extrusion_width
        paths: list[ToolPath] = []
        radius = boundary
        while radius > 0.0:
            ring = self._ring(profile, interior, radius)
            if ring is not None:
                paths.append(ring)
            radius -= step
        return paths

    @staticmethod
    def _ring(
        profile: RadialProfile, interior: np.ndarray, radius: float
    ) -> ToolPath | None:
        """A ring clamped to the interior boundary at each angle."""
        # Only keep angles where the interior still reaches this radius.
        mask = interior >= radius
        if mask.sum() < 3:
            return None
        points = [
            PolarPoint(r=radius, theta=float(t), z=profile.z)
            for t in profile.thetas[mask]
        ]
        return ToolPath(role=PathRole.INFILL, points=points, closed=True)
