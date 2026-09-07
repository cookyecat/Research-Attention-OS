"""Inventory the pinned Semantic Evidence development corpus.

No LLM calls. No semantic labels. Verifies git-blob provenance, extracts text,
and reports source size/page metadata so later extractor design can make explicit
context-window/chunking decisions rather than silently truncating sources.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Direct execution via `python eval/live/...py` sets sys.path[0] to eval/live,
# not the repository root. Bootstrap the repo root before importing `eval.*`,
# matching the other eval runners.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from eval.live.semantic_source_loader_v0_1 import corpus_inventory


def main() -> None:
    inventory = corpus_inventory()
    print(json.dumps({"n_sources": len(inventory), "sources": inventory}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
