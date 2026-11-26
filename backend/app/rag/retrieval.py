import hashlib
import math
import re
from dataclasses import dataclass
from collections import Counter

from app.schemas import RetrievalStrategy
from app.storage.documents import StoredChildChunk


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9$%]+")

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "does", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "the", "this", "to", "what",
    "when", "where", "which", "with",
}

INSURANCE_SYNONYMS = {
    "claim": ("claims", "loss", "damage"),
    "coverage": ("cover", "insured", "benefit"),
    "deductible": ("excess", "out-of-pocket"),
    "excluded": ("exclusion", "not-covered"),
    "excludes": ("exclusion", "not-covered"),
    "flood": ("water", "water-damage"),
    "premium": ("price", "cost"),
    "renewal": ("renew", "extension"),
}


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: StoredChildChunk
    score: float


def _tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
        if token.lower() not in STOP_WORDS
    ]


def transform_query(question: str) -> str:
    """Expand insurance terms deterministically without a model or API key."""
    tokens = _tokens(question)
    additions: list[str] = []
    for token in tokens:
        additions.extend(INSURANCE_SYNONYMS.get(token, ()))
    if not additions:
        return question
    return " ".join([question, *dict.fromkeys(additions)])


def _hashed_embedding(text: str, dimensions: int = 512) -> list[float]:
    vector = [0.0] * dimensions
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest, "little") % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _bm25_scores(
    question_tokens: list[str],
    chunks: list[StoredChildChunk],
) -> dict[str, float]:
    tokenized = [_tokens(chunk.text) for chunk in chunks]
    lengths = [len(tokens) for tokens in tokenized]
    average_length = sum(lengths) / len(lengths) if lengths else 1.0
    document_frequency: Counter[str] = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens))

    scores: dict[str, float] = {}
    for chunk, chunk_tokens in zip(chunks, tokenized):
        if not chunk_tokens:
            scores[chunk.chunk_id] = 0.0
            continue
        frequencies = Counter(chunk_tokens)
        score = 0.0
        for token in set(question_tokens):
            frequency = frequencies[token]
            if not frequency:
                continue
            idf = math.log(
                1.0
                + (len(chunks) - document_frequency[token] + 0.5)
                / (document_frequency[token] + 0.5)
            )
            normalization = 1.2 * (
                1.0 - 0.75 + 0.75 * len(chunk_tokens) / average_length
            )
            score += idf * (frequency * 2.2) / (frequency + normalization)
        scores[chunk.chunk_id] = score
    return scores


def rerank_chunks(
    question: str,
    retrieved: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    """Re-rank lexical matches with section/title and term-overlap signals."""
    question_terms = set(_tokens(question))
    reranked: list[RetrievedChunk] = []
    for item in retrieved:
        chunk_terms = set(_tokens(item.chunk.text))
        overlap = len(question_terms & chunk_terms) / max(len(question_terms), 1)
        section_terms = set(_tokens(item.chunk.section_title or ""))
        section_overlap = len(question_terms & section_terms) / max(
            len(question_terms),
            1,
        )
        adjusted_score = item.score + (0.35 * overlap) + (0.15 * section_overlap)
        reranked.append(RetrievedChunk(chunk=item.chunk, score=adjusted_score))
    reranked.sort(key=lambda item: item.score, reverse=True)
    return reranked


def compress_chunk_text(
    question: str,
    text: str,
    max_chars: int = 900,
) -> str:
    """Keep the most relevant sentences while preserving source sentence order."""
    if len(text) <= max_chars:
        return text
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]
    if len(sentences) == 1:
        return text[: max(1, max_chars)].rstrip() + "..."

    query_terms = set(_tokens(transform_query(question)))
    ranked = []
    for index, sentence in enumerate(sentences):
        sentence_terms = set(_tokens(sentence))
        overlap = len(query_terms & sentence_terms)
        ranked.append((overlap, -index, index, sentence))

    selected_indexes = [
        index
        for _, _, index, sentence in sorted(
            ranked,
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )
        if sentence
    ]
    kept: list[str] = []
    length = 0
    for index in sorted(selected_indexes):
        sentence = sentences[index]
        separator = 1 if kept else 0
        if length + separator + len(sentence) > max_chars:
            continue
        kept.append(sentence)
        length += separator + len(sentence)
    result = " ".join(kept)
    return result if result else text[:max_chars].rstrip() + "..."


def retrieve_chunks(
    question: str,
    chunks: list[StoredChildChunk],
    strategy: RetrievalStrategy,
    top_k: int,
    *,
    query_transform: bool = True,
    rerank: bool = True,
) -> list[RetrievedChunk]:
    if not chunks:
        return []

    search_question = transform_query(question) if query_transform else question
    question_embedding = _hashed_embedding(search_question)
    question_tokens = _tokens(search_question)
    dense = [
        (chunk, _cosine(question_embedding, _hashed_embedding(chunk.text)))
        for chunk in chunks
    ]
    if strategy is RetrievalStrategy.SEMANTIC:
        ranked = dense
    elif strategy is RetrievalStrategy.BM25:
        bm25_by_id = _bm25_scores(question_tokens, chunks)
        ranked = [(chunk, bm25_by_id[chunk.chunk_id]) for chunk in chunks]
    else:
        dense_by_id = {chunk.chunk_id: score for chunk, score in dense}
        bm25_by_id = _bm25_scores(question_tokens, chunks)
        dense_max = max(dense_by_id.values(), default=0.0)
        bm25_max = max(bm25_by_id.values(), default=0.0)
        ranked = [
            (
                chunk,
                (
                    (dense_by_id[chunk.chunk_id] / dense_max if dense_max else 0.0)
                    + (bm25_by_id[chunk.chunk_id] / bm25_max if bm25_max else 0.0)
                ),
            )
            for chunk in chunks
        ]

    ranked.sort(key=lambda item: item[1], reverse=True)
    retrieved = [
        RetrievedChunk(chunk=chunk, score=score)
        for chunk, score in ranked[:top_k]
        if score > 0
    ]
    return rerank_chunks(question, retrieved) if rerank else retrieved
