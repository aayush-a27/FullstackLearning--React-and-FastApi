"""Chunking, model routing and retrieval — the pieces RAG depends on."""
import numpy as np
import pytest

from app.services.chunking import chunk_pages, group_chunks_into_sections
from app.services.embedding_service import pack_vector, unpack_matrix, EMBED_DIM
from app.services.ai_service import _candidate_models
from app.services.model_router import (
    classify_complexity,
    is_summary_question,
    normalize_model_id,
    select_model,
    MODEL_MAX_CONTEXT_CHARS,
)


# --- chunking ---------------------------------------------------------------

def test_chunking_splits_long_text_with_overlap():
    pages = ["word " * 500, "other " * 500]
    chunks = chunk_pages(pages, target_chars=400, overlap_chars=100)
    assert len(chunks) > 2
    assert all(c.content for c in chunks)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_chunking_tracks_page_numbers():
    pages = ["alpha " * 200, "beta " * 200, "gamma " * 200]
    chunks = chunk_pages(pages, target_chars=300, overlap_chars=50)
    assert min(c.page_start for c in chunks) == 1
    assert max(c.page_end for c in chunks) == 3
    # Pages increase as we move through the document
    assert [c.page_start for c in chunks] == sorted(c.page_start for c in chunks)


def test_chunking_ignores_blank_pages():
    assert chunk_pages(["", "   ", ""]) == []


def test_chunking_keeps_short_documents_in_one_chunk():
    chunks = chunk_pages(["Just a short line of text."])
    assert len(chunks) == 1
    assert chunks[0].page_start == chunks[0].page_end == 1


def test_sections_group_chunks_by_size():
    chunks = chunk_pages(["x " * 5000], target_chars=500, overlap_chars=0)
    sections = group_chunks_into_sections(chunks, target_chars=2000)
    assert len(sections) > 1
    assert sum(len(s) for s in sections) == len(chunks)


# --- embedding storage ------------------------------------------------------

def test_vectors_are_normalized_and_round_trip():
    packed = pack_vector([3.0] + [0.0] * (EMBED_DIM - 1))
    matrix = unpack_matrix([packed])
    assert matrix.shape == (1, EMBED_DIM)
    assert np.isclose(np.linalg.norm(matrix[0]), 1.0)


def test_cosine_similarity_is_a_dot_product_after_packing():
    a = unpack_matrix([pack_vector([1.0, 1.0] + [0.0] * (EMBED_DIM - 2))])[0]
    same = unpack_matrix([pack_vector([2.0, 2.0] + [0.0] * (EMBED_DIM - 2))])[0]
    orthogonal = unpack_matrix([pack_vector([0.0, 0.0, 1.0] + [0.0] * (EMBED_DIM - 3))])[0]
    assert np.isclose(a @ same, 1.0, atol=1e-6)
    assert np.isclose(a @ orthogonal, 0.0, atol=1e-6)


# --- routing ----------------------------------------------------------------

@pytest.mark.parametrize(
    "question,expected",
    [
        ("hi", "simple"),
        ("Who is Jon Snow?", "simple"),
        ("Summarize chapter 3", "moderate"),
        ("Explain how the Night's Watch works", "moderate"),
        ("Compare these two leaders and analyse their weaknesses in detail", "complex"),
        ("Write an essay about the themes", "complex"),
    ],
)
def test_complexity_classification(question, expected):
    assert classify_complexity(question) == expected


def test_large_context_forces_a_capable_model():
    assert classify_complexity("What is this?", context_len=50_000) == "complex"


@pytest.mark.parametrize(
    "question,expected",
    [
        ("summarize this book", True),
        ("what is this document about", True),
        ("tl;dr", True),
        ("what are the main themes", True),
        ("Who killed Jon Arryn?", False),
        ("List the characters on page 20", False),
    ],
)
def test_summary_intent_detection(question, expected):
    assert is_summary_question(question) is expected


def test_smart_switch_off_keeps_the_chosen_model():
    assert select_model("hi", "nemotron-super", smart_switch_enabled=False) == "nemotron-super"


def test_smart_switch_on_overrides_the_chosen_model():
    assert select_model("hi", "nemotron-super", smart_switch_enabled=True) == "groq-fast"


def test_legacy_model_ids_are_mapped():
    assert normalize_model_id("groq-llama3") == "groq-fast"
    assert normalize_model_id("gpt-4o") == "nemotron-super"
    assert normalize_model_id("nonsense") is None
    assert normalize_model_id(None) is None


def test_fallback_order_starts_with_the_requested_model():
    assert _candidate_models("gemini-flash", 100)[0] == "gemini-flash"


def test_models_too_small_for_the_context_are_skipped():
    big = MODEL_MAX_CONTEXT_CHARS["groq-fast"] + 1
    assert "groq-fast" not in _candidate_models("groq-fast", big)


def test_oversized_context_falls_back_to_the_largest_model():
    candidates = _candidate_models("groq-fast", 10_000_000)
    assert candidates == ["gemini-flash"]
