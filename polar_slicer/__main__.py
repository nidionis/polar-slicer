"""Composition root and command-line interface.

This is the *only* place that instantiates concrete classes and wires them
together. Everything downstream depends on abstractions; here we choose the
implementations and inject them into :class:`~polar_slicer.pipeline.SlicerPipeline`.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from polar_slicer.config import InfillType, SlicerConfig
from polar_slicer.export.exporter import PolarGCodeExporter
from polar_slicer.geometry.profile import RaycastProfileBuilder
from polar_slicer.infill.factory import InfillStrategyFactory
from polar_slicer.mesh.loader import StlMeshLoader
from polar_slicer.perimeters.generator import ConcentricPerimeterGenerator
from polar_slicer.pipeline import SlicerPipeline
from polar_slicer.slicing.slicer import PlaneLayerSlicer


def build_config(args: argparse.Namespace) -> SlicerConfig:
    """Translate parsed CLI arguments into a :class:`SlicerConfig`."""
    return SlicerConfig(
        layer_height=args.layer_height,
        extrusion_width=args.extrusion_width,
        perimeters=args.perimeters,
        wall_thickness=args.wall_thickness,
        infill_percentage=args.infill,
        infill_type=InfillType(args.infill_type),
        angular_steps=args.angular_steps,
        center=None if args.center is None else tuple(args.center),
    )


def build_pipeline(config: SlicerConfig) -> SlicerPipeline:
    """Wire the concrete implementations into the pipeline (composition root)."""
    return SlicerPipeline(
        config=config,
        loader=StlMeshLoader(),
        slicer=PlaneLayerSlicer(),
        profile_builder=RaycastProfileBuilder(),
        perimeter_generator=ConcentricPerimeterGenerator(),
        infill_factory=InfillStrategyFactory(),
        exporter=PolarGCodeExporter(),
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="polar_slicer",
        description="Slice an STL mesh into polar (R, theta, Z) G-code.",
    )
    parser.add_argument("input", help="path to the input STL file")
    parser.add_argument("output", help="path to the output G-code file")

    parser.add_argument("--layer-height", type=float, default=0.2)
    parser.add_argument("--extrusion-width", type=float, default=0.4)
    parser.add_argument("--perimeters", type=int, default=2)
    parser.add_argument("--wall-thickness", type=float, default=1.2)
    parser.add_argument(
        "--infill", type=float, default=20.0, help="infill density in percent"
    )
    parser.add_argument(
        "--infill-type",
        choices=[t.value for t in InfillType],
        default=InfillType.GRID.value,
    )
    parser.add_argument("--angular-steps", type=int, default=180)
    parser.add_argument(
        "--center",
        type=float,
        nargs=2,
        metavar=("X", "Y"),
        default=None,
        help="rotation axis; defaults to the mesh centroid",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = build_config(args)
    pipeline = build_pipeline(config)
    gcode = pipeline.run(args.input, args.output)
    line_count = gcode.count("\n")
    print(f"Wrote {args.output} ({line_count} G-code lines).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
