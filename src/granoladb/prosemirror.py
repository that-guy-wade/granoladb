"""Build Granola's ProseMirror `notes` document from text lines.

Granola renders a note's editor (and its AI reads it) from the `notes` field — a
ProseMirror document: `paragraph` nodes, each with a uuid `id`, containing `text`.
Setting this makes GranolaDB notes visible and query-able. Pure Python, no deps.
"""
import uuid


def build(lines):
    """lines: list[str] -> a ProseMirror doc dict for Granola's `notes` field.

    Each line becomes a paragraph; empty strings become blank paragraphs.
    """
    content = []
    for line in lines:
        node = {"type": "paragraph", "attrs": {"id": str(uuid.uuid4())}}
        if line:
            node["content"] = [{"type": "text", "text": line}]
        content.append(node)
    return {"type": "doc", "content": content}
