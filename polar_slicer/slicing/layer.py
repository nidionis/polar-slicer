"""Cross-section data structures produced by slicing.

A :class:`Contour` is a single closed loop of 2D points at a fixed height. A
:class:`Layer` groups every contour found at one Z height. These types carry no
behaviour beyond simple geometry queries; the slicing algorithm lives in
:mod:`polar_slicer.slicing.slicer`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Contour:
    """A closed polyline of ``(x, y)`` points at a single height.

    The loop is implicitly closed: the last point connects back to the first;
    the closing point is not duplicated in ``points``.
    """

    points: np.ndarray  # shape (M, 2)

    def __post_init__(self) -> None:
        pts = np.asarray(self.points, dtype=np.float64)
        if pts.ndim != 2 or pts.shape[1] != 2:
            raise ValueError(f"contour points must be (M, 2), got {pts.shape}")
        object.__setattr__(self, "points", pts)

    def __len__(self) -> int:
        return int(self.points.shape[0])

    @property
    def centroid(self) -> tuple[float, float]:
        return (float(self.points[:, 0].mean()), float(self.points[:, 1].mean()))

    def signed_area(self) -> float:
        """Signed area via the shoelace formula (CCW positive)."""
        x = self.points[:, 0]
        y = self.points[:, 1]
        return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


@dataclass(frozen=True)
class Layer:
    """All closed contours found at one Z height."""

    z: float
    contours: list[Contour] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.contours) == 0
