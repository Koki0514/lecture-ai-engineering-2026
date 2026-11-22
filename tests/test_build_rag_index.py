"""実SQLiteと固定ベクトルで、索引作成から検索までを確認する。APIは呼ばない。"""

import json
from unittest.mock import Mock

import pytest

from app import retrieval
from scripts.build_rag_index import build_index


@pytest.fixture
def materials(tmp_path):
    source = tmp_path / "lectures.json"
    source.write_text(json.dumps([
        {"id": f"lec{n:02d}-main", "title": f"講義{n}", "content": [
            {"section": "章", "content": [
                {"id": f"lec{n:02d}-main-p001", "title": f"ページ{n}",
                 "page": 1, "content": f"本文{n}"}]}]}
        for n in (1, 2, 5)
    ], ensure_ascii=False), encoding="utf-8")
    return source, tmp_path / "index.sqlite3"


def test_built_index_can_be_searched(materials, monkeypatch):
    source, database = materials
    texts = []

    def embed(text, task):
        assert task == "RETRIEVAL_DOCUMENT"
        texts.append(text)
        return [1, 0] if "本文1" in text else [0, 1]

    result = build_index(source, database, embedder=embed)
    assert result["pages"] == 2  # 第5回の資料は検索対象に含めない
    assert all("章" in text and "ページ" in text for text in texts)
    monkeypatch.setattr(retrieval, "RAG_DB", database)
    monkeypatch.setattr(retrieval, "embed_text", lambda *_: [1, 0])
    hits = retrieval.search("質問")
    assert [h["page_id"] for h in hits] == ["lec01-main-p001", "lec02-main-p001"]
    assert hits[0]["content"] == "本文1"
    assert hits[0]["distance"] == pytest.approx(0)


def test_search_can_include_unique_neighbors_from_the_same_document(tmp_path, monkeypatch):
    source = tmp_path / "lectures.json"
    database = tmp_path / "index.sqlite3"
    documents = [
        {"id": "lec01-main", "title": "講義1", "content": [
            {"section": "章", "content": [
                {"id": f"lec01-main-p{page:03d}", "title": f"ページ{page}",
                 "page": page, "content": {1: "近い", 2: "一致", 3: "隣接"}[page]}
                for page in (1, 2, 3)]}]},
        {"id": "lec02-main", "title": "講義2", "content": [
            {"section": "章", "content": [
                {"id": "lec02-main-p002", "title": "別資料のページ2",
                 "page": 2, "content": "別資料"}]}]},
    ]
    source.write_text(json.dumps(documents, ensure_ascii=False), encoding="utf-8")

    def embed(text, task):
        assert task == "RETRIEVAL_DOCUMENT"
        if "一致" in text:
            return [1, 0]
        if "近い" in text:
            return [0.99, 0.1]
        return [0, 1]

    build_index(source, database, embedder=embed)
    monkeypatch.setattr(retrieval, "RAG_DB", database)
    monkeypatch.setattr(retrieval, "RAG_TOP_K", 2)
    monkeypatch.setattr(retrieval, "embed_text", lambda *_: [1, 0])
    monkeypatch.delenv("RAG_INCLUDE_NEIGHBORS", raising=False)

    regular_hits = retrieval.search("質問")
    assert [hit["page_id"] for hit in regular_hits] == [
        "lec01-main-p002", "lec01-main-p001",
    ]

    monkeypatch.setenv("RAG_INCLUDE_NEIGHBORS", "1")
    expanded_hits = retrieval.search("質問")
    assert [hit["page_id"] for hit in expanded_hits] == [
        "lec01-main-p002", "lec01-main-p001", "lec01-main-p003",
    ]
    assert [hit["page_id"] for hit in retrieval.search(
        "質問", include_neighbors=False,
    )] == [hit["page_id"] for hit in regular_hits]
    assert len({hit["page_id"] for hit in expanded_hits}) == len(expanded_hits)
    assert all(hit["document_id"] == "lec01-main" for hit in expanded_hits)
    assert all(set(hit) == set(regular_hits[0]) for hit in expanded_hits)

    monkeypatch.setattr(retrieval, "RAG_TOP_K", 1)
    assert [hit["page_id"] for hit in retrieval.search("質問")] == [
        "lec01-main-p002", "lec01-main-p001", "lec01-main-p003",
    ]


def test_existing_index_survives_failed_rebuild(materials):
    source, database = materials
    build_index(source, database, embedder=lambda *_: [1, 0])
    before = database.read_bytes()
    embed = Mock(side_effect=RuntimeError("埋め込みに失敗"))
    with pytest.raises(FileExistsError):
        build_index(source, database, embedder=embed)
    embed.assert_not_called()
    with pytest.raises(RuntimeError, match="埋め込みに失敗"):
        build_index(source, database, rebuild=True, embedder=embed)
    assert database.read_bytes() == before
    assert not list(database.parent.glob(".rag-build-*"))
