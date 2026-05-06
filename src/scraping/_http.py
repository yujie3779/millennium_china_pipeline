"""Shared HTTP session + helpers for the demo131 scrapers.

Per-request header override (Pixabay vs Bilibili expect different
Accept/Referer flavours), and a tolerant ``count_jsonl`` line counter.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Mapping, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

LOG = logging.getLogger(__name__)

USER_AGENT = (
    "DigitalSkillsFinalProject-demo131/0.1 "
    "(Mozilla/5.0; educational; contact: student@example.edu)"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
}


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def already_scraped(path: Path, target: int) -> bool:
    return count_jsonl(path) >= target


def make_session(timeout: float = 30.0) -> requests.Session:
    """Build a polite requests Session with retries + Chinese-friendly UA."""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    retry = Retry(
        total=5,
        connect=3,
        read=3,
        backoff_factor=1.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=8, pool_maxsize=8)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.request_timeout = timeout  # type: ignore[attr-defined]
    return session


def polite_get(
    session: requests.Session,
    url: str,
    *,
    params: Optional[dict] = None,
    sleep: float = 0.4,
    headers: Optional[Mapping[str, str]] = None,
) -> requests.Response:
    """GET with a built-in inter-request sleep + per-call header override."""
    timeout = getattr(session, "request_timeout", 30.0)
    merged = dict(session.headers)
    if headers:
        merged.update(headers)
    response = session.get(url, params=params, timeout=timeout, headers=merged)
    response.raise_for_status()
    if sleep > 0:
        time.sleep(sleep)
    return response
