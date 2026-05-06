"""Bilibili scraper — Chinese video search + danmaku (live-comment) harvest.

Danmaku are micro-comments (avg < 15 Chinese chars) overlaid on the video
timeline — a distinctive Chinese-social-media surface form. Two phases:
first search the seed-building keywords for video metadata (BVID + CID),
then pull every video's danmaku XML stream. Both endpoints are read-only
and require no OAuth. Output: one JSON object per line.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Iterable, List
from xml.etree import ElementTree

from tqdm import tqdm

from ..config import (
    BILIBILI_DANMAKU_ENDPOINT,
    BILIBILI_SEARCH_ENDPOINT,
    RAW_DIR,
    SEED_BUILDINGS_ZH,
    TARGET_ITEMS_PER_DATASET,
)
from ._http import already_scraped, make_session, polite_get

LOG = logging.getLogger(__name__)

# Bilibili wraps highlight terms in <em> tags inside the title field —
# strip them before persistence to keep the JSONL clean.
HIGHLIGHT_RE = re.compile(r"<[^>]+>")

REFERER_HEADERS = {"Referer": "https://search.bilibili.com"}


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    return HIGHLIGHT_RE.sub("", text).strip()


def _search_videos(session, keyword: str, page: int = 1, page_size: int = 30):
    """One page of Bilibili search results for ``keyword``."""
    params = {
        "search_type": "video",
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
        "order": "totalrank",
    }
    payload = polite_get(
        session,
        BILIBILI_SEARCH_ENDPOINT,
        params=params,
        headers=REFERER_HEADERS,
        sleep=0.7,
    ).json()

    if payload.get("code") != 0:
        LOG.debug("Bilibili search code=%s msg=%s", payload.get("code"),
                  payload.get("message"))
        return []
    return payload.get("data", {}).get("result") or []


def _fetch_video_meta(session, bvid: str) -> dict | None:
    """Use the canonical view API to recover (cid, aid, title, description, tag)."""
    url = "https://api.bilibili.com/x/web-interface/view"
    try:
        payload = polite_get(
            session, url, params={"bvid": bvid},
            headers=REFERER_HEADERS, sleep=0.4,
        ).json()
    except Exception as exc:  # noqa: BLE001
        LOG.debug("view-api failed for %s: %s", bvid, exc)
        return None
    if payload.get("code") != 0:
        return None
    return payload.get("data") or {}


def _fetch_danmaku(session, cid: int) -> List[str]:
    """Fetch the XML danmaku stream and return a list of comment strings."""
    if not cid:
        return []
    try:
        response = polite_get(
            session,
            BILIBILI_DANMAKU_ENDPOINT.format(cid=cid),
            headers=REFERER_HEADERS,
            sleep=0.5,
        )
    except Exception as exc:  # noqa: BLE001
        LOG.debug("danmaku miss cid=%s: %s", cid, exc)
        return []

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError:
        return []

    comments = []
    for d in root.findall("d"):
        text = (d.text or "").strip()
        if 1 <= len(text) <= 80:
            comments.append(text)
    return comments


def scrape_bilibili(
    out_path: Path | None = None,
    target: int = TARGET_ITEMS_PER_DATASET,
    keywords: Iterable[str] = SEED_BUILDINGS_ZH,
    pages_per_keyword: int = 4,
) -> Path:
    """Search seed keywords + harvest video meta + danmaku → JSONL."""
    out_path = out_path or (RAW_DIR / "bilibili" / "videos.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if already_scraped(out_path, target):
        LOG.info("Bilibili: %s already has ≥%d rows — skipping.", out_path, target)
        return out_path

    session = make_session()
    seen_bvid: set[str] = set()
    written = 0

    with out_path.open("w", encoding="utf-8") as fh:
        bar = tqdm(total=target, desc="Bilibili")
        for keyword in keywords:
            if written >= target:
                break
            for page in range(1, pages_per_keyword + 1):
                if written >= target:
                    break
                try:
                    results = _search_videos(session, keyword, page=page)
                except Exception as exc:  # noqa: BLE001
                    LOG.warning("search failed (%r p%d): %s", keyword, page, exc)
                    break
                if not results:
                    break

                for hit in results:
                    if written >= target:
                        break
                    bvid = hit.get("bvid")
                    if not bvid or bvid in seen_bvid:
                        continue
                    seen_bvid.add(bvid)

                    meta = _fetch_video_meta(session, bvid) or {}
                    cid = meta.get("cid")
                    danmaku = _fetch_danmaku(session, cid) if cid else []

                    title = _strip_html(hit.get("title")) or meta.get("title", "")
                    description = (
                        _strip_html(hit.get("description")) or meta.get("desc", "")
                    )
                    tag = hit.get("tag") or ""

                    text = " ".join(
                        [t for t in (title, description, tag) if t]
                        + danmaku[:60]  # cap to avoid one video dominating the corpus
                    )

                    fh.write(
                        json.dumps(
                            {
                                "id": f"bili-{bvid}",
                                "bvid": bvid,
                                "keyword": keyword,
                                "title": title,
                                "description": description,
                                "tag": tag,
                                "duration": hit.get("duration"),
                                "play": hit.get("play"),
                                "video_review": hit.get("video_review"),
                                "danmaku_count": len(danmaku),
                                "danmaku": danmaku[:60],
                                "text": text,
                                "url": f"https://www.bilibili.com/video/{bvid}",
                                "source": "bilibili",
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    written += 1
                    bar.update(1)
        bar.close()

    LOG.info("Bilibili: wrote %d rows → %s", written, out_path)
    return out_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scrape_bilibili()
