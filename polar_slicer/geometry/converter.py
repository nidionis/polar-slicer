"""Conversion between Cartesian and polar coordinate systems.

The abstraction lets any part of the pipeline convert coordinates without
knowing *how* the conversion is done or *where* the central axis is. The
concrete :class:`PolarConverter` performs the conversion about a fixed
``(cx, cy)`` axis.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from polar_slicer.geometry.points import CartesianPoint, PolarPoint


class CoordinateConverter(ABC):
    """Interface converting points between Cartesian and polar systems."""

    @abstractmethod
    def to_polar(self, point: CartesianPoint) -> PolarPoint:
        """Convert a Cartesian point to polar coordinates."""

    @abstractmethod
    def to_cartesian(self, point: PolarPoint) -> CartesianPoint:
        """Convert a polar point back to Cartesian coordinates."""


class PolarConverter(CoordinateConverter):
    """Cylindrical-polar conversion about a fixed central axis ``(cx, cy)``."""

    def __init__(self, center: tuple[float, float] = (0.0, 0.0)) -> None:
        self._cx, self._cy = center

    @property
    def center(self) -> tuple[float, float]:
        return (self._cx, self._cy)

    def to_polar(self, point: CartesianPoint) -> PolarPoint:
        dx = point.x - self._cx
        dy = point.y - self._cy
        r = math.hypot(dx, dy)
        theta = math.atan2(dy, dx)
        return PolarPoint(r=r, theta=theta, z=point.z)

    def to_cartesian(self, point: PolarPoint) -> CartesianPoint:
        x = self._cx + point.r * math.cos(point.theta)
        y = self._cy + point.r * math.sin(point.theta)
        return CartesianPoint(x=x, y=y, z=point.z)
