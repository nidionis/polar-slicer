"""Tests for concentric perimeter generation."""

from __future__ import annotations

import numpy as np

from polar_slicer.config import SlicerConfig
from polar_slicer.geometry.profile import RadialProfile
from polar_slicer.perimeters.generator import ConcentricPerimeterGenerator
from polar_slicer.toolpath.path import PathRole


def _uniform_profile(radius: float = 10.0, steps: int = 60) -> RadialProfile:
    thetas = np.linspace(-np.pi, np.pi, steps, endpoint=False)
    radii = np.full(steps, radius)
    return RadialProfile(z=1.0, thetas=thetas, radii=radii, center=(0.0, 0.0))


def test_perimeter_count_matches_config():
    profile = _uniform_profile()
    for n in (0, 1, 3, 5):
        config = SlicerConfig(perimeters=n)
        paths = ConcentricPerimeterGenerator().generate(profile, config)
        assert len(paths) == n
        assert all(p.role is PathRole.PERIMETER for p in paths)
        assert all(p.closed for p in paths)


def test_perimeters_offset_inward_by_width():
    profile = _uniform_profile(radius=10.0)
    config = SlicerConfig(perimeters=3, extrusion_width=0.4)
    paths = ConcentricPerimeterGenerator().generate(profile, config)
    radii = [p.points[0].r for p in paths]
    # ring k at 10 - (k + 0.5)*0.4
    assert np.allclose(radii, [9.8, 9.4, 9.0])


def test_perimeters_drop_when_radius_collapses():
    profile = _uniform_profile(radius=0.5)
    config = SlicerConfig(perimeters=5, extrusion_width=0.4)
    paths = ConcentricPerimeterGenerator().generate(profile, config)
    # 0.5 - 0.2 = 0.3 (ok); 0.5 - 0.6 < 0 -> dropped, so only 1 survives.
    assert len(paths) == 1
