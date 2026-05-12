"""Elasticsearch client wrapper."""

from __future__ import annotations

from elasticsearch import Elasticsearch

from ebm_backend.shared.config.settings import settings


def get_es_client(host: str | None = None) -> Elasticsearch:
    return Elasticsearch(host or settings.es_host)
