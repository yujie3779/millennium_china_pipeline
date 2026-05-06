"""Doc2Vec embedder (gensim, PV-DM) — corpus-trained dense vectors.

Captures word-order context via a sliding window + paragraph vector,
producing dense 200-D embeddings that drop straight into Ward clustering
without any sparse-matrix tricks. Tradeoff (quantified in ``compare.py``):
must learn its own vocabulary from this corpus, so it tends to be noisier
than a frozen multilingual SBERT on small corpora.
"""
from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

import numpy as np
from gensim.models.doc2vec import Doc2Vec, TaggedDocument

from ..config import (
    DOC2VEC_EPOCHS,
    DOC2VEC_MIN_COUNT,
    DOC2VEC_VECTOR_SIZE,
    DOC2VEC_WINDOW,
    RANDOM_STATE,
    VECTORS_DIR,
)

LOG = logging.getLogger(__name__)


@dataclass
class Doc2VecArtefact:
    ids: List[str]
    embeddings: np.ndarray  # shape (N, D)
    vocabulary_size: int

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump(self, fh)
        return path

    @classmethod
    def load(cls, path: Path) -> "Doc2VecArtefact":
        with path.open("rb") as fh:
            return pickle.load(fh)


class Doc2VecEmbedder:
    """Train a PV-DM Doc2Vec model on the supplied tokenized corpus."""

    def __init__(
        self,
        vector_size: int = DOC2VEC_VECTOR_SIZE,
        window: int = DOC2VEC_WINDOW,
        min_count: int = DOC2VEC_MIN_COUNT,
        epochs: int = DOC2VEC_EPOCHS,
        seed: int = RANDOM_STATE,
        workers: int = 2,
    ) -> None:
        self.vector_size = vector_size
        self.window = window
        self.min_count = min_count
        self.epochs = epochs
        self.seed = seed
        self.workers = workers
        self.model: Doc2Vec | None = None

    def fit(self, ids: Sequence[str], token_lists: Iterable[List[str]]) -> Doc2Vec:
        token_lists = list(token_lists)
        tagged = [
            TaggedDocument(words=tokens, tags=[ids[i]])
            for i, tokens in enumerate(token_lists)
        ]
        model = Doc2Vec(
            documents=tagged,
            vector_size=self.vector_size,
            window=self.window,
            min_count=self.min_count,
            epochs=self.epochs,
            workers=self.workers,
            seed=self.seed,
            dm=1,  # PV-DM (distributed memory)
        )
        self.model = model
        LOG.info(
            "Doc2Vec: %d docs, %d-D, vocab=%d, %d epochs",
            len(tagged), self.vector_size, len(model.wv), self.epochs,
        )
        return model

    def transform(self, ids: Sequence[str]) -> np.ndarray:
        assert self.model is not None, "fit() before transform()"
        return np.vstack(
            [self.model.dv[i] for i in ids if i in self.model.dv]
        ).astype(np.float32)


def embed_doc2vec(
    ids: Sequence[str],
    token_lists: Sequence[List[str]],
    out_name: str = "doc2vec.pkl",
) -> Doc2VecArtefact:
    """Train + serialise a Doc2VecArtefact for ``ids``."""
    enc = Doc2VecEmbedder()
    model = enc.fit(ids, token_lists)
    embeddings = enc.transform(list(ids))
    artefact = Doc2VecArtefact(
        ids=list(ids),
        embeddings=embeddings,
        vocabulary_size=len(model.wv),
    )
    artefact.save(VECTORS_DIR / out_name)
    return artefact
