"""Container HEALTHCHECK probe: `python -m saathi_api.healthcheck` (slim image has no curl)."""

from __future__ import annotations

import os
import sys
import urllib.request


def main() -> int:
    port = os.getenv("PORT", "8000")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=4) as resp:
            return 0 if resp.status == 200 else 1
    except OSError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
