"""Inventory the pinned Semantic Evidence development corpus.

No LLM calls. No semantic labels. Verifies git-blob provenance, extracts text,
and reports source size/page metadata so later extractor design can make explicit
context-window/chunking decisions rather than silently truncating sources.
"""

from __future__ import annotations

import json

from eval.live.semantic_source_loader_v0_1 import corpus_inventory


def main() -> None:
    inventory = corpus_inventory()
    print(json.dumps({"n_sources": len(inventory), "sources": inventory}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
