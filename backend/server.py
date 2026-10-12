"""Start the Learn4All API server.

    python server.py                    # http://127.0.0.1:8000
    python server.py --port 9000 --host 0.0.0.0
    python server.py --reset            # wipe DB and reload sample data
    python server.py --no-seed          # start with an empty database

Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import logging
import sys

from learn4all.api import create_server
from learn4all.config import DEFAULT_DB_PATH, DEFAULT_HOST, DEFAULT_PORT
from learn4all.database import Database
from learn4all.seed import seed_demo_data
from learn4all.services import Learn4AllService


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Learn4All REST API server")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"bind address (default {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port (default {DEFAULT_PORT})")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite database file")
    parser.add_argument("--reset", action="store_true", help="drop all data and reload the sample data")
    parser.add_argument("--no-seed", action="store_true", help="do not load sample data into an empty DB")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    db = Database(args.db)
    service = Learn4AllService(db)
    if args.reset:
        db.drop_all()
    db.initialize()
    if db.is_empty() and not args.no_seed:
        summary = seed_demo_data(service)
        logging.info("Loaded sample data: %s", summary)

    server = create_server(service, args.host, args.port)
    print(f"\n  Learn4All API running at http://{args.host}:{args.port}")
    print(f"  Docs:     http://{args.host}:{args.port}/api/docs")
    print(f"  OpenAPI:  http://{args.host}:{args.port}/api/openapi.json")
    print(f"  Database: {args.db}\n  Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
