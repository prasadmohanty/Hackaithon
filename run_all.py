"""Convenience launcher: starts the API and the (separate) frontend together.

    python run_all.py              # API on :8000, frontend on :5500, opens the browser
    python run_all.py --no-browser

The two parts remain independent processes; you can also start them on their own:
    python backend/server.py
    python -m http.server 5500 --directory frontend
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Learn4All API + frontend")
    parser.add_argument("--api-port", type=int, default=8000)
    parser.add_argument("--web-port", type=int, default=5500)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    api = subprocess.Popen([sys.executable, str(ROOT / "backend" / "server.py"), "--port", str(args.api_port)])
    web = subprocess.Popen([sys.executable, "-m", "http.server", str(args.web_port), "--bind", "127.0.0.1",
                            "--directory", str(ROOT / "frontend")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{args.web_port}/"
    if args.api_port != 8000:
        url += f"?api=http://127.0.0.1:{args.api_port}"
    print(f"\n  Frontend: {url}\n  API:      http://127.0.0.1:{args.api_port}/api\n  Ctrl+C to stop both.\n")
    time.sleep(1.2)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        while api.poll() is None and web.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for proc in (api, web):
            proc.terminate()
        for proc in (api, web):
            proc.wait(timeout=5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
