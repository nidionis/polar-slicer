"""Mesh loaders.

:class:`MeshLoader` is the abstraction the pipeline depends on. The bundled
:class:`StlMeshLoader` reads both binary and ASCII STL files without any
third-party dependency, producing a :class:`~polar_slicer.mesh.model.Mesh`.
"""

from __future__ import annotations

import re
import struct
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np

from polar_slicer.mesh.model import Mesh

# Binary STL layout: 80-byte header, uint32 triangle count, then per triangle
# 12 float32 (normal + 3 vertices) + a uint16 attribute count => 50 bytes.
_BINARY_HEADER = 80
_BINARY_COUNT = 4
_BINARY_TRIANGLE = 50


class MeshLoader(ABC):
    """Interface loading a mesh from a file path."""

    @abstractmethod
    def load(self, path: str | Path) -> Mesh:
        """Load and return a :class:`Mesh` from ``path``."""


class StlMeshLoader(MeshLoader):
    """Load triangle meshes from ASCII or binary STL files."""

    def load(self, path: str | Path) -> Mesh:
        path = Path(path)
        data = path.read_bytes()
        if self._is_ascii(data):
            triangles = self._parse_ascii(data.decode("ascii", errors="replace"))
        else:
            triangles = self._parse_binary(data)
        return Mesh(triangles)

    @staticmethod
    def _is_ascii(data: bytes) -> bool:
        """Decide ASCII vs binary robustly.

        An ASCII STL starts with ``solid`` and, unlike binary, contains the
        keyword ``facet``. Some binary files also start with ``solid`` in their
        header, so we additionally require the byte length to *not* match the
        exact binary layout before trusting the ``facet`` heuristic.
        """
        stripped = data.lstrip()
        if not stripped[:5].lower() == b"solid":
            return False
        # If the size matches the binary layout exactly, treat it as binary.
        if len(data) >= _BINARY_HEADER + _BINARY_COUNT:
            (count,) = struct.unpack_from("<I", data, _BINARY_HEADER)
            expected = _BINARY_HEADER + _BINARY_COUNT + count * _BINARY_TRIANGLE
            if expected == len(data):
                return False
        return b"facet" in data[:2048].lower()

    @staticmethod
    def _parse_binary(data: bytes) -> np.ndarray:
        if len(data) < _BINARY_HEADER + _BINARY_COUNT:
            raise ValueError("truncated binary STL: missing header/count")
        (count,) = struct.unpack_from("<I", data, _BINARY_HEADER)
        expected = _BINARY_HEADER + _BINARY_COUNT + count * _BINARY_TRIANGLE
        if len(data) < expected:
            raise ValueError(
                f"truncated binary STL: expected {expected} bytes, got {len(data)}"
            )
        offset = _BINARY_HEADER + _BINARY_COUNT
        # Read the per-triangle records as a structured array, then drop the
        # normal (first 3 floats) and the attribute count, keeping the 9 vertex
        # floats reshaped to (count, 3, 3).
        record = np.dtype(
            [("normal", "<f4", 3), ("verts", "<f4", (3, 3)), ("attr", "<u2")]
        )
        records = np.frombuffer(data, dtype=record, count=count, offset=offset)
        return records["verts"].astype(np.float64)

    @staticmethod
    def _parse_ascii(text: str) -> np.ndarray:
        # Grab every "vertex x y z" line in document order.
        floats = re.findall(
            r"vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)", text
        )
        if not floats:
            return np.empty((0, 3, 3), dtype=np.float64)
        verts = np.array(floats, dtype=np.float64)
        if verts.shape[0] % 3 != 0:
            raise ValueError(
                "malformed ASCII STL: vertex count is not a multiple of 3"
            )
        return verts.reshape(-1, 3, 3)
