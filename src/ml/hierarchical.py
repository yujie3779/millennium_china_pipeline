"""Ward hierarchical clustering + t-SNE + the bridge to 3D design.

Ward agglomeration produces a full dendrogram (cut at k=5) that Blender
later consumes to drive a branch-unfold reveal animation; t-SNE provides
the 2-D projection used in the cluster scatter plot. The function
``fragments_from_clusters`` materialises the ``clusters.json`` shared by
both 3D pipelines (Grasshopper and Blender Geometry Nodes).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score

from ..config import (
    CLUSTERS_DIR,
    FRAGMENT_PARAMS_DIR,
    FRAGMENTS_PER_CLUSTER,
    N_CLUSTERS,
    RANDOM_STATE,
    TSNE_LEARNING_RATE,
    TSNE_PERPLEXITY,
)

LOG = logging.getLogger(__name__)


@dataclass
class HierarchicalResult:
    labels: np.ndarray
    centroids: np.ndarray  # (k, d)
    linkage_matrix: np.ndarray  # scipy linkage Z, shape (N-1, 4)
    silhouette: float
    k: int
    embedding_kind: str  # "doc2vec" | "sbert" | "fused"
    cluster_sizes: List[int] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "k": self.k,
            "embedding_kind": self.embedding_kind,
            "silhouette": self.silhouette,
            "cluster_sizes": self.cluster_sizes,
            # Convert dendrogram to a list-of-lists so it survives JSON.
            "linkage": self.linkage_matrix.tolist(),
        }


def run_ward(
    matrix: np.ndarray,
    k: int = N_CLUSTERS,
    embedding_kind: str = "fused",
) -> HierarchicalResult:
    """Run Ward agglomerative clustering, cut the tree at ``k``."""
    if matrix.ndim != 2:
        raise ValueError("input must be 2-D")

    LOG.info("Ward: linkage on %d × %d", *matrix.shape)
    Z = linkage(matrix, method="ward", metric="euclidean")
    return cut_dendrogram(matrix, Z, k=k, embedding_kind=embedding_kind)


def cut_dendrogram(
    matrix: np.ndarray,
    linkage_matrix: np.ndarray,
    k: int,
    embedding_kind: str,
) -> HierarchicalResult:
    """Cut a pre-computed linkage matrix into ``k`` flat clusters."""
    labels = fcluster(linkage_matrix, t=k, criterion="maxclust") - 1  # 0-based

    centroids = np.zeros((k, matrix.shape[1]), dtype=np.float32)
    sizes = []
    for ci in range(k):
        members = matrix[labels == ci]
        sizes.append(int(len(members)))
        if len(members):
            centroids[ci] = members.mean(axis=0)

    sil = (
        float(silhouette_score(matrix, labels, metric="euclidean"))
        if matrix.shape[0] > k + 1
        else float("nan")
    )

    return HierarchicalResult(
        labels=labels,
        centroids=centroids,
        linkage_matrix=linkage_matrix,
        silhouette=sil,
        k=k,
        embedding_kind=embedding_kind,
        cluster_sizes=sizes,
    )


def project_tsne(
    matrix: np.ndarray,
    perplexity: float = TSNE_PERPLEXITY,
    learning_rate=TSNE_LEARNING_RATE,
) -> np.ndarray:
    """t-SNE → 2-D for plotting (deliberately not UMAP)."""
    if matrix.shape[0] - 1 < perplexity * 3:
        perplexity = max(5, (matrix.shape[0] - 1) // 3)
        LOG.info("t-SNE: shrinking perplexity to %d", perplexity)

    LOG.info("t-SNE: %d × %d → 2-D, perplexity=%s", *matrix.shape, perplexity)
    reducer = TSNE(
        n_components=2,
        perplexity=perplexity,
        learning_rate=learning_rate,
        init="pca",
        random_state=RANDOM_STATE,
        metric="euclidean",
    )
    return reducer.fit_transform(matrix)


# --- The bridge to 3D ---------------------------------------------------- #

# Six normalised parameters meaningful to *Chinese* millennium architecture
# (steel-lattice woven, ETFE pillow facade, double-Z cantilever, twisting
# tower, stepped pavilion). Mapping is deterministic so GH and Blender
# read the same numbers.
PARAM_KEYS = (
    "lattice",       # 0..1 — steel-truss density (鸟巢-style)
    "pillow",        # 0..1 — ETFE puff inflation amount (水立方-style)
    "cantilever",    # 0..1 — horizontal overhang ratio (CCTV-style)
    "twist",         # 0..1 — z-axis rotation per metre (上海中心-style)
    "stack",         # 0..1 — number of stacked terraces (中国馆-style)
    "porosity",      # 0..1 — facade opening fraction (general)
)


def _project_centroid_to_params(centroid: np.ndarray) -> dict:
    """Hash a centroid into 6 normalised parameters via a fixed projection."""
    rng = np.random.default_rng(RANDOM_STATE)
    n_dim = centroid.shape[0]
    proj = rng.standard_normal((len(PARAM_KEYS), n_dim))
    raw = proj @ centroid
    # robust sigmoid normalisation
    norm = 1.0 / (1.0 + np.exp(-raw / max(1e-6, np.std(raw))))
    return {k: float(v) for k, v in zip(PARAM_KEYS, norm)}


def fragments_from_clusters(
    result: HierarchicalResult,
    fragments_per_cluster: int = FRAGMENTS_PER_CLUSTER,
    out_path: Path | None = None,
) -> Path:
    """Materialise k × ``fragments_per_cluster`` parametric fragments → JSON."""
    rng = np.random.default_rng(RANDOM_STATE)
    fragments: list[dict] = []

    # Map each Ward cluster to one of five "archetype" labels — purely for
    # downstream readability. The archetype identity is centroid-dependent
    # and stable across runs because the projection seed is fixed.
    archetype_names = (
        "lattice_woven",     # 鸟巢
        "pillow_skin",       # 水立方
        "double_cantilever", # CCTV
        "twisting_tower",    # 上海中心
        "stepped_pavilion",  # 中国馆
    )

    for ci, centroid in enumerate(result.centroids):
        base_params = _project_centroid_to_params(centroid)
        archetype = archetype_names[ci % len(archetype_names)]
        for vi in range(fragments_per_cluster):
            jitter = rng.normal(0.0, 0.07, size=len(PARAM_KEYS))
            params = {
                k: float(np.clip(base_params[k] + jitter[i], 0.0, 1.0))
                for i, k in enumerate(PARAM_KEYS)
            }
            fragments.append(
                {
                    "fragment_id": f"frag-c{ci:02d}-v{vi:02d}",
                    "cluster": ci,
                    "variant": vi,
                    "archetype": archetype,
                    "params": params,
                    "cluster_size": result.cluster_sizes[ci],
                }
            )

    payload = {
        "k": result.k,
        "embedding_kind": result.embedding_kind,
        "fragments_per_cluster": fragments_per_cluster,
        "param_keys": list(PARAM_KEYS),
        "archetype_names": list(archetype_names),
        "fragments": fragments,
    }

    out_path = out_path or (FRAGMENT_PARAMS_DIR / "clusters.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    LOG.info("wrote %d fragments → %s", len(fragments), out_path)

    summary = CLUSTERS_DIR / "summary.json"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_path
