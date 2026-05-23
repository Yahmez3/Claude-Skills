"""Sentiment scoring engines: VADER, TextBlob, LLM (Claude), and ensemble."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
except ImportError:
    _vader = None  # type: ignore[assignment]
except LookupError:
    import nltk
    nltk.download("vader_lexicon", quiet=True)
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()

try:
    from textblob import TextBlob
except ImportError:
    TextBlob = None  # type: ignore[assignment]

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]


@dataclass
class SentimentResult:
    text_id: str
    score: float      # -1.0 (bearish) to +1.0 (bullish)
    magnitude: float   # 0.0 (neutral) to 1.0 (strong)
    method: str
    symbol: str | None = None


def _text_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def vader_score(text: str, symbol: str | None = None) -> SentimentResult:
    if _vader is None:
        raise ImportError("pip install nltk && python -c \"import nltk; nltk.download('vader_lexicon')\"")
    scores = _vader.polarity_scores(text)
    return SentimentResult(
        text_id=_text_id(text),
        score=scores["compound"],
        magnitude=abs(scores["compound"]),
        method="vader",
        symbol=symbol,
    )


def textblob_score(text: str, symbol: str | None = None) -> SentimentResult:
    if TextBlob is None:
        raise ImportError("pip install textblob")
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity      # -1 to 1
    subjectivity = blob.sentiment.subjectivity  # 0 to 1
    return SentimentResult(
        text_id=_text_id(text),
        score=polarity,
        magnitude=subjectivity,
        method="textblob",
        symbol=symbol,
    )


_LLM_SYSTEM_PROMPT = (
    "You are a financial sentiment classifier. For each text, output a JSON object with "
    "\"score\" (float from -1.0 bearish to +1.0 bullish) and \"magnitude\" (float 0.0 to 1.0 "
    "indicating strength of sentiment). Return a JSON array of objects, one per input text, "
    "in the same order. Output ONLY the JSON array, no other text."
)


def llm_score(
    texts: list[str],
    symbols: list[str | None] | None = None,
    model: str = "claude-sonnet-4-6",
) -> list[SentimentResult]:
    if anthropic is None:
        raise ImportError("pip install anthropic")

    if symbols is None:
        symbols = [None] * len(texts)

    numbered = "\n".join(f"[{i}] {t[:500]}" for i, t in enumerate(texts))

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": _LLM_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": numbered}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    parsed = json.loads(raw)

    results: list[SentimentResult] = []
    for i, item in enumerate(parsed):
        score = max(-1.0, min(1.0, float(item["score"])))
        magnitude = max(0.0, min(1.0, float(item["magnitude"])))
        results.append(SentimentResult(
            text_id=_text_id(texts[i]),
            score=score,
            magnitude=magnitude,
            method="llm",
            symbol=symbols[i] if i < len(symbols) else None,
        ))

    return results


def ensemble_score(
    text: str,
    methods: list[str] | None = None,
    symbol: str | None = None,
) -> SentimentResult:
    """Average scores across multiple methods for a more robust reading."""
    methods = methods or ["vader", "textblob"]

    scorers = {
        "vader": lambda t: vader_score(t, symbol),
        "textblob": lambda t: textblob_score(t, symbol),
    }

    results: list[SentimentResult] = []
    for m in methods:
        if m == "llm":
            llm_results = llm_score([text], symbols=[symbol])
            results.extend(llm_results)
        elif m in scorers:
            results.append(scorers[m](text))
        else:
            raise ValueError(f"Unknown method: {m}. Choose from vader, textblob, llm.")

    if not results:
        raise ValueError("No scoring methods produced results")

    avg_score = sum(r.score for r in results) / len(results)
    avg_magnitude = sum(r.magnitude for r in results) / len(results)

    return SentimentResult(
        text_id=_text_id(text),
        score=avg_score,
        magnitude=avg_magnitude,
        method="ensemble",
        symbol=symbol,
    )
