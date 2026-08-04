"""Toolpath value objects.

A :class:`ToolPath` is a single continuous extrusion move expressed as an
ordered list of :class:`~polar_slicer.geometry.points.PolarPoint`. Generators
(perimeters, infill) emit them; the exporter turns them into G-code, inserting
travel moves between paths as needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from polar_slicer.geometry.points import PolarPoint


class PathRole(str, Enum):
    """What a toolpath represents, for annotation and possible per-role tuning."""

    PERIMETER = "perimeter"
    INFILL = "infill"


@dataclass(frozen=True)
class ToolPath:
    """An ordered polar polyline extruded as one continuous move.

    Attributes
    ----------
    role:
        Whether this path is a perimeter or infill move.
    points:
        Ordered polar points. Consecutive points are connected by extrusion.
    closed:
        When ``True`` the path is a closed loop and the exporter appends the
        first point again to seal it.
    """

    role: PathRole
    points: list[PolarPoint] = field(default_factory=list)
    closed: bool = False

    def __len__(self) -> int:
        return len(self.points)

    @property
    def is_empty(self) -> bool:
        return len(self.points) == 0
