"""Two text vectorizers + an empirical comparator.

    Doc2Vec  (gensim PV-DM, trained on this corpus)
    Sentence-BERT (paraphrase-multilingual-MiniLM-L12-v2, frozen pretrained)

Both methods sit at opposite ends of a useful axis: shallow self-supervised
trained from scratch vs deep pretrained Transformer used zero-shot. The
``compare_methods`` helper produces a JSON report so the choice between the
two can be defended empirically rather than by appeal to authority.
"""
from .compare import compare_methods, evaluate_doc2vec, evaluate_sbert
from .doc2vec import Doc2VecArtefact, Doc2VecEmbedder, embed_doc2vec
from .sbert import SBertArtefact, SBertEmbedder, embed_sbert

__all__ = [
    "Doc2VecArtefact", "Doc2VecEmbedder", "embed_doc2vec",
    "SBertArtefact", "SBertEmbedder", "embed_sbert",
    "compare_methods", "evaluate_doc2vec", "evaluate_sbert",
]
