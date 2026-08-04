"""Tests for the polar G-code reader (visualization round-trip)."""

from __future__ import annotations

import math

from polar_slicer.config import SlicerConfig
from polar_slicer.export.exporter import PolarGCodeExporter
from polar_slicer.gcode_reader import PolarGCodeReader
from polar_slicer.geometry.points import PolarPoint
from polar_slicer.slicing.layer import Layer
from polar_slicer.toolpath.path import PathRole, ToolPath


def _ring(radius=5.0, z=1.0, n=8):
    pts = [
        PolarPoint(r=radius, theta=-math.pi + i * (2 * math.pi / n), z=z)
        for i in range(n)
    ]
    return ToolPath(role=PathRole.PERIMETER, points=pts, closed=True)


def _reader_for(config: SlicerConfig) -> PolarGCodeReader:
    return PolarGCodeReader(
        radial_axis=config.radial_axis,
        angular_axis=config.angular_axis,
        z_axis=config.z_axis,
        angular_in_degrees=config.angular_in_degrees,
    )


def test_reader_recovers_layer_count():
    config = SlicerConfig()
    layers = [Layer(z=0.5), Layer(z=1.5)]
    toolpaths = [[_ring(z=0.5)], [_ring(z=1.5)]]
    gcode = PolarGCodeExporter().export(layers, toolpaths, config)

    view = _reader_for(config).read(gcode)
    assert len(view) == 2
    assert math.isclose(view[0].z, 0.5)
    assert math.isclose(view[1].z, 1.5)


def test_reader_recovers_ring_radius():
    config = SlicerConfig()
    gcode = PolarGCodeExporter().export([Layer(z=1.0)], [[_ring(radius=5.0)]], config)
    view = _reader_for(config).read(gcode)
    extrude = [s for s in view[0].segments if s.kind == "perimeter"]
    assert extrude
    for s in extrude:
        assert math.isclose(math.hypot(s.x1, s.y1), 5.0, abs_tol=1e-3)
        assert math.isclose(math.hypot(s.x2, s.y2), 5.0, abs_tol=1e-3)


def test_reader_tags_travel_moves():
    config = SlicerConfig()
    # Two paths in one layer -> a travel move is emitted between them.
    gcode = PolarGCodeExporter().export(
        [Layer(z=1.0)], [[_ring(radius=5.0), _ring(radius=3.0)]], config
    )
    kinds = {s.kind for s in _reader_for(config).read(gcode)[0].segments}
    assert "travel" in kinds
    assert "perimeter" in kinds


def test_reader_honours_radian_axis_letters():
    config = SlicerConfig(
        radial_axis="R", angular_axis="C", angular_in_degrees=False
    )
    gcode = PolarGCodeExporter().export([Layer(z=1.0)], [[_ring(radius=3.0)]], config)
    view = _reader_for(config).read(gcode)
    assert view and view[0].segments
    s = next(s for s in view[0].segments if s.kind == "perimeter")
    assert math.isclose(math.hypot(s.x1, s.y1), 3.0, abs_tol=1e-3)
