"""The slicing pipeline — the orchestrator.

:class:`SlicerPipeline` coordinates the stages but performs none of their work
itself. Every collaborator is an abstraction injected through the constructor,
so the pipeline depends only on interfaces (Dependency Inversion) and can be
tested with fakes or reconfigured without edits. Concrete wiring happens at the
composition root (:mod:`polar_slicer.__main__`).
"""

from __future__ import annotations

from pathlib import Path

from polar_slicer.config import SlicerConfig
from polar_slicer.export.exporter import GCodeExporter
from polar_slicer.geometry.converter import PolarConverter
from polar_slicer.geometry.profile import RadialProfileBuilder
from polar_slicer.infill.factory import InfillStrategyFactory
from polar_slicer.mesh.loader import MeshLoader
from polar_slicer.perimeters.generator import PerimeterGenerator
from polar_slicer.slicing.slicer import LayerSlicer
from polar_slicer.toolpath.path import ToolPath


class SlicerPipeline:
    """Convert an STL file into polar G-code by composing injected stages."""

    def __init__(
        self,
        config: SlicerConfig,
        loader: MeshLoader,
        slicer: LayerSlicer,
        profile_builder: RadialProfileBuilder,
        perimeter_generator: PerimeterGenerator,
        infill_factory: InfillStrategyFactory,
        exporter: GCodeExporter,
    ) -> None:
        self._config = config
        self._loader = loader
        self._slicer = slicer
        self._profile_builder = profile_builder
        self._perimeter_generator = perimeter_generator
        self._infill_factory = infill_factory
        self._exporter = exporter

    def run(self, stl_path: str | Path, gcode_path: str | Path) -> str:
        """Slice ``stl_path`` and write the resulting G-code to ``gcode_path``.

        Returns the generated G-code string as well, to ease testing.
        """
        gcode = self.slice_to_gcode(stl_path)
        Path(gcode_path).write_text(gcode)
        return gcode

    def slice_to_gcode(self, stl_path: str | Path) -> str:
        """Slice ``stl_path`` and return the G-code string (no file written)."""
        mesh = self._loader.load(stl_path)
        layers = self._slicer.slice(mesh, self._config)

        # The rotation axis defaults to the mesh centroid unless overridden.
        center = self._config.center or mesh.xy_centroid
        converter = PolarConverter(center=center)
        infill = self._infill_factory.create(self._config)

        toolpaths: list[list[ToolPath]] = []
        for layer in layers:
            toolpaths.append(self._toolpaths_for_layer(layer, converter, infill))

        return self._exporter.export(layers, toolpaths, self._config)

    def _toolpaths_for_layer(self, layer, converter, infill) -> list[ToolPath]:
        if layer.is_empty:
            return []
        profile = self._profile_builder.build(layer, converter, self._config)
        if profile.is_empty():
            return []
        paths: list[ToolPath] = []
        paths.extend(self._perimeter_generator.generate(profile, self._config))
        paths.extend(infill.generate(profile, self._config))
        return paths
