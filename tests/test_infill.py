"""Tests for infill strategies and the selection factory."""

from __future__ import annotations

import numpy as np
import pytest

from polar_slicer.config import InfillType, SlicerConfig
from polar_slicer.geometry.profile import RadialProfile
from polar_slicer.infill.factory import InfillStrategyFactory
from polar_slicer.infill.grid import GridInfill
from polar_slicer.infill.solid import SolidInfill
from polar_slicer.toolpath.path import PathRole


def _uniform_profile(radius: float = 10.0, steps: int = 90) -> RadialProfile:
    thetas = np.linspace(-np.pi, np.pi, steps, endpoint=False)
    radii = np.full(steps, radius)
    return RadialProfile(z=1.0, thetas=thetas, radii=radii, center=(0.0, 0.0))


# --- factory --------------------------------------------------------------

def test_factory_selects_by_config():
    factory = InfillStrategyFactory()
    assert isinstance(
        factory.create(SlicerConfig(infill_type=InfillType.SOLID)), SolidInfill
    )
    assert isinstance(
        factory.create(SlicerConfig(infill_type=InfillType.GRID)), GridInfill
    )


def test_factory_is_extensible():
    factory = InfillStrategyFactory()
    sentinel = SolidInfill  # pretend custom strategy
    factory.register(InfillType.GRID, sentinel)
    assert isinstance(factory.create(SlicerConfig(infill_type=InfillType.GRID)), SolidInfill)


# --- solid ----------------------------------------------------------------

def test_solid_stays_inside_shell():
    profile = _uniform_profile(radius=10.0)
    config = SlicerConfig(
        infill_type=InfillType.SOLID, wall_thickness=2.0, perimeters=0
    )
    paths = SolidInfill().generate(profile, config)
    assert paths
    assert all(p.role is PathRole.INFILL for p in paths)
    # No infill ring may exceed the interior boundary (10 - 2 = 8).
    assert max(pt.r for p in paths for pt in p.points) <= 8.0 + 1e-9


def test_solid_rings_touch():
    profile = _uniform_profile(radius=10.0)
    config = SlicerConfig(
        infill_type=InfillType.SOLID, wall_thickness=2.0, perimeters=0,
        extrusion_width=0.4,
    )
    paths = SolidInfill().generate(profile, config)
    outer_radii = sorted({round(p.points[0].r, 6) for p in paths})
    diffs = np.diff(outer_radii)
    assert np.allclose(diffs, 0.4, atol=1e-6)


# --- grid -----------------------------------------------------------------

def test_grid_has_rings_and_spokes():
    profile = _uniform_profile(radius=10.0)
    config = SlicerConfig(
        infill_type=InfillType.GRID, infill_percentage=50.0,
        wall_thickness=2.0, perimeters=0,
    )
    paths = GridInfill().generate(profile, config)
    closed = [p for p in paths if p.closed]   # rings
    spokes = [p for p in paths if not p.closed]
    assert closed and spokes
    assert all(len(s) == 2 for s in spokes)  # radial line = 2 points


def test_grid_density_controls_ring_spacing():
    profile = _uniform_profile(radius=10.0)
    dense = GridInfill().generate(
        profile,
        SlicerConfig(infill_type=InfillType.GRID, infill_percentage=100.0,
                     wall_thickness=2.0, perimeters=0),
    )
    sparse = GridInfill().generate(
        profile,
        SlicerConfig(infill_type=InfillType.GRID, infill_percentage=20.0,
                     wall_thickness=2.0, perimeters=0),
    )
    dense_rings = len([p for p in dense if p.closed])
    sparse_rings = len([p for p in sparse if p.closed])
    assert dense_rings > sparse_rings


def test_grid_spokes_avoid_center():
    profile = _uniform_profile(radius=10.0)
    width = 0.4
    config = SlicerConfig(
        infill_type=InfillType.GRID, infill_percentage=80.0,
        wall_thickness=2.0, perimeters=0, extrusion_width=width,
    )
    spokes = [p for p in GridInfill().generate(profile, config) if not p.closed]
    assert spokes
    # No ray reaches the axis; the innermost stop is the floor R0 = d/2.
    assert all(len(s) == 2 for s in spokes)
    inner = [min(pt.r for pt in s.points) for s in spokes]
    assert min(inner) >= width / 2.0 - 1e-9
    # Every ray stays inside the interior boundary (10 - 2 = 8).
    assert max(pt.r for s in spokes for pt in s.points) <= 8.0 + 1e-9


def test_grid_spoke_stop_radius_grows_with_count():
    profile = _uniform_profile(radius=10.0)
    width = 0.4
    config = SlicerConfig(
        infill_type=InfillType.GRID, infill_percentage=100.0,
        wall_thickness=2.0, perimeters=0, extrusion_width=width,
    )
    spokes = [p for p in GridInfill().generate(profile, config) if not p.closed]
    stops = sorted({round(min(pt.r for pt in s.points), 6) for s in spokes})
    # Hierarchical field: several distinct butée radii, not one uniform hole.
    assert len(stops) >= 3
    # The coarsest (4 principal axes) reach the innermost chord radius
    # d/(2*sin(pi/4)); finer generations stop strictly farther out.
    coarsest = width / (2.0 * np.sin(np.pi / 4.0))
    assert stops[0] == pytest.approx(coarsest, abs=1e-6)
    assert stops[1] > stops[0]


def test_grid_denser_infill_more_spokes():
    profile = _uniform_profile(radius=10.0)
    dense = GridInfill().generate(
        profile,
        SlicerConfig(infill_type=InfillType.GRID, infill_percentage=100.0,
                     wall_thickness=2.0, perimeters=0),
    )
    sparse = GridInfill().generate(
        profile,
        SlicerConfig(infill_type=InfillType.GRID, infill_percentage=20.0,
                     wall_thickness=2.0, perimeters=0),
    )
    dense_spokes = len([p for p in dense if not p.closed])
    sparse_spokes = len([p for p in sparse if not p.closed])
    assert dense_spokes > sparse_spokes


def test_grid_zero_percent_is_empty():
    profile = _uniform_profile()
    paths = GridInfill().generate(
        profile, SlicerConfig(infill_type=InfillType.GRID, infill_percentage=0.0)
    )
    assert paths == []
