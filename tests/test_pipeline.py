"""End-to-end pipeline tests wiring every concrete stage together."""

from __future__ import annotations

import re

from polar_slicer.__main__ import build_pipeline, main
from polar_slicer.config import InfillType, SlicerConfig


def _pipeline(**overrides):
    config = SlicerConfig(**overrides)
    return build_pipeline(config), config


def test_end_to_end_produces_gcode(cylinder_stl):
    pipeline, _ = _pipeline(
        layer_height=1.0, perimeters=2, wall_thickness=1.5,
        infill_percentage=25.0, infill_type=InfillType.GRID, angular_steps=90,
    )
    gcode = pipeline.slice_to_gcode(cylinder_stl)
    assert gcode.strip()
    # 5 layers for a height-5 cylinder at 1mm layers.
    assert gcode.count("; layer ") == 5
    assert "G1" in gcode


def test_solid_and_grid_both_run(cylinder_stl):
    for kind in (InfillType.SOLID, InfillType.GRID):
        pipeline, _ = _pipeline(
            layer_height=1.0, infill_type=kind, wall_thickness=1.5,
            infill_percentage=40.0, angular_steps=60,
        )
        gcode = pipeline.slice_to_gcode(cylinder_stl)
        assert "infill" in gcode


def test_run_writes_file(cylinder_stl, tmp_path):
    pipeline, _ = _pipeline(layer_height=1.0, angular_steps=60)
    out = tmp_path / "out.gcode"
    pipeline.run(cylinder_stl, out)
    assert out.exists() and out.stat().st_size > 0


def test_cli_main(cylinder_stl, tmp_path, capsys):
    out = tmp_path / "cli.gcode"
    rc = main([
        str(cylinder_stl), str(out),
        "--layer-height", "1.0", "--angular-steps", "60",
        "--infill-type", "solid", "--infill", "30",
    ])
    assert rc == 0
    assert out.exists()
    printed = capsys.readouterr().out
    assert "Wrote" in printed


def test_all_coordinate_lines_have_expected_axes(cylinder_stl):
    pipeline, config = _pipeline(layer_height=1.0, angular_steps=60)
    gcode = pipeline.slice_to_gcode(cylinder_stl)
    for ln in gcode.splitlines():
        if ln.startswith(("G0", "G1")):
            assert re.search(rf"\b{config.radial_axis}[-0-9.]+", ln)
            assert re.search(rf"\b{config.angular_axis}[-0-9.]+", ln)
            assert re.search(rf"\b{config.z_axis}[-0-9.]+", ln)
