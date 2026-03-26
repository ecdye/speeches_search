from flask import Flask, render_template, request
from next_plaid_client import NextPlaidClient

from .database import get_all_speakers, get_paragraph_content
from .searcher import search_speeches, search_by_speaker

NEXTPLAID_URL = "http://localhost:8080"

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    speakers = get_all_speakers()
    query = request.args.get("query", "").strip()
    speaker = request.args.get("speaker", "").strip()
    top_k = request.args.get("top_k", "5")
    try:
        top_k = int(top_k)
    except ValueError:
        top_k = 5

    results = []
    if query:
        with NextPlaidClient(NEXTPLAID_URL) as client:
            if speaker:
                search_result = search_by_speaker(client, query, speaker, top_k=top_k)
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

    return render_template(
        "index.html",
        speakers=speakers,
        results=results,
        query=query,
        selected_speaker=speaker,
    )


def run_webapp():
    app.run(debug=True, host="0.0.0.0", port=8081)
