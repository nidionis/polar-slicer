"""Tests for the centralized configuration."""

from __future__ import annotations

import dataclasses

import pytest

from polar_slicer.config import InfillType, SlicerConfig


def test_defaults_are_valid():
    config = SlicerConfig()
    assert config.perimeters >= 0
    assert config.infill_type is InfillType.GRID


def test_is_frozen():
    config = SlicerConfig()
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.perimeters = 5  # type: ignore[misc]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"layer_height": 0.0},
        {"extrusion_width": -1.0},
        {"perimeters": -1},
        {"wall_thickness": -0.1},
        {"infill_percentage": 150.0},
        {"angular_steps": 2},
    ],
)
def test_invalid_values_rejected(kwargs):
    with pytest.raises((ValueError, TypeError)):
        SlicerConfig(**kwargs)


def test_infill_type_roundtrips_via_string():
    assert InfillType("solid") is InfillType.SOLID
    assert InfillType("grid") is InfillType.GRID
