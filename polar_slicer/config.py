"""Centralized slicer configuration.

Every tunable parameter of the slicing process lives here. No other module is
allowed to hard-code process values (layer height, number of perimeters, infill
percentage, axis names, ...); they all read them from a :class:`SlicerConfig`
instance that is injected into them. This keeps the whole behaviour of the
slicer driven by a single, explicit surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class InfillType(str, Enum):
    """Selectable infill strategies.

    The value is a stable, human-readable string so a configuration can be
    round-tripped to/from text (CLI flags, config files) without a lookup table.
    """

    SOLID = "solid"
    GRID = "grid"


@dataclass(frozen=True)
class SlicerConfig:
    """Immutable bundle of every process parameter.

    Instances are frozen so a configuration cannot be mutated halfway through a
    slice, which would make the produced G-code impossible to reason about.

    Attributes
    ----------
    layer_height:
        Vertical distance between two consecutive layers, in millimetres.
    extrusion_width:
        Width of a single extruded line, in millimetres. Drives the spacing
        between concentric perimeters and solid-infill rings.
    perimeters:
        Number of contour lines generated around each layer's boundary.
    wall_thickness:
        Radial thickness of the part's shell, in millimetres. Infill is only
        generated *inside* this shell (``R < R_outer - wall_thickness``).
    infill_percentage:
        Density of the infill, in percent (0-100). ``0`` disables infill,
        ``100`` makes the grid strategy as dense as the solid one.
    infill_type:
        Which :class:`InfillType` strategy to use for the interior volume.
    angular_steps:
        Number of angular samples used to describe a layer boundary and to
        render rings/spokes. Higher means smoother polar curves.
    center:
        Optional ``(x, y)`` rotation axis for the polar conversion. When
        ``None`` the mesh XY centroid is used.
    flow:
        Extrusion multiplier converting travelled distance (mm) into extruded
        filament length (mm) for the ``E`` axis.
    radial_axis / angular_axis / z_axis:
        G-code axis letters for the radius, rotation angle and height.
    angular_in_degrees:
        When ``True`` the angular axis is emitted in degrees, otherwise radians.
    feedrate:
        Movement feedrate in mm/min written on the first move.
    """

    # Vertical resolution / extrusion geometry.
    layer_height: float = 0.2
    extrusion_width: float = 0.4

    # Shell.
    perimeters: int = 2
    wall_thickness: float = 1.2

    # Infill.
    infill_percentage: float = 20.0
    infill_type: InfillType = InfillType.GRID

    # Polar sampling.
    angular_steps: int = 180
    center: tuple[float, float] | None = None

    # Extrusion / G-code.
    flow: float = 0.05
    radial_axis: str = "X"
    angular_axis: str = "A"
    z_axis: str = "Z"
    angular_in_degrees: bool = True
    feedrate: float = 1200.0

    def __post_init__(self) -> None:
        """Validate invariants that every downstream module relies on."""
        if self.layer_height <= 0:
            raise ValueError("layer_height must be > 0")
        if self.extrusion_width <= 0:
            raise ValueError("extrusion_width must be > 0")
        if self.perimeters < 0:
            raise ValueError("perimeters must be >= 0")
        if self.wall_thickness < 0:
            raise ValueError("wall_thickness must be >= 0")
        if not 0.0 <= self.infill_percentage <= 100.0:
            raise ValueError("infill_percentage must be within [0, 100]")
        if self.angular_steps < 3:
            raise ValueError("angular_steps must be >= 3")
        if not isinstance(self.infill_type, InfillType):
            raise TypeError("infill_type must be an InfillType")
