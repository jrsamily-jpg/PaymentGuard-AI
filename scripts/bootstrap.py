"""Usage: python -m scripts.bootstrap [--rows 100000]. Existing data is preserved."""

import argparse
import json
from app.services.pipeline import build

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=100000)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    print(json.dumps(build(args.rows, args.seed), indent=2))
