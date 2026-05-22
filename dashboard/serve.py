"""
Mizan Dashboard Server — Serves the dashboard UI and benchmark results.

Usage:
    python dashboard/serve.py
    # Opens http://localhost:8050
"""

import http.server
import json
import os
import sys
import webbrowser
from pathlib import Path

PORT = 8050
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = Path(__file__).resolve().parent
RESULTS_DIR = PROJECT_ROOT / "benchmark_results"


class MizanHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that serves dashboard + benchmark results."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def do_GET(self):
        # Serve dashboard at root
        if self.path == "/" or self.path == "/dashboard" or self.path == "/dashboard/":
            self.path = "/dashboard/index.html"

        # API: list benchmark JSON files
        if self.path == "/api/results":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            files = []
            if RESULTS_DIR.exists():
                for f in sorted(RESULTS_DIR.glob("benchmark_*.json"), reverse=True):
                    files.append({
                        "name": f.name,
                        "path": f"/benchmark_results/{f.name}",
                        "size": f.stat().st_size,
                        "modified": f.stat().st_mtime,
                    })
            self.wfile.write(json.dumps(files).encode())
            return

        # API: get latest result
        if self.path == "/api/latest":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            files = sorted(RESULTS_DIR.glob("benchmark_*.json"), reverse=True) if RESULTS_DIR.exists() else []
            if files:
                with open(files[0], "r", encoding="utf-8") as f:
                    data = f.read()
                self.wfile.write(data.encode())
            else:
                self.wfile.write(b'{"error": "No results found"}')
            return

        # Add CORS headers for JSON files
        if self.path.endswith(".json"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            file_path = PROJECT_ROOT / self.path.lstrip("/")
            if file_path.exists():
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b'{"error": "File not found"}')
            return

        return super().do_GET()

    def log_message(self, format, *args):
        """Suppress default logging noise."""
        pass


def main():
    print(f"\n  Mizan Dashboard")
    print(f"  {'=' * 40}")
    print(f"  Server:  http://localhost:{PORT}")
    print(f"  Results: {RESULTS_DIR}")

    # Count available results
    if RESULTS_DIR.exists():
        json_files = list(RESULTS_DIR.glob("benchmark_*.json"))
        print(f"  Files:   {len(json_files)} benchmark results found")
    else:
        print(f"  Files:   No results yet — run a benchmark first")

    print(f"  {'=' * 40}")
    print(f"  Press Ctrl+C to stop\n")

    server = http.server.HTTPServer(("", PORT), MizanHandler)

    # Open browser
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Dashboard stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
