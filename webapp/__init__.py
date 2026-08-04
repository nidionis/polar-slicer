"""Web front-end for polar-slicer.

A thin Flask layer on top of the slicing pipeline: it accepts an STL upload plus
process parameters, runs :class:`~polar_slicer.pipeline.SlicerPipeline`, and
returns the generated G-code together with per-layer geometry for the in-browser
viewer.
"""

from webapp.server import create_app

__all__ = ["create_app"]
