"""Sentence-BERT embedder — frozen pretrained multilingual MiniLM.

Vs Doc2Vec: out-of-the-box zh/en grounding (paraphrase-multilingual-
MiniLM-L12-v2 was fine-tuned on 50+ language pairs); zero training.
Drawback (surfaced in compare.py's notes): paraphrase-optimised, so
buildings described in similar registers can land closer than they should.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence

import numpy as np

from ..config import SBERT_MODEL_NAME, VECTORS_DIR

LOG = logging.getLogger(__name__)


@dataclass
class SBertArtefact:
    ids: List[str]
    embeddings: np.ndarray  # (N, 384), L2-normalised
    model_name: str

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            ids=np.array(self.ids, dtype=object),
            embeddings=self.embeddings.astype(np.float32),
            model_name=np.array([self.model_name], dtype=object),
        )
        return path

    @classmethod
    def load(cls, path: Path) -> "SBertArtefact":
        data = np.load(path, allow_pickle=True)
        return cls(
            ids=list(data["ids"]),
            embeddings=data["embeddings"],
            model_name=str(data["model_name"][0]),
        )


class SBertEmbedder:
    """Lazy-loaded multilingual MiniLM encoder."""

    def __init__(self, model_name: str = SBERT_MODEL_NAME) -> None:
        from sentence_transformers import SentenceTransformer  # noqa: WPS433

        LOG.info("Sentence-BERT: loading %s", model_name)
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(
        self, texts: Sequence[str], batch_size: int = 32, normalize: bool = True
    ) -> np.ndarray:
        emb = self.model.encode(
            list(texts),
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            show_progress_bar=True,
        )
        return emb.astype(np.float32)


def embed_sbert(
    ids: Sequence[str],
    texts: Sequence[str],
    out_name: str = "sbert.npz",
) -> SBertArtefact:
    """Encode ``texts`` to MiniLM space and persist."""
    enc = SBertEmbedder()
    embeddings = enc.encode(texts)
    artefact = SBertArtefact(
        ids=list(ids),
        embeddings=embeddings,
        model_name=enc.model_name,
    )
    artefact.save(VECTORS_DIR / out_name)
    LOG.info("Sentence-BERT: saved %d × %d → %s",
             *embeddings.shape, VECTORS_DIR / out_name)
    return artefact
