"""Grid ("Grille") infill: spaced concentric rings crossed by radial spokes.

Density is driven by ``infill_percentage``: the spacing between rings and the
number of radial spokes both scale with it. At 100 % the ring spacing collapses
to a single extrusion width (as dense as solid infill); at low percentages the
rings spread apart and fewer spokes are drawn.

**Central butée.** Radial spokes cannot all run to the axis: two spokes
separated by an angle ``Δθ`` have a chord spacing ``E(R) = 2·R·sin(Δθ/2)`` at
radius ``R``, so keeping the deposited lines from overlapping (``E ≥ d`` for a
line width ``d``) forces every spoke to stop at a butée radius

    R_stop = d / (2·sin(Δθ/2)).

Below that radius the spoke would collide with its neighbours, over-extrude and
crash the nozzle at the centre. To keep the line density roughly constant across
the whole disc, spokes are built in **dyadic generations**: a coarse set of
rays reaches near the centre, and each finer generation doubles the ray count by
inserting bisectors (halving ``Δθ``), stopping progressively farther out per the
suite ``R_n = d / (2·sin(θ₀/2ⁿ))``. The line width ``d`` is ``extrusion_width``.
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

    # Coarsest generation: the principal axes (0, pi/2, pi, 3pi/2). Every finer
    # generation doubles this by inserting the bisectors.
    _BASE_SPOKES = 4

    @classmethod
    def _spokes(
        cls,
        profile: RadialProfile,
        interior: np.ndarray,
        config: SlicerConfig,
        density: float,
    ) -> list[ToolPath]:
        d = config.extrusion_width
        boundary = float(interior.max())
        floor = d / 2.0  # absolute innermost stop (matches R0 = d/2)

        # Target tangential spacing between spokes at the boundary follows the
        # same density law as the rings; ``target`` is how many rays fit there.
        step = d / density
        target = 2.0 * np.pi * boundary / step

        thetas = profile.thetas
        paths: list[ToolPath] = []
        emitted: set[float] = set()  # dedup rays shared across generations
        n = cls._BASE_SPOKES
        while True:
            # Butée radius for a generation of ``n`` evenly spaced rays.
            r_stop = max(floor, d / (2.0 * np.sin(np.pi / n)))
            # r_stop grows with n, so once it clears the rim no finer generation
            # fits either and we are done.
            if r_stop >= boundary:
                break
            for k in range(n):
                theta = -np.pi + 2.0 * np.pi * k / n
                key = round(theta, 9)
                if key in emitted:  # even k coincide with a coarser generation
                    continue
                emitted.add(key)
                idx = cls._nearest_index(thetas, theta)
                outer = float(interior[idx])
                if outer <= r_stop:  # no interior room past the butée here
                    continue
                sampled = float(thetas[idx])
                points = [
                    PolarPoint(r=r_stop, theta=sampled, z=profile.z),
                    PolarPoint(r=outer, theta=sampled, z=profile.z),
                ]
                paths.append(
                    ToolPath(role=PathRole.INFILL, points=points, closed=False)
                )
            if n >= target:  # density cap reached
                break
            n *= 2
        return paths

    @staticmethod
    def _nearest_index(thetas: np.ndarray, theta: float) -> int:
        """Index of the sampled angle closest to ``theta`` on the circle."""
        delta = np.abs(np.angle(np.exp(1j * (thetas - theta))))
        return int(np.argmin(delta))
