"""Tests for infill strategies and the selection factory."""

from __future__ import annotations

import numpy as np

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


def test_grid_zero_percent_is_empty():
    profile = _uniform_profile()
    paths = GridInfill().generate(
        profile, SlicerConfig(infill_type=InfillType.GRID, infill_percentage=0.0)
    )
    assert paths == []
