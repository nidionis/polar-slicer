"""Immutable point value objects for the two coordinate systems used."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class CartesianPoint:
    """A point in Cartesian space ``(x, y, z)``, millimetres."""

    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class PolarPoint:
    """A point in cylindrical-polar space ``(r, theta, z)``.

    ``r`` is the radius from the central axis (mm), ``theta`` the angle in
    radians, and ``z`` the height (mm). This is the native representation the
    rotative printer consumes.
    """

    r: float
    theta: float
    z: float = 0.0

    @property
    def theta_degrees(self) -> float:
        """The angle expressed in degrees."""
        return math.degrees(self.theta)
