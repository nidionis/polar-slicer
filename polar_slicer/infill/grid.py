"""Grid ("Grille") infill: spaced concentric rings crossed by radial spokes.

Density is driven by ``infill_percentage``: both the spacing between rings and
the number of radial spokes scale with it. At 100 % the ring spacing collapses
to a single extrusion width (as dense as solid infill); at low percentages the
rings spread apart and fewer spokes are drawn.
"""

from __future__ import annotations

import numpy as np

from polar_slicer.config import SlicerConfig
from polar_slicer.geometry.points import PolarPoint
from polar_slicer.geometry.profile import RadialProfile
from polar_slicer.infill.strategy import InfillStrategy
from polar_slicer.toolpath.path import PathRole, ToolPath


class GridInfill(InfillStrategy):
    """Concentric rings spaced by the infill density, plus radial spokes."""

    def generate(
        self, profile: RadialProfile, config: SlicerConfig
    ) -> list[ToolPath]:
        if profile.is_empty() or config.infill_percentage <= 0.0:
            return []

        interior = self.interior_radii(profile, config)
        boundary = float(interior.max())
        if boundary <= 0.0:
            return []

        density = config.infill_percentage / 100.0
        paths: list[ToolPath] = []
        paths.extend(self._rings(profile, interior, boundary, config, density))
        paths.extend(self._spokes(profile, interior, config, density))
        return paths

    @staticmethod
    def _rings(
        profile: RadialProfile,
        interior: np.ndarray,
        boundary: float,
        config: SlicerConfig,
        density: float,
    ) -> list[ToolPath]:
        # Wider spacing for sparser infill; one extrusion width at 100 %.
        step = config.extrusion_width / density
        paths: list[ToolPath] = []
        radius = boundary
        while radius > 0.0:
            mask = interior >= radius
            if mask.sum() >= 3:
                points = [
                    PolarPoint(r=radius, theta=float(t), z=profile.z)
                    for t in profile.thetas[mask]
                ]
                paths.append(
                    ToolPath(role=PathRole.INFILL, points=points, closed=True)
                )
            radius -= step
        return paths

    @staticmethod
    def _spokes(
        profile: RadialProfile,
        interior: np.ndarray,
        config: SlicerConfig,
        density: float,
    ) -> list[ToolPath]:
        # Spoke count scales with density; reuse profile angles so each spoke's
        # outer radius is known exactly. Index against the profile's actual
        # sample count, which need not equal config.angular_steps.
        samples = int(profile.radii.size)
        count = max(2, int(round(samples * density)))
        indices = np.unique(
            np.linspace(0, samples, count, endpoint=False).astype(int)
        )
        paths: list[ToolPath] = []
        for idx in indices:
            outer = float(interior[idx])
            if outer <= 0.0:
                continue
            theta = float(profile.thetas[idx])
            points = [
                PolarPoint(r=0.0, theta=theta, z=profile.z),
                PolarPoint(r=outer, theta=theta, z=profile.z),
            ]
            paths.append(ToolPath(role=PathRole.INFILL, points=points, closed=False))
        return paths
