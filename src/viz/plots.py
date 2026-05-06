"""Visualization suite (Matplotlib + Seaborn) — six figures.

Figure index (matches the 04_visualization.ipynb narrative order):

    01  dataset overview (per-source counts)
    02  token-count distribution per source
    03  Doc2Vec vs Sentence-BERT empirical comparison
    04  Ward dendrogram (truncated)
    05  t-SNE projection — coloured by Ward cluster + by source
    06  fragment-parameter heatmap (the JSON consumed by GH + Blender)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import font_manager
from scipy.cluster.hierarchy import dendrogram

from ..config import PLOTS_DIR

LOG = logging.getLogger(__name__)

sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams["figure.dpi"] = 110
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False


def setup_chinese_font() -> str | None:
    """Pick a Chinese-glyph font available on the host (Windows-friendly)."""
    candidates = [
        "Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
        "WenQuanYi Zen Hei", "PingFang SC", "Source Han Sans CN",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            plt.rcParams["axes.unicode_minus"] = False
            LOG.info("font: %s", name)
            return name
    LOG.warning("no Chinese font found — labels may render as boxes")
    return None


def _save(fig: plt.Figure, name: str) -> Path:
    """Save the figure AND inline-display it in the calling notebook cell."""
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = PLOTS_DIR / f"{name}.png"
    fig.savefig(out)
    LOG.info("plot → %s", out)
    try:
        from IPython.display import display

        display(fig)
    except Exception:
        pass
    plt.close(fig)
    return out


# --- 01 dataset overview -------------------------------------------------- #

def plot_dataset_overview(corpus: pd.DataFrame) -> Path:
    counts = (
        corpus["source"].value_counts().rename_axis("source").reset_index(name="count")
    )
    fig, ax = plt.subplots(figsize=(6.5, 4))
    sns.barplot(
        data=counts, x="source", y="count", hue="source",
        palette="rocket", legend=False, ax=ax,
    )
    for p in ax.patches:
        ax.annotate(
            f"{int(p.get_height())}",
            (p.get_x() + p.get_width() / 2, p.get_height()),
            ha="center", va="bottom", fontsize=10,
        )
    ax.set_title("各数据源条目数 / Items per source")
    ax.set_xlabel("")
    ax.set_ylabel("条目数 (count)")
    return _save(fig, "01_dataset_overview")


# --- 02 token distribution ----------------------------------------------- #

def plot_token_distribution(corpus: pd.DataFrame) -> Path:
    df = corpus.assign(token_count=corpus["tokens"].str.split().str.len())
    fig, ax = plt.subplots(figsize=(7, 4))
    sns.boxenplot(
        data=df, x="source", y="token_count",
        hue="source", palette="mako", legend=False, ax=ax,
    )
    ax.set_title("分词后长度分布 / Token-count distribution per source")
    ax.set_ylabel("Tokens per item")
    ax.set_xlabel("")
    ax.set_yscale("log")
    return _save(fig, "02_token_distribution")


# --- 03 method comparison ------------------------------------------------- #

def plot_method_comparison(report: dict) -> Path:
    rows = []
    for key, r in report.items():
        rows.append({"method": r["method"], "metric": "silhouette",
                     "value": r["silhouette"]})
        rows.append({"method": r["method"], "metric": "top-5 source purity",
                     "value": r["mean_intra_source_topk_purity"]})
        rows.append({"method": r["method"], "metric": "fit time (s, /100)",
                     "value": r["fit_seconds"] / 100.0})
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    sns.barplot(
        data=df, x="metric", y="value", hue="method",
        palette="rocket_r", ax=ax,
    )
    ax.set_title("Doc2Vec vs Sentence-BERT — empirical comparison")
    ax.set_ylabel("Score (higher = better, except fit time)")
    ax.set_xlabel("")
    ax.legend(title="", fontsize=8)
    for c in ax.containers:
        ax.bar_label(c, fmt="%.3f", padding=3, fontsize=8)
    return _save(fig, "03_method_comparison")


# --- 04 Ward dendrogram -------------------------------------------------- #

def plot_dendrogram(linkage_matrix: np.ndarray, k: int = 5) -> Path:
    fig, ax = plt.subplots(figsize=(11, 5))
    # Truncated dendrogram: show only the top 30 merges so labels stay legible.
    dendrogram(
        linkage_matrix,
        truncate_mode="lastp",
        p=30,
        leaf_rotation=90,
        leaf_font_size=9,
        color_threshold=linkage_matrix[-(k - 1), 2] if len(linkage_matrix) >= k - 1 else 0,
        ax=ax,
    )
    ax.set_title(f"Ward dendrogram (truncated to last 30 merges, k={k})")
    ax.set_xlabel("Cluster (collapsed)")
    ax.set_ylabel("Linkage distance")
    return _save(fig, "04_dendrogram")


# --- 05 t-SNE clusters --------------------------------------------------- #

def plot_tsne_clusters(
    coords_2d: np.ndarray,
    labels: Sequence[int],
    sources: Sequence[str] | None = None,
) -> Path:
    df = pd.DataFrame(
        {"x": coords_2d[:, 0], "y": coords_2d[:, 1], "cluster": labels}
    )
    if sources is not None:
        df["source"] = list(sources)
        fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.5))
        sns.scatterplot(
            data=df, x="x", y="y", hue="cluster",
            palette="tab10", s=20, alpha=0.85, ax=axes[0],
        )
        axes[0].set_title("t-SNE — coloured by Ward cluster")
        sns.scatterplot(
            data=df, x="x", y="y", hue="source",
            palette="Set2", s=20, alpha=0.85, ax=axes[1],
        )
        axes[1].set_title("t-SNE — coloured by source")
        for ax in axes:
            ax.set_xlabel("t-SNE-1")
            ax.set_ylabel("t-SNE-2")
        fig.tight_layout()
    else:
        fig, ax = plt.subplots(figsize=(7.5, 6))
        sns.scatterplot(
            data=df, x="x", y="y", hue="cluster",
            palette="tab10", s=20, alpha=0.85, ax=ax,
        )
        ax.set_title("t-SNE — coloured by Ward cluster")
    return _save(fig, "05_tsne_clusters")


# --- 06 fragment-parameter heatmap -------------------------------------- #

def plot_fragment_params_heatmap(fragments_payload: dict) -> Path:
    keys = fragments_payload["param_keys"]
    rows = []
    for f in fragments_payload["fragments"]:
        rows.append({"fragment": f["fragment_id"], **f["params"]})
    df = pd.DataFrame(rows).set_index("fragment")[keys]
    fig, ax = plt.subplots(figsize=(8.5, max(5.5, 0.3 * len(df))))
    sns.heatmap(
        df, cmap="mako", ax=ax, vmin=0, vmax=1,
        cbar_kws={"label": "normalised value"},
    )
    ax.set_title("20 个建筑碎片参数矩阵 (5 clusters × 4 variants)")
    ax.set_ylabel("")
    return _save(fig, "06_fragment_params_heatmap")
