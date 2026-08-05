# polar-slicer

(prototype)

A modular 3D-printing slicer for **rotative** printing. It converts an STL mesh
into **polar** toolpaths `(R, θ, Z)` and exports G-code.

## Web app (easiest)

```bash
pip install -e ".[web]"     # installs Flask
python -m webapp            # starts a server and opens your browser
```

Load an STL, set the parameters, click **Slice**, then step through the result
layer by layer and download the G-code.

## Command line

```bash
pip install -e ".[dev]"
python examples/make_sample_stl.py            # writes examples/cylinder.stl
python -m polar_slicer examples/cylinder.stl out.gcode \
    --perimeters 2 --wall-thickness 1.5 --infill 25 --infill-type grid
```

Run `python -m polar_slicer --help` for all options, or use it as a library via
`SlicerConfig` + `build_pipeline`. Run the tests with `pytest`.
