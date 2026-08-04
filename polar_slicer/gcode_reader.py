"""Read polar G-code back into Cartesian toolpaths for visualization.

This is the inverse of :class:`~polar_slicer.export.exporter.PolarGCodeExporter`:
it parses the G-code text (using the same configurable axis letters) and returns
per-layer line segments in Cartesian space, tagged as perimeter, infill or
travel. Rendering the *parsed G-code* — rather than the internal toolpaths —
guarantees the viewer shows exactly what the file contains.

The radius is plotted about the origin ``(0, 0)``; the physical rotation-axis
offset is irrelevant for a per-layer preview and is not stored in the G-code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Segment:
    """A straight line segment between two Cartesian points."""

    x1: float
    y1: float
    x2: float
    y2: float
    kind: str  # "perimeter" | "infill" | "travel"

    def as_dict(self) -> dict:
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "kind": self.kind,
        }


@dataclass
class ViewLayer:
    """All segments of one layer, plus its height."""

    z: float
    segments: list[Segment] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"z": self.z, "segments": [s.as_dict() for s in self.segments]}


class PolarGCodeReader:
    """Parse polar G-code into a list of :class:`ViewLayer`.

    Parameters
    ----------
    radial_axis / angular_axis / z_axis:
        Axis letters used when the G-code was written.
    angular_in_degrees:
        Whether the angular axis is in degrees (else radians).
    """

    def __init__(
        self,
        radial_axis: str = "X",
        angular_axis: str = "A",
        z_axis: str = "Z",
        angular_in_degrees: bool = True,
    ) -> None:
        self._radial = radial_axis.upper()
        self._angular = angular_axis.upper()
        self._z = z_axis.upper()
        self._degrees = angular_in_degrees

    def read(self, gcode: str) -> list[ViewLayer]:
        layers: list[ViewLayer] = []
        current: ViewLayer | None = None
        role = "perimeter"
        last: tuple[float, float] | None = None
        last_z = 0.0

        for raw in gcode.splitlines():
            line = raw.strip()
            if not line:
                continue

            if line.startswith(";"):
                comment = line[1:].strip()
                if comment.startswith("layer"):
                    current = ViewLayer(z=self._parse_layer_z(comment))
                    layers.append(current)
                    last = None  # no segment across the layer boundary
                elif comment in ("perimeter", "infill"):
                    role = comment
                continue

            if not (line.startswith("G0") or line.startswith("G1")):
                continue

            words = self._parse_words(line)
            if self._radial not in words or self._angular not in words:
                continue

            r = words[self._radial]
            theta = words[self._angular]
            if self._degrees:
                theta = math.radians(theta)
            x = r * math.cos(theta)
            y = r * math.sin(theta)
            last_z = words.get(self._z, last_z)

            travel = line.startswith("G0")
            if current is not None and last is not None:
                kind = "travel" if travel else role
                current.segments.append(Segment(last[0], last[1], x, y, kind))
            last = (x, y)

        return layers

    @staticmethod
    def _parse_layer_z(comment: str) -> float:
        # comment looks like "layer 3 z=1.5000"
        for token in comment.split():
            if token.startswith("z="):
                try:
                    return float(token[2:])
                except ValueError:
                    return 0.0
        return 0.0

    @staticmethod
    def _parse_words(line: str) -> dict[str, float]:
        words: dict[str, float] = {}
        for token in line.split()[1:]:  # skip the G-command itself
            letter = token[:1].upper()
            try:
                words[letter] = float(token[1:])
            except ValueError:
                continue
        return words
