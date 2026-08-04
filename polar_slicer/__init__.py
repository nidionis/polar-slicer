"""Polar Slicer.

A modular 3D slicer for rotative 3D printing. It converts an STL mesh into
polar toolpaths ``(R, theta, Z)`` and exports G-code.

The package is designed around the SOLID principles: every processing stage
(mesh loading, coordinate conversion, layer slicing, perimeter generation,
infill strategies and G-code export) lives behind a small abstract interface so
that concrete implementations can be swapped and injected freely.

The recommended entry point is :class:`polar_slicer.pipeline.SlicerPipeline`,
wired together at a composition root (see :mod:`polar_slicer.__main__`).
"""

from polar_slicer.config import InfillType, SlicerConfig

__all__ = ["InfillType", "SlicerConfig"]

__version__ = "0.1.0"
