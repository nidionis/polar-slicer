"""Layer slicing: turning a 3D mesh into stacked 2D cross-sections."""

from polar_slicer.slicing.layer import Contour, Layer
from polar_slicer.slicing.slicer import LayerSlicer, PlaneLayerSlicer

__all__ = ["Contour", "Layer", "LayerSlicer", "PlaneLayerSlicer"]
