"""The infill strategy interface.

Infill only fills the interior volume that lies *beyond* the shell, i.e. inside
``R_outer(theta) - wall_thickness``. Every concrete strategy receives the layer
profile and must confine its geometry to that interior radius. Splitting each
strategy into its own class keeps them independently testable and lets new fill
patterns be added without touching existing ones (Open/Closed).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from polar_slicer.config import SlicerConfig
from polar_slicer.geometry.profile import RadialProfile
from polar_slicer.toolpath.path import ToolPath


class InfillStrategy(ABC):
    """Interface generating the infill toolpaths for a single layer."""

    @abstractmethod
    def generate(
        self, profile: RadialProfile, config: SlicerConfig
    ) -> list[ToolPath]:
        """Return infill toolpaths confined to the interior of ``profile``."""

    @staticmethod
    def interior_radii(profile: RadialProfile, config: SlicerConfig) -> np.ndarray:
        """Per-angle radius of the infill boundary.

        This is the outer radius pulled in by the full shell: ``perimeters``
        already consume ``perimeters * width`` and the requested
        ``wall_thickness`` sets the minimum shell. We take the larger of the two
        so the shell is never thinner than configured.
        """
        shell = max(
            config.wall_thickness,
            config.perimeters * config.extrusion_width,
        )
        return profile.radii - shell
