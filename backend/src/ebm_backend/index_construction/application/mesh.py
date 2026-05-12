"""NLM MeSH lookup helpers for Module 1 normalization."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

MESH_LOOKUP_URL = "https://id.nlm.nih.gov/mesh/lookup/descriptor"


@dataclass(frozen=True)
class MeshLookupResult:
    descriptor_id: str
    preferred_term: str
    entry_terms: list[str]


class _Opener(Protocol):
    def __call__(self, url: str, timeout: int): ...


class MeshLookupClient:
    def __init__(self, timeout: int = 10, opener: _Opener | None = None):
        self.timeout = timeout
        self.opener = opener or urllib.request.urlopen

    @lru_cache(maxsize=2048)
    def lookup(self, label: str) -> MeshLookupResult | None:
        query = urllib.parse.urlencode({"label": label})
        url = f"{MESH_LOOKUP_URL}?{query}"
        try:
            with self.opener(url, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None
        if not payload:
            return None
        first = payload[0]
        resource = first.get("resource", "")
        descriptor_id = resource.rsplit("/", 1)[-1] if resource else ""
        preferred_term = first.get("label", label)
        if not descriptor_id:
            return None
        return MeshLookupResult(
            descriptor_id=descriptor_id,
            preferred_term=preferred_term,
            entry_terms=[],
        )
