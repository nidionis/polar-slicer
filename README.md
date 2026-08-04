# polar-slicer

A modular 3D-printing slicer optimized for **rotative** printing. It converts an
STL mesh into **polar** toolpaths `(R, θ, Z)` and exports G-code.

The codebase is built around the **SOLID** principles: every processing stage
lives behind a small abstract interface, so implementations can be swapped and
injected freely. Nothing is hard-coded — all process parameters come from a
single, centralized configuration object.

## Features

- **STL loading** — self-contained binary *and* ASCII STL parser (no third-party
  STL dependency; only `numpy`).
- **Polar conversion** — each layer's cross-section is described as a radial
  profile `R(θ)` about the part's central axis.
- **Configurable perimeters** — a parametrable number of concentric contour
  lines per layer.
- **Infill inside the shell only** — infill is generated strictly *inside* the
  configured wall thickness. Two selectable strategies:
  - **Solid** (`solid`, *Plein*) — touching concentric rings that fill the
    interior completely.
  - **Grid** (`grid`, *Grille*) — concentric rings spaced by the infill density,
    crossed by radial spokes; both the spacing and spoke count scale with the
    infill percentage.
- **Polar G-code export** — configurable axis letters for radius / rotation /
  height, continuous (unwrapped) rotary motion, and extrusion computed from true
  Cartesian path length.

## Architecture

Each module has a single responsibility and is defined behind an abstract base
class so concrete implementations are injected at a composition root.

```
polar_slicer/
  config.py            SlicerConfig (frozen), InfillType — the one config surface
  geometry/
    points.py          CartesianPoint, PolarPoint value objects
    converter.py       CoordinateConverter → PolarConverter
    profile.py         RadialProfileBuilder → RaycastProfileBuilder (Cartesian→polar)
  mesh/
    model.py           Mesh (triangle soup + bounds)
    loader.py          MeshLoader → StlMeshLoader (binary + ASCII)
  slicing/
    layer.py           Contour, Layer
    slicer.py          LayerSlicer → PlaneLayerSlicer (plane intersect + stitch)
  perimeters/
    generator.py       PerimeterGenerator → ConcentricPerimeterGenerator
  infill/
    strategy.py        InfillStrategy (interior-only base)
    solid.py           SolidInfill
    grid.py            GridInfill
    factory.py         InfillStrategyFactory (config → strategy; extension point)
  toolpath/
    path.py            ToolPath, PathRole
  export/
    exporter.py        GCodeExporter → PolarGCodeExporter
  gcode_reader.py      PolarGCodeReader (G-code → Cartesian layers, for the viewer)
  pipeline.py          SlicerPipeline — orchestrator (all collaborators injected)
  __main__.py          composition root + CLI (the only place concretes are built)

webapp/                browser front-end (Flask)
  server.py            create_app + /api/slice (STL upload → gcode + layer JSON)
  __main__.py          `python -m webapp` launcher (opens the browser)
  static/              index.html, app.js, style.css (canvas layer viewer)
```

**How SOLID maps here**

- **S** — every module above changes for exactly one reason.
- **O** — a new infill pattern is a new `InfillStrategy` registered in the
  factory; a new file format is a new `MeshLoader`; a new output is a new
  `GCodeExporter`. Existing code is untouched.
- **L** — every concrete honours its ABC contract; the pipeline uses only the
  abstractions.
- **I** — interfaces are minimal (`load`, `slice`, `build`, `generate`, `export`).
- **D** — `SlicerPipeline` depends on abstractions; concretes are injected in
  `__main__` (the composition root).

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Web app (easiest)

A small browser UI lets you load an STL, slice it with your parameters, and step
through the result layer by layer.

```bash
pip install -e ".[web]"     # or: pip install flask
python -m webapp            # starts a local server and opens your browser
```

Then, in the page:

1. **Choose an STL file** and set the parameters (layer height, perimeters, wall
   thickness, infill % and type, angular steps).
2. Click **Slice** — the model is converted to polar G-code on the server.
3. **Preview by layer** with the slider / play button; toggle *ghost* to see the
   layers below. Click **Download G-code** to save the result.

Extrusions are drawn in blue (perimeters) and orange (infill); travel moves are
faint. The preview renders the *actual generated G-code* (parsed back via
`polar_slicer.gcode_reader.PolarGCodeReader`), so it reflects exactly what the
file contains.

Options: `python -m webapp --port 8000 --no-browser`.

## Usage (command line)

```bash
# Generate a demo cylinder STL
python examples/make_sample_stl.py

# Slice it into polar G-code
python -m polar_slicer examples/cylinder.stl out.gcode \
    --layer-height 1.0 \
    --perimeters 2 \
    --wall-thickness 1.5 \
    --infill 25 \
    --infill-type grid \
    --angular-steps 90
```

As a library (dependency injection at the composition root):

```python
from polar_slicer.config import InfillType, SlicerConfig
from polar_slicer.__main__ import build_pipeline

config = SlicerConfig(
    layer_height=0.2,
    perimeters=3,
    wall_thickness=1.2,
    infill_percentage=20.0,
    infill_type=InfillType.SOLID,
)
pipeline = build_pipeline(config)
gcode = pipeline.run("model.stl", "model.gcode")
```

To wire your own implementations, construct `SlicerPipeline` directly with any
objects satisfying the module interfaces.

## Configuration

All parameters live in `SlicerConfig` (see `polar_slicer/config.py`):

| Parameter            | Meaning                                             |
| -------------------- | --------------------------------------------------- |
| `layer_height`       | Vertical step between layers (mm)                   |
| `extrusion_width`    | Extruded line width; drives ring/perimeter spacing  |
| `perimeters`         | Number of contour lines per layer                   |
| `wall_thickness`     | Radial shell thickness; infill stays inside it      |
| `infill_percentage`  | Infill density (0–100)                              |
| `infill_type`        | `InfillType.SOLID` or `InfillType.GRID`             |
| `angular_steps`      | Angular samples per layer (polar resolution)        |
| `center`             | Rotation axis `(x, y)`; defaults to mesh centroid   |
| `radial/angular/z_axis` | G-code axis letters                              |
| `angular_in_degrees` | Emit the rotary axis in degrees vs radians          |
| `flow`, `feedrate`   | Extrusion multiplier and movement feedrate          |

## G-code output

Coordinates are polar. The header documents the axis mapping, e.g.:

```
; coordinates are polar (R, theta, Z)
;   radius  -> X
;   angle   -> A (degrees)
;   height  -> Z
```

Angles are unwrapped along each path so the rotary axis turns continuously
instead of snapping across the ±180° seam.

## Testing

```bash
pytest
```

## Assumptions (v1)

- Perimeters and infill use **radial** (polar) offsetting — exact for sections
  that are star-convex about the central axis. Complex concave cross-sections are
  a future enhancement, addable as new `PerimeterGenerator` / `InfillStrategy`
  implementations without touching existing code.
- G-code targets a generic polar/rotative motion system with configurable axis
  letters.
```
