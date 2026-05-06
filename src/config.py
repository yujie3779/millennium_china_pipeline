"""Project-wide configuration for demo131.

Theme: 中国千禧年代地标建筑 (China's millennial-decade landmarks, 2000–2010).
Everything here is theme-tunable — change the constants below to retarget
the entire pipeline.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
VECTORS_DIR = DATA_DIR / "vectors"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PLOTS_DIR = OUTPUTS_DIR / "plots"
CLUSTERS_DIR = OUTPUTS_DIR / "clusters"
FRAGMENT_PARAMS_DIR = OUTPUTS_DIR / "fragments_params"
GH_MESHES_DIR = OUTPUTS_DIR / "gh_meshes"
RENDERS_DIR = OUTPUTS_DIR / "renders"

# --- Theme ---------------------------------------------------------------- #
# Used by every scraper to focus the search, by jieba as user dict, and by
# OpenAI as in-context priming.
THEME_NAME_ZH = "中国千禧年代建筑"
THEME_NAME_EN = "Millennium-decade Chinese architecture (2000s)"

# Curated seed building names — used to bootstrap Wikidata SPARQL queries
# and to drive Bilibili keyword searches.
SEED_BUILDINGS_ZH = [
    # 北京奥运 / 国家级标志
    "国家体育场", "国家游泳中心", "中央电视台总部大楼", "国家大剧院",
    "国家体育馆", "首都博物馆", "中国国家博物馆", "首都国际机场3号航站楼",
    "鸟巢", "水立方",
    # 北京其他千禧建筑
    "中国国际贸易中心三期", "银河SOHO", "三里屯太古里",
    "盘古大观", "国贸大酒店", "北京电视台总部大楼",
    # 上海
    "上海环球金融中心", "上海中心大厦", "东方明珠广播电视塔",
    "上海东方艺术中心", "上海科技馆", "中国2010年上海世界博览会中国国家馆",
    "上海世博会中国国家馆", "金茂大厦", "上海大剧院",
    "外滩源", "上海浦东国际机场",
    # 广州 / 深圳
    "广州塔", "广州大剧院", "广州西塔", "广州国际金融中心",
    "深圳京基100", "深圳市民中心", "深圳证券交易所大楼",
    "京基100", "深圳大运中心",
    # 其他大城市
    "天津之眼", "天津津塔", "南京紫峰大厦", "苏州东方之门",
    "杭州市民中心", "重庆来福士广场", "成都来福士广场",
    "武汉绿地中心", "西安大唐芙蓉园", "厦门双子塔",
    "青岛奥帆中心", "沈阳方圆大厦",
]

SEED_BUILDINGS_EN = [
    "Beijing National Stadium",
    "Beijing National Aquatics Center",
    "CCTV Headquarters",
    "National Centre for the Performing Arts China",
    "Shanghai World Financial Center",
    "Shanghai Tower",
    "Canton Tower",
    "Oriental Pearl Tower",
    "National Museum of China",
    "China Zun",
    "Shanghai Oriental Art Center",
    "China Pavilion Expo 2010",
    "Guangzhou Opera House",
]

# How many items each scraper aims to collect.
# Brief says 200–300 per dataset; we aim for 220 (comfortably above the
# 200 floor while keeping scrape time reasonable).
TARGET_ITEMS_PER_DATASET = 220

# --- Vectorization -------------------------------------------------------- #
DOC2VEC_VECTOR_SIZE = 200
DOC2VEC_EPOCHS = 40
DOC2VEC_WINDOW = 8
DOC2VEC_MIN_COUNT = 2

SBERT_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
SBERT_DIM = 384

# --- Clustering ----------------------------------------------------------- #
N_CLUSTERS = 5            # Ward target k (matches dendrogram cut)
FRAGMENTS_PER_CLUSTER = 4 # 5 * 4 = 20 fragments

# --- Manifold learning ---------------------------------------------------- #
TSNE_PERPLEXITY = 30
TSNE_LEARNING_RATE = "auto"

# Reproducibility — used everywhere a seed is needed.
RANDOM_STATE = 42

# --- OpenAI augmentation -------------------------------------------------- #
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_AUGMENT_COUNT = 50

# --- Pixabay -------------------------------------------------------------- #
PIXABAY_ENDPOINT = "https://pixabay.com/api/"
PIXABAY_PER_PAGE = 50  # max 200, but 50 is friendlier

# --- Bilibili ------------------------------------------------------------- #
BILIBILI_SEARCH_ENDPOINT = "https://api.bilibili.com/x/web-interface/search/type"
BILIBILI_DANMAKU_ENDPOINT = "https://comment.bilibili.com/{cid}.xml"


def ensure_dirs() -> None:
    """Create every output directory used by the project."""
    for d in (
        RAW_DIR,
        PROCESSED_DIR,
        VECTORS_DIR,
        PLOTS_DIR,
        CLUSTERS_DIR,
        FRAGMENT_PARAMS_DIR,
        GH_MESHES_DIR,
        RENDERS_DIR,
        RAW_DIR / "wikidata",
        RAW_DIR / "pixabay",
        RAW_DIR / "bilibili",
    ):
        d.mkdir(parents=True, exist_ok=True)
