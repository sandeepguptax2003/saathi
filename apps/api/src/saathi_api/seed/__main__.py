"""`python -m saathi_api.seed`: check the bundled demo fixtures load.

Demo inbox / calendar / bills are served from the JSON fixtures in this package
(see loader.py), so there is nothing to write to the database. This entrypoint
fails fast if a fixture is missing or malformed, which keeps `make seed` and CI honest.
"""

import sys

from saathi_api.seed.loader import demo_counts


def main() -> None:
    counts = demo_counts()
    sys.stdout.write("demo fixtures OK: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) + "\n")


if __name__ == "__main__":
    main()
