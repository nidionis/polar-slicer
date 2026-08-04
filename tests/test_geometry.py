"""Tests for coordinate conversion and radial profiling."""

from __future__ import annotations

import math

import numpy as np

from polar_slicer.config import SlicerConfig
from polar_slicer.geometry.converter import PolarConverter
from polar_slicer.geometry.points import CartesianPoint, PolarPoint
from polar_slicer.geometry.profile import RaycastProfileBuilder
from polar_slicer.slicing.layer import Contour, Layer


def test_converter_roundtrip():
    converter = PolarConverter(center=(1.0, -2.0))
    original = CartesianPoint(4.0, 3.0, 7.0)
    polar = converter.to_polar(original)
    back = converter.to_cartesian(polar)
    assert math.isclose(back.x, original.x, abs_tol=1e-9)
    assert math.isclose(back.y, original.y, abs_tol=1e-9)
    assert math.isclose(back.z, original.z, abs_tol=1e-9)


def test_polar_point_degrees():
    p = PolarPoint(r=1.0, theta=math.pi)
    assert math.isclose(p.theta_degrees, 180.0)


def _square_layer(half: float = 5.0, z: float = 1.0) -> Layer:
    pts = np.array([[-half, -half], [half, -half], [half, half], [-half, half]])
    return Layer(z=z, contours=[Contour(pts)])


def test_profile_radii_match_square_geometry():
    """A ray at angle 0 through a centred square hits the right edge at x=half."""
    layer = _square_layer(half=5.0)
    converter = PolarConverter(center=(0.0, 0.0))
    config = SlicerConfig(angular_steps=4)  # angles at -pi, -pi/2, 0, pi/2
    profile = RaycastProfileBuilder().build(layer, converter, config)

    # angular_steps=4 -> thetas = [-pi, -pi/2, 0, pi/2]; each ray exits at an
    # edge midpoint, radius == half.
    assert np.allclose(profile.radii, 5.0, atol=1e-9)
    assert math.isclose(profile.z, 1.0)


def test_profile_diagonal_reaches_corner():
    layer = _square_layer(half=5.0)
    converter = PolarConverter(center=(0.0, 0.0))
    config = SlicerConfig(angular_steps=8)
    profile = RaycastProfileBuilder().build(layer, converter, config)
    # The diagonal rays (theta = +/-pi/4, +/-3pi/4) reach the corners at r = half*sqrt(2).
    assert math.isclose(profile.max_radius, 5.0 * math.sqrt(2.0), rel_tol=1e-6)
