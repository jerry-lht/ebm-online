"""Cleaned article contracts consumed by online workflow modules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ArticleMetadata:
    title: str
    pmid: str | None = None
    pmc_id: str | None = None
    source_type: str | None = None
    publication_year: str | None = None
    mesh_terms: list[str] = field(default_factory=list)
    doi: str | None = None


@dataclass(frozen=True)
class ArticleSection:
    section_id: str
    title: str
    text: str


@dataclass(frozen=True)
class ArticleXmlContent:
    sections: list[ArticleSection] = field(default_factory=list)


@dataclass(frozen=True)
class ArticleTable:
    table_id: str
    caption: str
    rows: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class ArticleSource:
    database: str
    retrieval_rank: int | None = None
    retrieval_score: float | None = None
    raw_source_url: str | None = None
    raw_record_id: str | None = None


@dataclass(frozen=True)
class CleanedArticle:
    study_id: str
    metadata: ArticleMetadata
    xml_content: ArticleXmlContent
    tables: list[ArticleTable] = field(default_factory=list)
    source: ArticleSource | None = None


@dataclass(frozen=True)
class SearchRetrievalResult:
    search_query: str
    query_used: str
    database: str
    total_hits: int
    returned_count: int
    articles: list[CleanedArticle] = field(default_factory=list)
