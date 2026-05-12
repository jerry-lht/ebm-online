from __future__ import annotations

from ebm_backend.index_construction.application.mesh import MeshLookupClient


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return b'[{"resource":"http://id.nlm.nih.gov/mesh/D008687","label":"Metformin"}]'


def _fake_opener(url: str, timeout: int):
    assert "label=metformin" in url
    assert timeout == 10
    return _FakeResponse()


def test_mesh_lookup_client_returns_descriptor():
    client = MeshLookupClient(timeout=10, opener=_fake_opener)
    result = client.lookup("metformin")
    assert result is not None
    assert result.descriptor_id == "D008687"
    assert result.preferred_term == "Metformin"
