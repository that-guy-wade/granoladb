from typing import Optional, Protocol


class Backend(Protocol):
    def create_document(self, title: str, body: str) -> str: ...
    def get_documents(self, after: Optional[str] = None) -> list: ...
    def get_document(self, doc_id: str) -> dict: ...


class FakeBackend:
    """In-memory backend for tests and dry demos. No network."""

    def __init__(self):
        self._docs = {}
        self._n = 0

    def create_document(self, title, body):
        self._n += 1
        doc_id = f"doc-{self._n}"
        self._docs[doc_id] = {"id": doc_id, "title": title, "body": body}
        return doc_id

    def get_documents(self, after=None):
        return list(self._docs.values())

    def get_document(self, doc_id):
        return self._docs[doc_id]
