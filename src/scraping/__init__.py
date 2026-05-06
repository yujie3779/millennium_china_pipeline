"""Three scrapers for the millennium-China-architecture dataset.

Three complementary retrieval philosophies: SPARQL semantic query
against Wikidata, Pixabay keyword search (REST API), and Bilibili
search + XML danmaku stream.
"""
from .bilibili import scrape_bilibili
from .pixabay import scrape_pixabay
from .wikidata_sparql import scrape_wikidata_sparql

__all__ = ["scrape_bilibili", "scrape_pixabay", "scrape_wikidata_sparql"]
