"""Wikidata SPARQL + zh.wiki search scraper for millennium-Chinese buildings.

Two complementary retrieval philosophies are combined:

    1. SPARQL — semantic structured query against the Wikidata graph,
       restricted to subclasses of *building* (Q41176) inside China (Q148)
       with inception 2000–2010.
    2. zh.wiki ``list=search`` — full-text search over the Chinese wiki
       corpus, seeded with our ``SEED_BUILDINGS_ZH`` list. This is the
       search index, not the category tree, so hits are ranked by lexical
       relevance to each seed name.

Each candidate title is then enriched with the zh.wiki REST summary
(falling back to en.wiki if the zh page is missing). One JSON object per
line is written to ``data/raw/wikidata/buildings.jsonl``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from tqdm import tqdm

from ..config import RAW_DIR, SEED_BUILDINGS_ZH, TARGET_ITEMS_PER_DATASET
from ._http import already_scraped, make_session, polite_get

LOG = logging.getLogger(__name__)

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
ZH_REST = "https://zh.wikipedia.org/api/rest_v1/page/summary/"
EN_REST = "https://en.wikipedia.org/api/rest_v1/page/summary/"
ZH_API = "https://zh.wikipedia.org/w/api.php"

# Narrow query — narrow indexes return faster than broad ones.
SPARQL_QUERY = """
SELECT ?item ?itemLabel ?itemLabelEn ?inception ?height ?coord
WHERE {
  ?item wdt:P31/wdt:P279* wd:Q41176 ;
        wdt:P17 wd:Q148 ;
        wdt:P571 ?inception .
  FILTER(YEAR(?inception) >= 2000 && YEAR(?inception) <= 2010)
  OPTIONAL { ?item wdt:P2048 ?height . }
  OPTIONAL { ?item wdt:P625 ?coord . }
  OPTIONAL { ?item rdfs:label ?itemLabel .   FILTER(LANG(?itemLabel)   = "zh") }
  OPTIONAL { ?item rdfs:label ?itemLabelEn . FILTER(LANG(?itemLabelEn) = "en") }
}
LIMIT 500
"""


def _run_sparql(session) -> List[dict]:
    """Execute the SPARQL query (60 s timeout) → list of candidate dicts."""
    try:
        r = session.get(
            WIKIDATA_SPARQL,
            params={"query": SPARQL_QUERY, "format": "json"},
            headers={**dict(session.headers),
                     "Accept": "application/sparql-results+json"},
            timeout=60,
        )
        r.raise_for_status()
        payload = r.json()
    except Exception as exc:  # noqa: BLE001
        LOG.warning("SPARQL failed (%s) — relying on seed + zh.wiki search", exc)
        return []

    rows: list[dict] = []
    for b in payload["results"]["bindings"]:
        qid = b.get("item", {}).get("value", "").rsplit("/", 1)[-1]
        if not qid:
            continue
        try:
            year = int(b["inception"]["value"][:4])
        except (KeyError, ValueError):
            continue
        rows.append({
            "qid": qid,
            "title_zh": b.get("itemLabel", {}).get("value"),
            "title_en": b.get("itemLabelEn", {}).get("value"),
            "year": year,
        })
    LOG.info("SPARQL: %d candidates", len(rows))
    return rows


def _zh_search(session, keyword: str, limit: int = 3) -> List[str]:
    """Full-text search the Chinese wiki for ``keyword``; return page titles."""
    try:
        data = polite_get(
            session, ZH_API,
            params={"action": "query", "format": "json", "list": "search",
                    "srsearch": keyword, "srlimit": limit, "srnamespace": 0},
            sleep=0.2,
        ).json()
    except Exception as exc:  # noqa: BLE001
        LOG.debug("zh-search miss for %s: %s", keyword, exc)
        return []
    return [hit["title"] for hit in data.get("query", {}).get("search", [])]


def _fetch_summary(session, title: str, lang: str) -> str | None:
    base = ZH_REST if lang == "zh" else EN_REST
    safe = title.replace(" ", "_")
    try:
        data = polite_get(session, base + safe, sleep=0.1).json()
    except Exception:
        return None
    extract = (data.get("extract") or "").strip()
    return extract or None


def scrape_wikidata_sparql(out_path: Path | None = None,
                           target: int = TARGET_ITEMS_PER_DATASET) -> Path:
    """Run SPARQL + zh.wiki enrichment, persist as JSONL."""
    out_path = out_path or (RAW_DIR / "wikidata" / "buildings.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if already_scraped(out_path, target):
        LOG.info("Wikidata: %s already has ≥%d rows — skipping.", out_path, target)
        return out_path

    session = make_session()
    candidates: list[dict] = _run_sparql(session)

    seen_titles: set[str] = set(SEED_BUILDINGS_ZH)
    for name in SEED_BUILDINGS_ZH:
        candidates.append({"qid": None, "title_zh": name, "title_en": None})

    if len(candidates) < target * 1.5:
        LOG.info("expanding via zh.wiki full-text search (%d seeds × 3 hits)",
                 len(SEED_BUILDINGS_ZH))
        for si, seed in enumerate(SEED_BUILDINGS_ZH, 1):
            for hit in _zh_search(session, seed):
                if hit not in seen_titles:
                    seen_titles.add(hit)
                    candidates.append(
                        {"qid": None, "title_zh": hit, "title_en": None}
                    )
            if si % 10 == 0:
                LOG.info("  zh-search progress: %d/%d seeds, %d candidates so far",
                         si, len(SEED_BUILDINGS_ZH), len(candidates))

    written = 0
    keys: set[str] = set()
    with out_path.open("w", encoding="utf-8") as fh:
        bar = tqdm(total=target, desc="Wikidata")
        for cand in candidates:
            if written >= target:
                break
            zh = cand.get("title_zh")
            en = cand.get("title_en")
            qid = cand.get("qid")
            key = qid or zh or en
            if not key or key in keys:
                continue
            keys.add(key)

            extract = lang = None
            if zh:
                extract, lang = _fetch_summary(session, zh, "zh"), "zh"
            if not extract and en:
                extract, lang = _fetch_summary(session, en, "en"), "en"
            if not extract or len(extract) < 60:
                continue
            if written and written % 25 == 0:
                LOG.info("  wikidata progress: %d/%d rows written", written, target)

            url_title = (zh if lang == "zh" else en) or zh
            fh.write(json.dumps({
                "id": f"wd-{qid or 'seed-' + str(written)}",
                "qid": qid,
                "title": zh or en,
                "title_en": en,
                "year": cand.get("year"),
                "extract": extract,
                "extract_lang": lang,
                "url": f"https://{lang}.wikipedia.org/wiki/{url_title.replace(' ', '_')}",
                "source": "wikidata",
            }, ensure_ascii=False) + "\n")
            written += 1
            bar.update(1)
        bar.close()

    LOG.info("Wikidata: wrote %d rows → %s", written, out_path)
    return out_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scrape_wikidata_sparql()
