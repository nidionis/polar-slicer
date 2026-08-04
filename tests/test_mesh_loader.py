"""Tests for the STL loader (binary and ASCII)."""

from __future__ import annotations

import numpy as np

from polar_slicer.mesh.loader import StlMeshLoader
from polar_slicer.mesh.model import Mesh


def test_load_binary(binary_stl, cube):
    mesh = StlMeshLoader().load(binary_stl)
    assert isinstance(mesh, Mesh)
    assert len(mesh) == cube.shape[0] == 12
    assert np.allclose(mesh.min_bound, [0, 0, 0])
    assert np.allclose(mesh.max_bound, [10, 10, 10])


def test_load_ascii(ascii_stl, cube):
    mesh = StlMeshLoader().load(ascii_stl)
    assert len(mesh) == 12
    assert np.allclose(mesh.max_bound, [10, 10, 10])


def test_binary_and_ascii_agree(binary_stl, ascii_stl):
    a = StlMeshLoader().load(binary_stl)
    b = StlMeshLoader().load(ascii_stl)
    assert np.allclose(np.sort(a.triangles.reshape(-1)), np.sort(b.triangles.reshape(-1)))


def test_mesh_is_immutable(binary_stl):
    mesh = StlMeshLoader().load(binary_stl)
    assert mesh.triangles.flags.writeable is False


def test_centroid_of_cube(binary_stl):
    mesh = StlMeshLoader().load(binary_stl)
    cx, cy = mesh.xy_centroid
    assert abs(cx - 5.0) < 1.0
    assert abs(cy - 5.0) < 1.0
