#!/usr/bin/env python3
"""Simple HTTP server for the research engine UI.

Serves from the project root so the UI can access ../data/ui/*.json
via relative paths. Includes CORS headers and cache-busting.

Usage:
    python scripts/serve_ui.py [--port 8080]
"""

import argparse
import http.server
import os
import functools


class CORSHandler(http.server.SimpleHTTPRequestHandler):
    """Handler with CORS and no-cache headers for live data."""

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, format, *args):
        # Quieter logging — only log non-200 or non-JSON requests
        if args and '200' not in str(args[1:]):
            super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description='Serve research engine UI')
    parser.add_argument('--port', type=int, default=8080, help='Port (default: 8080)')
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    handler = functools.partial(CORSHandler, directory=project_root)
    server = http.server.HTTPServer(('localhost', args.port), handler)

    print(f"Research Engine UI: http://localhost:{args.port}/ui/")
    print(f"Serving from: {project_root}")
    print("Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == '__main__':
    main()
