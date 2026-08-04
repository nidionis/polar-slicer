"""Flask application factory and routes.

Endpoints
---------
``GET  /``            -> the single-page UI.
``POST /api/slice``   -> multipart STL upload + form parameters; returns JSON
                         ``{stats, gcode, layers}`` where ``layers`` holds the
                         Cartesian segments the viewer draws.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from polar_slicer.__main__ import build_pipeline
from polar_slicer.config import InfillType, SlicerConfig
from polar_slicer.gcode_reader import PolarGCodeReader

_STATIC = Path(__file__).with_name("static")

# Guard rails so a bad upload can't lock up the process.
_MAX_UPLOAD_BYTES = 64 * 1024 * 1024  # 64 MB


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = _MAX_UPLOAD_BYTES

    @app.get("/")
    def index():
        return send_from_directory(_STATIC, "index.html")

    @app.get("/static/<path:name>")
    def static_files(name: str):
        return send_from_directory(_STATIC, name)

    @app.post("/api/slice")
    def slice_stl():
        upload = request.files.get("stl")
        if upload is None or upload.filename == "":
            return jsonify(error="No STL file uploaded."), 400

        try:
            config = _config_from_form(request.form)
        except (ValueError, TypeError) as exc:
            return jsonify(error=f"Invalid parameters: {exc}"), 400

        with tempfile.NamedTemporaryFile(suffix=".stl", delete=True) as tmp:
            upload.save(tmp.name)
            try:
                gcode = build_pipeline(config).slice_to_gcode(tmp.name)
            except Exception as exc:  # noqa: BLE001 - surface any slicing error
                return jsonify(error=f"Slicing failed: {exc}"), 400

        layers = _read_layers(gcode, config)
        return jsonify(
            gcode=gcode,
            layers=[layer.as_dict() for layer in layers],
            stats=_stats(layers, gcode),
        )

    return app


def _config_from_form(form) -> SlicerConfig:
    """Build a validated :class:`SlicerConfig` from posted form fields."""
    return SlicerConfig(
        layer_height=float(form.get("layer_height", 0.2)),
        extrusion_width=float(form.get("extrusion_width", 0.4)),
        perimeters=int(form.get("perimeters", 2)),
        wall_thickness=float(form.get("wall_thickness", 1.2)),
        infill_percentage=float(form.get("infill_percentage", 20.0)),
        infill_type=InfillType(form.get("infill_type", "grid")),
        angular_steps=int(form.get("angular_steps", 180)),
    )


def _read_layers(gcode: str, config: SlicerConfig):
    reader = PolarGCodeReader(
        radial_axis=config.radial_axis,
        angular_axis=config.angular_axis,
        z_axis=config.z_axis,
        angular_in_degrees=config.angular_in_degrees,
    )
    return reader.read(gcode)


def _stats(layers, gcode: str) -> dict:
    segments = sum(len(layer.segments) for layer in layers)
    return {
        "layer_count": len(layers),
        "segment_count": segments,
        "gcode_lines": gcode.count("\n"),
    }
