from flask import Flask, render_template, request, jsonify
from next_plaid_client import NextPlaidClient

from .database import get_all_speakers, get_paragraph_content
from .searcher import search_speeches, search_by_speaker, search_by_speakers

NEXTPLAID_URL = "http://localhost:8080"
PAGE_SIZE = 5
DEFAULT_TOP_K = 50
SCORE_CUTOFF_RATIO = 0.7

app = Flask(__name__)


def _build_results(query: str, selected_speakers: list[str], top_k: int) -> list[dict]:
    results = []
    with NextPlaidClient(NEXTPLAID_URL) as client:
        if len(selected_speakers) == 1:
            search_result = search_by_speaker(client, query, selected_speakers[0], top_k=top_k)
        elif len(selected_speakers) > 1:
            search_result = search_by_speakers(client, query, selected_speakers, top_k=top_k)
        else:
            search_result = search_speeches(client, query, top_k=top_k)

        # Group hits by talk
        grouped: dict[tuple[str, str, str, str], list[tuple[float, int]]] = {}
        for qr in search_result.results:
            for score, meta in zip(qr.scores, qr.metadata or []):
                assert meta is not None
                key = (
                    meta.get("speaker_name", "Unknown"),
                    meta.get("speech_title", "Unknown"),
                    meta.get("speech_url", "Unknown"),
                    meta.get("speech_date", "Unknown"),
                )
                para_idx = int(meta.get("paragraph_index", 0))
                grouped.setdefault(key, []).append((score, para_idx))

        for (speaker_name, title, url, date), hits in grouped.items():
            hits.sort(key=lambda h: h[1])  # sort by paragraph index
            best_score = max(h[0] for h in hits)
            para_indices = [h[1] for h in hits]

            # Fetch paragraph content and insert ellipsis between gaps
            paragraphs: list[str] = []
            for i, idx in enumerate(para_indices):
                if i > 0 and idx != para_indices[i - 1] + 1:
                    paragraphs.append("…")
                content = get_paragraph_content(speaker_name, title, idx)
                if content:
                    paragraphs.append(content)

            results.append({
                "title": title,
                "speaker": speaker_name,
                "date": date,
                "paragraph_indices": ", ".join(str(p) for p in para_indices),
                "best_score": best_score,
                "url": url,
                "paragraphs": paragraphs,
            })

        results.sort(key=lambda r: r["best_score"], reverse=True)

        # Drop results below the relative score cutoff
        if results:
            top_score = results[0]["best_score"]
            threshold = top_score * SCORE_CUTOFF_RATIO
            results = [r for r in results if r["best_score"] >= threshold]

    return results


@app.route("/", methods=["GET"])
def index():
    speakers = get_all_speakers()
    query = request.args.get("query", "").strip()
    selected_speakers = [s.strip() for s in request.args.getlist("speaker") if s.strip()]
    top_k = request.args.get("top_k", str(DEFAULT_TOP_K))
    try:
        top_k = int(top_k)
    except ValueError:
        top_k = DEFAULT_TOP_K

    results = []
    total = 0
    if query:
        results = _build_results(query, selected_speakers, top_k)
        total = len(results)
        results = results[:PAGE_SIZE]

    return render_template(
        "index.html",
        speakers=speakers,
        results=results,
        total=total,
        query=query,
        selected_speakers=selected_speakers,
    )


@app.route("/api/search", methods=["GET"])
def api_search():
    query = request.args.get("query", "").strip()
    selected_speakers = [s.strip() for s in request.args.getlist("speaker") if s.strip()]
    top_k = request.args.get("top_k", str(DEFAULT_TOP_K))
    offset = request.args.get("offset", "0")
    limit = request.args.get("limit", str(PAGE_SIZE))
    try:
        top_k = int(top_k)
    except ValueError:
        top_k = DEFAULT_TOP_K
    try:
        offset = int(offset)
    except ValueError:
        offset = 0
    try:
        limit = int(limit)
    except ValueError:
        limit = PAGE_SIZE

    if not query:
        return jsonify({"results": [], "total": 0, "has_more": False})

    all_results = _build_results(query, selected_speakers, top_k)
    page = all_results[offset:offset + limit]
    return jsonify({
        "results": page,
        "total": len(all_results),
        "has_more": offset + limit < len(all_results),
    })


def run_webapp():
    app.run(debug=True, host="0.0.0.0", port=8081)
