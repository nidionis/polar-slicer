"""G-code export.

:class:`GCodeExporter` is the abstraction; :class:`PolarGCodeExporter` writes
G-code for a rotative/polar motion system, emitting the radius, rotation angle
and height on configurable axis letters. Angles are unwrapped along each path so
the rotary axis turns continuously instead of snapping across the +/-pi seam.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod

from polar_slicer.config import SlicerConfig
from polar_slicer.geometry.points import PolarPoint
from polar_slicer.slicing.layer import Layer
from polar_slicer.toolpath.path import ToolPath


class GCodeExporter(ABC):
    """Interface turning per-layer toolpaths into a G-code string."""

    @abstractmethod
    def export(
        self,
        layers: list[Layer],
        toolpaths: list[list[ToolPath]],
        config: SlicerConfig,
    ) -> str:
        """Render G-code for ``toolpaths`` (one inner list per layer)."""


class PolarGCodeExporter(GCodeExporter):
    """Emit polar G-code: radius, angle and height on configurable axes."""

    def export(
        self,
        layers: list[Layer],
        toolpaths: list[list[ToolPath]],
        config: SlicerConfig,
    ) -> str:
        lines: list[str] = []
        lines.extend(self._header(config))

        extrude = 0.0
        first_move = True
        for index, (layer, paths) in enumerate(zip(layers, toolpaths)):
            lines.append(f"; layer {index} z={layer.z:.4f}")
            for path in paths:
                if path.is_empty:
                    continue
                extrude, first_move = self._emit_path(
                    lines, path, config, extrude, first_move
                )
        lines.append("; end")
        return "\n".join(lines) + "\n"

    def _header(self, config: SlicerConfig) -> list[str]:
        unit = "degrees" if config.angular_in_degrees else "radians"
        return [
            "; polar-slicer G-code",
            "; coordinates are polar (R, theta, Z)",
            f";   radius  -> {config.radial_axis}",
            f";   angle   -> {config.angular_axis} ({unit})",
            f";   height  -> {config.z_axis}",
            "G21 ; millimetres",
            "G90 ; absolute positioning",
            "M82 ; absolute extrusion",
            "G92 E0",
        ]

    def _emit_path(
        self,
        lines: list[str],
        path: ToolPath,
        config: SlicerConfig,
        extrude: float,
        first_move: bool,
    ) -> tuple[float, bool]:
        points = list(path.points)
        if path.closed:
            points = points + [points[0]]

        # Unwrap angles so the rotary axis moves continuously.
        angles = self._unwrap([p.theta for p in points])

        # Travel to the first point without extruding.
        lines.append(
            "; " + path.role.value
        )
        lines.append(
            self._move(config, points[0], angles[0], extrude, first_move, travel=True)
        )
        first_move = False

        prev = points[0]
        prev_angle = angles[0]
        for point, angle in zip(points[1:], angles[1:]):
            extrude += self._segment_length(prev, prev_angle, point, angle) * config.flow
            lines.append(
                self._move(config, point, angle, extrude, first_move, travel=False)
            )
            prev, prev_angle = point, angle
        return extrude, first_move

    def _move(
        self,
        config: SlicerConfig,
        point: PolarPoint,
        angle: float,
        extrude: float,
        with_feedrate: bool,
        travel: bool,
    ) -> str:
        angle_value = math.degrees(angle) if config.angular_in_degrees else angle
        parts = [
            "G0" if travel else "G1",
            f"{config.radial_axis}{self._fmt(point.r)}",
            f"{config.angular_axis}{self._fmt(angle_value)}",
            f"{config.z_axis}{self._fmt(point.z)}",
        ]
        if with_feedrate:
            parts.append(f"F{self._fmt(config.feedrate)}")
        if not travel:
            parts.append(f"E{self._fmt(extrude)}")
        return " ".join(parts)

    @staticmethod
    def _unwrap(angles: list[float]) -> list[float]:
        """Add multiples of 2*pi so consecutive angles are as close as possible."""
        if not angles:
            return []
        out = [angles[0]]
        for a in angles[1:]:
            prev = out[-1]
            delta = a - prev
            # Shift delta into (-pi, pi].
            delta -= 2.0 * math.pi * math.floor((delta + math.pi) / (2.0 * math.pi))
            out.append(prev + delta)
        return out

    @staticmethod
    def _segment_length(
        a: PolarPoint, a_angle: float, b: PolarPoint, b_angle: float
    ) -> float:
        """Cartesian length of a polar segment (law of cosines + Z)."""
        d_theta = b_angle - a_angle
        planar_sq = (
            a.r * a.r + b.r * b.r - 2.0 * a.r * b.r * math.cos(d_theta)
        )
        planar_sq = max(planar_sq, 0.0)
        dz = b.z - a.z
        return math.sqrt(planar_sq + dz * dz)

    @staticmethod
    def _fmt(value: float) -> str:
        # Fixed 5-decimal precision, trailing zeros trimmed for compactness.
        return f"{value:.5f}".rstrip("0").rstrip(".") or "0"
