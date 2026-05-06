"""OpenAI Chat augmentation — synthesise *Chinese* millennium-architecture entries.

Chinese system prompt in 建筑评论体 (review register, not encyclopaedic),
structured JSON output (title/city/year/typology/text), and a topic-driven
typology × city × year matrix sampled with replacement so every call is
unique. The 50 generated reviews are merged into the corpus before
vectorisation, so they participate in the Ward dendrogram on equal footing
with the scraped data.

Setup: write the key to ``.openai_key`` (gitignored) or set
``OPENAI_API_KEY``. Optional ``.openai_base_url`` for OpenAI-compatible
proxies.
"""
from __future__ import annotations

import json
import logging
import os
import random
from pathlib import Path
from typing import Iterable, List

from tqdm import tqdm

from ..config import OPENAI_AUGMENT_COUNT, OPENAI_MODEL, RANDOM_STATE, RAW_DIR

LOG = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "你是一位资深建筑评论家，专门撰写 21 世纪头十年（2000–2010）"
    "中国大陆地标建筑的简短分析。每一段评论必须：\n"
    "1. 长度 100–180 个汉字；\n"
    "2. 包含：建筑名称（虚构，但风格契合时代）、所在城市、建成年份、"
    "结构类型（如钢编织、双悬臂、ETFE 气枕、扭转塔身、斗拱叠加等）、"
    "材料肌理、社会语境（奥运、世博、城市化等）；\n"
    "3. 不要复制任何已存在的真实建筑名；\n"
    "4. 输出严格为 JSON：{\"title\":..., \"city\":..., \"year\":..., "
    "\"typology\":..., \"text\":...}。\n"
)


TYPOLOGIES = [
    "钢编织", "ETFE 气枕外膜", "双 Z 悬臂", "螺旋扭转塔身", "斗拱阶梯", "悬浮平台",
    "灯笼造型表皮", "双层玻璃幕墙", "波浪形钢结构", "立体网架穹顶",
]

CITIES = [
    "北京", "上海", "广州", "深圳", "杭州", "南京", "苏州", "天津",
    "武汉", "成都", "重庆", "厦门", "青岛", "西安", "沈阳",
]

YEARS = list(range(2000, 2011))


def _load_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    for candidate in (
        Path(".openai_key"),
        Path(__file__).resolve().parents[2] / ".openai_key",
    ):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    raise RuntimeError(
        "OpenAI key not found — set OPENAI_API_KEY or write `.openai_key`."
    )


def _load_base_url() -> str | None:
    """Optional OpenAI-compatible proxy URL (env or `.openai_base_url`)."""
    url = os.environ.get("OPENAI_BASE_URL")
    if url:
        return url.strip()
    for candidate in (
        Path(".openai_base_url"),
        Path(__file__).resolve().parents[2] / ".openai_base_url",
    ):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    return None


def _make_user_prompt(rng: random.Random) -> str:
    typology = rng.choice(TYPOLOGIES)
    city = rng.choice(CITIES)
    year = rng.choice(YEARS)
    return (
        f"撰写一段关于 {year} 年建成于 {city} 的虚构地标的建筑评论，"
        f"主结构采用 {typology}。请按 JSON 格式输出。"
    )


def generate_synthetic_descriptions(
    n: int = OPENAI_AUGMENT_COUNT,
    out_path: Path | None = None,
    model: str = OPENAI_MODEL,
    dry_run: bool = False,
) -> Path:
    """Generate ``n`` synthetic Chinese architecture descriptions → JSONL."""
    out_path = out_path or (RAW_DIR / "openai_synthetic_zh.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not dry_run and out_path.exists():
        with out_path.open(encoding="utf-8") as fh:
            existing = [json.loads(line) for line in fh if line.strip()]
        is_real = existing and not any(
            (r.get("text") or "").startswith("[STUB") for r in existing
        )
        if is_real and len(existing) >= n:
            LOG.info(
                "OpenAI augment: %s already has %d real rows — skipping.",
                out_path, len(existing),
            )
            return out_path

    rng = random.Random(RANDOM_STATE)

    if dry_run:
        LOG.info("dry-run mode: writing %d stub records", n)
        with out_path.open("w", encoding="utf-8") as fh:
            for i in range(n):
                typology, city, year = rng.choice(TYPOLOGIES), rng.choice(CITIES), rng.choice(YEARS)
                fh.write(json.dumps({
                    "id": f"openai-stub-{i:04d}", "source": "openai",
                    "title": f"[STUB] {city} {typology} 中心",
                    "text": f"[STUB] 一座 {year} 年建成于 {city} 的虚构 {typology} 建筑。",
                    "typology": typology, "city": city, "year": year,
                }, ensure_ascii=False) + "\n")
        return out_path

    from openai import OpenAI  # noqa: WPS433

    base_url = _load_base_url()
    client_kwargs: dict = {"api_key": _load_api_key()}
    if base_url:
        client_kwargs["base_url"] = base_url
        LOG.info("OpenAI: routing through %s", base_url)
    client = OpenAI(**client_kwargs)

    with out_path.open("w", encoding="utf-8") as fh:
        for i in tqdm(range(n), desc="OpenAI(zh)"):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": _make_user_prompt(rng)},
                    ],
                    temperature=0.9,
                    max_tokens=420,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content.strip()
                obj = json.loads(raw)
            except Exception as exc:  # noqa: BLE001
                LOG.warning("OpenAI call failed (%d): %s", i, exc)
                continue

            fh.write(json.dumps({
                "id": f"openai-{i:04d}", "source": "openai",
                "title": obj.get("title", f"虚构地标 {i}"),
                "city": obj.get("city"), "year": obj.get("year"),
                "typology": obj.get("typology"),
                "text": obj.get("text", ""),
            }, ensure_ascii=False) + "\n")

    LOG.info("OpenAI augment: wrote → %s", out_path)
    return out_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generate_synthetic_descriptions(
        dry_run=os.environ.get("OPENAI_API_KEY") is None,
    )
