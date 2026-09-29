from granoladb.backend import FakeBackend


def test_create_and_get_documents():
    b = FakeBackend()
    doc_id = b.create_document("[gdb] t ERROR api", "body-1")
    assert isinstance(doc_id, str) and doc_id
    docs = b.get_documents()
    assert docs == [{"id": doc_id, "title": "[gdb] t ERROR api", "body": "body-1"}]


def test_get_document_by_id():
    b = FakeBackend()
    doc_id = b.create_document("t", "body")
    assert b.get_document(doc_id)["body"] == "body"
