"""Matplotlib + Seaborn plotting suite (six figures)."""
from .plots import (
    plot_dataset_overview,
    plot_dendrogram,
    plot_fragment_params_heatmap,
    plot_method_comparison,
    plot_token_distribution,
    plot_tsne_clusters,
    setup_chinese_font,
)

__all__ = [
    "plot_dataset_overview", "plot_token_distribution",
    "plot_method_comparison", "plot_dendrogram",
    "plot_tsne_clusters", "plot_fragment_params_heatmap",
    "setup_chinese_font",
]
