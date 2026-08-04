"""Shared pytest fixtures.

The repository root is put on ``sys.path`` so the ``examples`` helpers (mesh
generators, STL writers) can be imported by tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from examples.make_sample_stl import (  # noqa: E402
    cube_triangles,
    cylinder_triangles,
    write_ascii_stl,
    write_binary_stl,
)


@pytest.fixture
def cylinder() -> np.ndarray:
    return cylinder_triangles(radius=10.0, height=5.0, segments=64)


@pytest.fixture
def cube() -> np.ndarray:
    return cube_triangles(size=10.0)


@pytest.fixture
def binary_stl(tmp_path, cube) -> Path:
    path = tmp_path / "cube.stl"
    write_binary_stl(path, cube)
    return path


@pytest.fixture
def ascii_stl(tmp_path, cube) -> Path:
    path = tmp_path / "cube_ascii.stl"
    write_ascii_stl(path, cube)
    return path


@pytest.fixture
def cylinder_stl(tmp_path, cylinder) -> Path:
    path = tmp_path / "cylinder.stl"
    write_binary_stl(path, cylinder)
    return path
