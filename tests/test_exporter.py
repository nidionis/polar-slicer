"""Tests for the polar G-code exporter."""

from __future__ import annotations

import math
import re

from polar_slicer.config import SlicerConfig
from polar_slicer.export.exporter import PolarGCodeExporter
from polar_slicer.geometry.points import PolarPoint
from polar_slicer.slicing.layer import Layer
from polar_slicer.toolpath.path import PathRole, ToolPath


def _ring_path(radius: float = 5.0, z: float = 1.0, n: int = 8) -> ToolPath:
    pts = [
        PolarPoint(r=radius, theta=-math.pi + i * (2 * math.pi / n), z=z)
        for i in range(n)
    ]
    return ToolPath(role=PathRole.PERIMETER, points=pts, closed=True)


def test_header_declares_axes():
    config = SlicerConfig(radial_axis="X", angular_axis="A", z_axis="Z")
    gcode = PolarGCodeExporter().export([Layer(z=1.0)], [[]], config)
    assert "G21" in gcode and "G90" in gcode
    assert "radius  -> X" in gcode
    assert "angle   -> A" in gcode


def test_moves_use_configured_axis_letters():
    config = SlicerConfig(radial_axis="R", angular_axis="C", z_axis="Z")
    layer = Layer(z=1.0)
    gcode = PolarGCodeExporter().export([layer], [[_ring_path()]], config)
    move_lines = [ln for ln in gcode.splitlines() if ln.startswith(("G0", "G1"))]
    assert move_lines
    for ln in move_lines:
        assert re.search(r"\bR[-0-9.]+", ln)
        assert re.search(r"\bC[-0-9.]+", ln)
        assert re.search(r"\bZ[-0-9.]+", ln)


def test_extrusion_is_monotonic_and_positive():
    config = SlicerConfig()
    gcode = PolarGCodeExporter().export([Layer(z=1.0)], [[_ring_path()]], config)
    e_values = [
        float(m.group(1))
        for ln in gcode.splitlines()
        if (m := re.search(r"\bE([-0-9.]+)", ln))
    ]
    assert e_values
    assert e_values == sorted(e_values)
    assert e_values[-1] > 0.0


def test_closed_path_seam_does_not_command_full_reverse_turn():
    """Angle unwrapping keeps the rotary step small across the +/-pi seam."""
    config = SlicerConfig(angular_in_degrees=True)
    gcode = PolarGCodeExporter().export([Layer(z=1.0)], [[_ring_path(n=8)]], config)
    angles = [
        float(m.group(1))
        for ln in gcode.splitlines()
        if (m := re.search(r"\bA([-0-9.]+)", ln))
    ]
    steps = [abs(b - a) for a, b in zip(angles, angles[1:])]
    # Each step is ~45 deg; unwrapping must keep every step well under 180.
    assert max(steps) < 90.0


def test_travel_move_has_no_extrusion():
    config = SlicerConfig()
    gcode = PolarGCodeExporter().export([Layer(z=1.0)], [[_ring_path()]], config)
    travels = [ln for ln in gcode.splitlines() if ln.startswith("G0")]
    assert travels
    assert all("E" not in ln for ln in travels)
