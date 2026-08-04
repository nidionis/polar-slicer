"""Tests for the plane layer slicer."""

from __future__ import annotations

import numpy as np

from polar_slicer.config import SlicerConfig
from polar_slicer.mesh.model import Mesh
from polar_slicer.slicing.slicer import PlaneLayerSlicer


def test_layer_count(cylinder):
    mesh = Mesh(cylinder)  # height 5.0
    config = SlicerConfig(layer_height=1.0)
    layers = PlaneLayerSlicer().slice(mesh, config)
    # First plane at z=0.5, then 1.5, 2.5, 3.5, 4.5 -> 5 layers below z_max=5.
    assert len(layers) == 5
    assert all(0.0 < layer.z < 5.0 for layer in layers)


def test_contours_are_closed_loops(cylinder):
    mesh = Mesh(cylinder)
    config = SlicerConfig(layer_height=1.0)
    layers = PlaneLayerSlicer().slice(mesh, config)
    mid = layers[len(layers) // 2]
    assert not mid.is_empty
    contour = max(mid.contours, key=len)
    # A cylinder cross-section is a single loop with ~one point per segment.
    assert len(contour) >= 3


def test_cross_section_radius_matches_cylinder(cylinder):
    mesh = Mesh(cylinder)  # radius 10 about origin
    config = SlicerConfig(layer_height=1.0)
    layers = PlaneLayerSlicer().slice(mesh, config)
    contour = max(layers[2].contours, key=len)
    radii = np.hypot(contour.points[:, 0], contour.points[:, 1])
    assert np.allclose(radii, 10.0, atol=0.5)


def test_empty_mesh_yields_no_layers():
    mesh = Mesh(np.empty((0, 3, 3)))
    layers = PlaneLayerSlicer().slice(mesh, SlicerConfig())
    assert layers == []
