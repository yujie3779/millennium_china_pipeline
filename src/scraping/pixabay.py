"""Pixabay metadata scraper — keyword-driven REST API, metadata only.

A keyword-first retrieval philosophy (no taxonomy descent). We persist
tags + photographer + URL — the photo binary itself is *not* downloaded;
this pipeline consumes only the captions/tags as text, not pixel data.

Setup
-----
Free key at https://pixabay.com/api/docs/ → write to ``.pixabay_key``
(gitignored) at the project root, or set ``PIXABAY_API_KEY``.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Iterable

from tqdm import tqdm

from ..config import (
    PIXABAY_ENDPOINT, PIXABAY_PER_PAGE,
    RAW_DIR, SEED_BUILDINGS_EN, TARGET_ITEMS_PER_DATASET,
)
from ._http import already_scraped, make_session, polite_get

LOG = logging.getLogger(__name__)

SUPPLEMENTARY_KEYWORDS = [
    "Beijing 2008 architecture", "Shanghai skyline 2010",
    "Guangzhou skyline night", "Chinese stadium", "Chinese skyscraper",
    "Shanghai Pudong", "Beijing CBD", "Shenzhen skyline",
]


def _load_api_key() -> str:
    key = os.environ.get("PIXABAY_API_KEY")
    if key:
        return key
    for cand in (Path(".pixabay_key"),
                 Path(__file__).resolve().parents[2] / ".pixabay_key"):
        if cand.exists():
            return cand.read_text(encoding="utf-8").strip()
    raise RuntimeError(
        "Pixabay key not found — set PIXABAY_API_KEY or write `.pixabay_key`."
    )


def scrape_pixabay(
    out_path: Path | None = None,
    target: int = TARGET_ITEMS_PER_DATASET,
    extra_keywords: Iterable[str] = SUPPLEMENTARY_KEYWORDS,
) -> Path:
    """Run keyword-driven search → JSONL of metadata (no image download)."""
    out_path = out_path or (RAW_DIR / "pixabay" / "images.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if already_scraped(out_path, target):
        LOG.info("Pixabay: %s already has ≥%d rows — skipping.", out_path, target)
        return out_path

    key = _load_api_key()
    session = make_session()
    queries = list(SEED_BUILDINGS_EN) + list(extra_keywords)

    seen: set[str] = set()
    written = 0
    with out_path.open("w", encoding="utf-8") as fh:
        bar = tqdm(total=target, desc="Pixabay")
        for query in queries:
            if written >= target:
                break
            for page in range(1, 6):
                if written >= target:
                    break
                try:
                    payload = polite_get(
                        session, PIXABAY_ENDPOINT,
                        params={"key": key, "q": query, "image_type": "photo",
                                "per_page": PIXABAY_PER_PAGE, "page": page,
                                "safesearch": "true", "lang": "en"},
                        sleep=0.4,
                    ).json()
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("Pixabay search %r p%d failed: %s", query, page, exc)
                    break

                hits = payload.get("hits", [])
                if not hits:
                    break
                for hit in hits:
                    if written >= target:
                        break
                    pid = str(hit.get("id"))
                    if not pid or pid in seen:
                        continue
                    seen.add(pid)
                    fh.write(json.dumps({
                        "id": f"pixabay-{pid}",
                        "title": hit.get("tags", ""),
                        "query": query,
                        "url": hit.get("pageURL"),
                        "image_url": hit.get("largeImageURL") or hit.get("webformatURL"),
                        "user": hit.get("user"),
                        "views": hit.get("views"),
                        "license": "Pixabay License (CC0-like)",
                        "source": "pixabay",
                    }, ensure_ascii=False) + "\n")
                    written += 1
                    bar.update(1)
        bar.close()

    LOG.info("Pixabay: wrote %d rows → %s", written, out_path)
    return out_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scrape_pixabay()
