"""Launch the polar-slicer web app and open it in the browser.

Run it with::

    python -m webapp

It starts a local server and pops open your default browser at the UI. Use
``--no-browser`` for headless runs, or ``--port`` to change the port.
"""

from __future__ import annotations

import argparse
import threading
import webbrowser

from webapp.server import create_app


def main() -> int:
    parser = argparse.ArgumentParser(prog="polar-slicer-web")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument(
        "--no-browser", action="store_true", help="do not open a browser window"
    )
    args = parser.parse_args()

    url = f"http://{args.host}:{args.port}/"
    if not args.no_browser:
        # Open the browser shortly after the server starts serving.
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    print(f"Polar Slicer running at {url}  (Ctrl+C to stop)")
    app = create_app()
    # threaded=True so the browser's asset requests don't block slicing.
    app.run(host=args.host, port=args.port, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
