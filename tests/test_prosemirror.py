# tests/test_prosemirror.py
from granoladb import prosemirror


def test_build_makes_paragraphs_with_text():
    doc = prosemirror.build(["hello world", "second line"])
    assert doc["type"] == "doc"
    assert [n["type"] for n in doc["content"]] == ["paragraph", "paragraph"]
    assert doc["content"][0]["content"][0]["text"] == "hello world"


def test_build_gives_each_paragraph_a_uuid_id():
    doc = prosemirror.build(["a", "b"])
    ids = [n["attrs"]["id"] for n in doc["content"]]
    assert len(ids) == len(set(ids)) == 2
    assert all(len(i) == 36 for i in ids)  # uuid4 string


def test_build_blank_line_is_empty_paragraph():
    doc = prosemirror.build(["", "x"])
    assert "content" not in doc["content"][0]
    assert doc["content"][1]["content"][0]["text"] == "x"
