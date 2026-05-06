"""Chinese-aware data cleaning + corpus unification.

Design choices specific to a Chinese millennium-architecture corpus:
    * jieba word segmentation (中文不靠空格切词)
    * curated bilingual stop-list (高频词 "的/了/是" + common English ones)
    * danmaku-specific noise filters (颜文字、刷屏、弹幕表情代码)
    * text-only pipeline — Pixabay rows contribute their tag-text only;
      no image download or visual vectorization is performed.
"""
from __future__ import annotations

import html
import json
import logging
import re
from pathlib import Path
from typing import Iterable, List

import jieba
import pandas as pd

from .config import PROCESSED_DIR, RAW_DIR, SEED_BUILDINGS_ZH

LOG = logging.getLogger(__name__)

WHITESPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"https?://\S+")
HTML_TAG_RE = re.compile(r"<[^>]+>")
EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U0001F600-\U0001F64F\U00002600-\U000027BF]+",
    flags=re.UNICODE,
)
REPEATED_RUN_RE = re.compile(r"(.)\1{4,}")
DANMAKU_BRACKETS_RE = re.compile(r"\[[^\]]{0,8}\]")

CHINESE_STOPWORDS = set(
    "的 了 是 在 我 有 和 就 不 人 都 一 一个 上 也 很 到 说 要 去 你 会 着 没有 看 好 自己 这 那 啊 哦 嗯 呢 吧 哈哈 哈 嘿 哇 真的 这个 那个 怎么 什么 时候 这样 这种 但是 因为 所以 而且 还有 不是 觉得 还是 一下 一些 已经".split()
)
ENGLISH_STOPWORDS = set(
    "a an the and or but if then so as is are was were be been being do does did have has had to of in on at by for with from this that these those it its".split()
)
STOPWORDS = CHINESE_STOPWORDS | ENGLISH_STOPWORDS

for _name in SEED_BUILDINGS_ZH:
    jieba.add_word(_name)


def _read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        LOG.warning("missing JSONL: %s — returning empty list", path)
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def clean_text(raw: str) -> str:
    """Strip HTML, URLs, emojis, tame run-on repetition, collapse whitespace."""
    if not raw:
        return ""
    s = html.unescape(raw)
    s = HTML_TAG_RE.sub(" ", s)
    s = URL_RE.sub(" ", s)
    s = EMOJI_RE.sub(" ", s)
    s = DANMAKU_BRACKETS_RE.sub(" ", s)
    s = REPEATED_RUN_RE.sub(r"\1\1", s)
    s = WHITESPACE_RE.sub(" ", s).strip()
    return s


def tokenize(text: str, drop_stopwords: bool = True) -> List[str]:
    """jieba-tokenize + (optional) stopword removal."""
    if not text:
        return []
    tokens = [t for t in jieba.cut(text) if t.strip()]
    if drop_stopwords:
        tokens = [t for t in tokens if t.lower() not in STOPWORDS and len(t) > 1]
    return tokens


def _row(rid: str, source: str, title: str, text: str, **extra) -> dict:
    text = clean_text(text)
    return {
        "id": rid, "source": source, "title": title,
        "text": text, "tokens": " ".join(tokenize(text)),
        "url": extra.get("url"), "license": extra.get("license"),
        "year": extra.get("year"),
    }


def _wikidata_to_rows(records: Iterable[dict]) -> List[dict]:
    out = []
    for r in records:
        text = f"{r.get('title', '')}. {r.get('extract', '')}"
        row = _row(r["id"], "wikidata", r.get("title", ""), text,
                   url=r.get("url"), license="CC BY-SA 3.0", year=r.get("year"))
        if len(row["text"]) >= 50:
            out.append(row)
    return out


def _bilibili_to_rows(records: Iterable[dict]) -> List[dict]:
    out = []
    for r in records:
        row = _row(r["id"], "bilibili", r.get("title", ""),
                   r.get("text") or r.get("title") or "",
                   url=r.get("url"), license="Bilibili ToS (research-only)")
        if len(row["text"]) >= 30:
            out.append(row)
    return out


def _pixabay_to_rows(records: Iterable[dict]) -> List[dict]:
    out = []
    for r in records:
        title = r.get("title", "")
        if not title:
            continue
        out.append(_row(r["id"], "pixabay", title, title,
                        url=r.get("url"), license=r.get("license")))
    return out


def _openai_to_rows(records: Iterable[dict]) -> List[dict]:
    out = []
    for r in records:
        text = f"{r.get('title', '')}. {r.get('text', '')}"
        row = _row(r["id"], "openai", r.get("title", ""), text,
                   license="Synthetic (gpt-4o-mini, 2026)")
        if len(row["text"]) >= 50:
            out.append(row)
    return out


def build_corpus() -> pd.DataFrame:
    """Combine all four datasets (3 scraped + OpenAI augmentation)."""
    wd = _read_jsonl(RAW_DIR / "wikidata" / "buildings.jsonl")
    pix = _read_jsonl(RAW_DIR / "pixabay" / "images.jsonl")
    bili = _read_jsonl(RAW_DIR / "bilibili" / "videos.jsonl")
    oa = _read_jsonl(RAW_DIR / "openai_synthetic_zh.jsonl")

    LOG.info("raw counts — wikidata=%d, pixabay=%d, bilibili=%d, openai=%d",
             len(wd), len(pix), len(bili), len(oa))

    rows = (_wikidata_to_rows(wd) + _bilibili_to_rows(bili)
            + _pixabay_to_rows(pix) + _openai_to_rows(oa))
    df = pd.DataFrame(rows).drop_duplicates(subset=["id"]).reset_index(drop=True)
    out = PROCESSED_DIR / "corpus.parquet"
    df.to_parquet(out, index=False)
    LOG.info("processed corpus: %d rows → %s", len(df), out)
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_corpus()
