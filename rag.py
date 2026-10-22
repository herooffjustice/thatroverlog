"""
rag.py - the question-answering engine behind "Ask the Rover".

Pipeline (the same 4 steps as the Hack Hour poster):
  1. Ingest   - read datasheet PDFs, our notes (.md) and the activity log (.csv),
                and cut them into small chunks. Datasheet tables become one
                sentence per row, so a number never loses its label.
  2. Retrieve - search with BM25 (keywords) and embeddings (meaning) together,
                and mix the two scores into one.
  3. Generate - an LLM answers using ONLY the retrieved chunks.
  4. Cite     - every answer shows its sources, and a "number check" confirms
                each number in the answer really appears in a cited source.

Run `python rag.py` to build the index and try a few questions in the terminal.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent
DATA = ROOT / "data"
INDEX_DIR = ROOT / "index"       # the finished search index, built once and uploaded with the app
INDEX_VERSION = "4"               # raise this when the chunking code changes, then run: python rag.py

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MIN_SIMILARITY = 0.25   # below this, we answer "I don't know" without calling the LLM
TOP_K = 6               # how many chunks the LLM gets
DENSE_WEIGHT = 0.7      # hybrid score = meaning score x weight + keyword score x (1 - weight)
NOT_FOUND = "I don't know. Our notes and datasheets do not have this information."

# Each part, the words people use for it, and a word that appears in its PDF file name.
PARTS = {
    "TB6612FNG": {"file": "tb6612", "names": ["tb6612", "tb6612fng", "motor driver", "h-bridge"]},
    "MPU6050": {"file": "mpu", "names": ["mpu6050", "mpu-6050", "mpu 6050", "mpu6500", "imu", "gyro", "accelerometer"]},
    "RPLiDAR A1M8": {"file": "rplidar", "names": ["rplidar", "a1m8", "lidar"]},
    "Raspberry Pi 5": {"file": "raspberry", "names": ["raspberry pi", "pi 5", "pi5", "raspberry"]},
}


@dataclass
class Chunk:
    text: str
    source_type: str          # "datasheet", "notes" or "log"
    source: str               # file name, or "Activity log"
    location: str             # "page 3", a section heading, or a date
    part: str = ""            # for datasheets: which part
    page: int = 0             # for datasheets: 1-based page number
    meta: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        if self.source_type == "datasheet":
            return f"{self.part} datasheet, {self.location}"
        if self.source_type == "log":
            return f"Our workflow, {self.location}"
        return f"Our notes: {self.source}, {self.location}"


# --------------------------------------------------------------------------------------
# 1. INGEST
# --------------------------------------------------------------------------------------

def _clean(text: str) -> str:
    text = (text or "").replace("　", " ")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n", text).strip()


def _windows(words: list[str], size: int = 140, overlap: int = 30):
    """Split a long list of words into overlapping windows."""
    if len(words) <= size:
        yield " ".join(words)
        return
    step = size - overlap
    for start in range(0, len(words) - overlap, step):
        yield " ".join(words[start:start + size])


def _part_for_file(name: str) -> str:
    low = name.lower()
    for part, info in PARTS.items():
        if info["file"] in low:
            return part
    return Path(name).stem


def _table_to_sentences(table: list[list], part: str, page: int) -> list[str]:
    """Turn one PDF table into one readable sentence per row.

    PDF tables often have merged cells, which pdfplumber returns as None.
    We copy the value from the row above ("fill down"), so a row like
    [None, 'Vcc', '6', None] still says which characteristic it belongs to.
    """
    rows = [[_clean(c) if isinstance(c, str) else c for c in row] for row in table if row]
    if len(rows) < 2:
        return []
    cells = [c for r in rows for c in r if c]
    if len(cells) < 4:
        return []
    # Skip garbled tables (rotated text gives many one-letter cells).
    if sum(len(c) for c in cells) / len(cells) < 2.5:
        return []

    # Two-row headers: the first row has merged cells (None) and the second row has the
    # real column names, for example ["Input", None, None] then ["IN1", "IN2", "PWM"].
    if (len(rows) > 2 and sum(c is None for c in rows[0]) >= len(rows[0]) * 0.3
            and all(isinstance(c, str) and c and not re.match(r"^[-\d.]", c) for c in rows[1])):
        rows = rows[1:]
    header = [(h or "").replace("\n", " ").strip() for h in rows[0]]
    if sum(1 for h in header if h) < 2:
        header = [f"column {i + 1}" for i in range(len(header))]

    sentences, previous = [], [""] * len(header)
    for row in rows[1:]:
        row = list(row) + [None] * (len(header) - len(row))
        filled = []
        for i, cell in enumerate(row[: len(header)]):
            if cell is None and i < 2:          # merged cell: copy from the row above
                cell = previous[i]
            filled.append((cell or "").replace("\n", " ").strip())
        previous = filled
        pairs = [f"{h}: {v}" for h, v in zip(header, filled) if v and h]
        if len(pairs) >= 2:
            sentences.append(f"{part} (page {page}) - " + "; ".join(pairs) + ".")
    return sentences


def load_pdf(path: Path) -> list[Chunk]:
    import pdfplumber

    part = _part_for_file(path.name)
    chunks = []
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            # a) tables -> one sentence per row, grouped 6 rows per chunk
            try:
                tables = page.extract_tables()
            except Exception:
                tables = []
            for table in tables:
                rows = _table_to_sentences(table, part, page_no)
                for i in range(0, len(rows), 6):
                    chunks.append(Chunk(" ".join(rows[i:i + 6]), "datasheet", path.name,
                                        f"page {page_no}", part, page_no, {"kind": "table"}))
            # b) normal text -> overlapping windows of about 140 words
            text = _clean(page.extract_text() or "")
            try:
                page.close()                           # free this page's memory before the next one
            except Exception:
                pass
            words = text.split()
            if len(words) < 12:
                continue
            for piece in _windows(words):
                chunks.append(Chunk(f"{part} (page {page_no}): {piece}", "datasheet", path.name,
                                    f"page {page_no}", part, page_no, {"kind": "text"}))
    return chunks


def load_notes(path: Path) -> list[Chunk]:
    """Split a markdown note by its '## ' headings. One heading = one chunk."""
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^# (.+)$", text, re.M)
    title = title_match.group(1).strip() if title_match else path.stem
    chunks = []
    for section in re.split(r"^## ", text, flags=re.M)[1:]:
        heading, _, body = section.partition("\n")
        body = body.strip()
        for piece in _windows(body.split(), size=220, overlap=40):
            chunks.append(Chunk(f"{title} - {heading.strip()}: {piece}", "notes", title,
                                heading.strip()))
    return chunks


def load_log(path: Path) -> list[Chunk]:
    """Each row of the activity log becomes one chunk."""
    chunks = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            text = (f"Our workflow, {row['no']}. ({row['phase']}) {row['title']}. {row['details']} "
                    f"Status: {row['status']}. Area: {row['area']}.")
            if row.get("captions"):
                text += f" Photo: {row['captions']}"
            chunks.append(Chunk(text, "log", "Our workflow", f"{row['no']}. {row['title']}", meta=dict(row)))
    return chunks


def load_all(data_dir: Path = DATA) -> list[Chunk]:
    chunks: list[Chunk] = []
    for pdf in sorted((data_dir / "datasheets").glob("*.pdf")):
        chunks += load_pdf(pdf)
    for md in sorted((data_dir / "notes").glob("*.md")):
        chunks += load_notes(md)
    if (data_dir / "log.csv").exists():
        chunks += load_log(data_dir / "log.csv")
    return chunks


# --------------------------------------------------------------------------------------
# 2. RETRIEVE
# --------------------------------------------------------------------------------------

TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def detect_parts(question: str) -> list[str]:
    q = question.lower()
    return [part for part, info in PARTS.items()
            if any(re.search(rf"\b{re.escape(n)}\b", q) for n in info["names"])]


def _data_fingerprint(data_dir: Path) -> str:
    """A short code that changes whenever any data file's content changes.
    It uses file contents (not dates), so the same files give the same code on any computer."""
    h = hashlib.md5(f"{INDEX_VERSION}|{EMBED_MODEL}".encode())
    for p in sorted(data_dir.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(data_dir)).replace("\\", "/").encode())
            h.update(hashlib.md5(p.read_bytes()).digest())
    return h.hexdigest()[:12]


class RoverIndex:
    """Holds all chunks, the BM25 index and the embedding (FAISS) index."""

    def __init__(self, data_dir: Path = DATA):
        import faiss
        from fastembed import TextEmbedding
        from rank_bm25 import BM25Okapi

        # threads=1 keeps memory low on small servers (Streamlit Cloud gives about 1 GB).
        self.embedder = TextEmbedding(EMBED_MODEL, threads=1)
        fingerprint = _data_fingerprint(data_dir)
        chunks_file, vectors_file = INDEX_DIR / "chunks.json", INDEX_DIR / "vectors.npy"
        saved = json.loads(chunks_file.read_text(encoding="utf-8")) if chunks_file.exists() else {}
        if saved.get("fingerprint") == fingerprint and vectors_file.exists():
            # Fast and light: load the finished index instead of reading the PDFs again.
            self.chunks = [Chunk(**r) for r in saved["chunks"]]
            vectors = np.load(vectors_file)
        else:
            # Heavy: read every PDF and note, then embed every piece. Done once, then saved.
            self.chunks = load_all(data_dir)
            vectors = self._embed([c.text for c in self.chunks])
            try:
                INDEX_DIR.mkdir(exist_ok=True)
                chunks_file.write_text(json.dumps({"fingerprint": fingerprint,
                                                   "chunks": [vars(c) for c in self.chunks]}), encoding="utf-8")
                np.save(vectors_file, vectors)
            except OSError:
                pass                                   # read-only server: just keep it in memory

        self.vectors = vectors
        self.faiss = faiss.IndexFlatIP(vectors.shape[1])   # inner product = cosine (vectors are normalised)
        self.faiss.add(vectors)
        self.bm25 = BM25Okapi([tokenize(c.text) for c in self.chunks])

    def _embed(self, texts: list[str]) -> np.ndarray:
        v = np.array(list(self.embedder.embed(texts, batch_size=32)), dtype="float32")
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    def stats(self) -> dict:
        out = {"chunks": len(self.chunks)}
        for t in ("datasheet", "notes", "log"):
            out[t] = sum(1 for c in self.chunks if c.source_type == t)
        out["table_rows"] = sum(1 for c in self.chunks if c.meta.get("kind") == "table")
        return out

    def search(self, question: str, k: int = TOP_K, mode: str = "hybrid") -> tuple[list[tuple[Chunk, float]], dict]:
        """Return the top-k chunks with their cosine similarity, plus some debug info.

        mode: "hybrid" (default), "bm25" or "dense" - useful for comparing methods.
        """
        parts = detect_parts(question)
        # Part filter: if the question names a part, ignore the OTHER parts' datasheets.
        # Our notes and the log stay in, because they talk about the whole rover.
        allowed = np.array([
            not (c.source_type == "datasheet" and parts and c.part not in parts)
            for c in self.chunks
        ])

        qvec = self._embed([question])[0]
        dense_scores = self.vectors @ qvec
        bm25_scores = np.array(self.bm25.get_scores(tokenize(question)))
        dense_scores[~allowed] = -1
        bm25_scores[~allowed] = -1

        if mode == "dense":
            fused = list(np.argsort(-dense_scores))
        elif mode == "bm25":
            fused = [i for i in np.argsort(-bm25_scores) if bm25_scores[i] > 0]
        else:
            # Hybrid: mix the two scores. BM25 scores have no fixed scale, so we divide by
            # the best BM25 score first (0..1), like the cosine scores of the embeddings.
            bm25_norm = np.clip(bm25_scores, 0, None) / (bm25_scores.max() or 1.0)
            combined = DENSE_WEIGHT * dense_scores + (1 - DENSE_WEIGHT) * bm25_norm
            combined[~allowed] = -1
            fused = list(np.argsort(-combined))

        top = [(self.chunks[i], float(dense_scores[i])) for i in fused[:k]]
        info = {
            "parts": parts,
            "best_similarity": float(max(dense_scores[allowed])) if allowed.any() else 0.0,
            "best_bm25": float(max(bm25_scores)) if len(bm25_scores) else 0.0,
        }
        return top, info


# --------------------------------------------------------------------------------------
# 3. GENERATE
# --------------------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You answer questions about a student-built autonomous rover. "
    "Use ONLY the numbered sources given. Do not use outside knowledge. "
    "Cite the sources you use like [1] or [2][3] right after each fact. Use only this plain [n] form for citations. "
    "Copy numbers and units exactly as the sources write them. "
    "If a value comes with a condition (for example a pulse length, a voltage or a temperature), give the condition too. "
    "Only say that sources disagree if they give different values for the same thing under the same condition. "
    f"If the sources do not contain the answer, reply exactly: {NOT_FOUND} "
    "Keep the answer short and in simple English."
)


def build_prompt(question: str, hits: list[tuple[Chunk, float]]) -> str:
    sources = "\n\n".join(f"[{i}] ({c.label})\n{c.text}" for i, (c, _) in enumerate(hits, start=1))
    return f"Sources:\n{sources}\n\nQuestion: {question}\nAnswer:"


def _secret(name: str) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


def llm_provider() -> str | None:
    if _secret("GROQ_API_KEY"):
        return "groq"
    if _secret("GEMINI_API_KEY"):
        return "gemini"
    return None


# Groq retires models from time to time. If the chosen model is gone, the app picks the
# first one from this list that the key can use (or any chat model, as a last resort).
GROQ_PREFERRED = ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "openai/gpt-oss-20b",
                  "meta-llama/llama-4-maverick-17b-128e-instruct", "qwen/qwen3-32b", "llama-3.1-8b-instant"]
_NOT_CHAT = ("whisper", "guard", "orpheus", "tts", "embed", "safeguard", "allam")
_groq_model_cache: dict = {}


def _groq_models(key: str) -> list[str]:
    import requests
    r = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=20)
    r.raise_for_status()
    return [m["id"] for m in r.json().get("data", [])]


def _pick_groq_model(key: str) -> str:
    if "model" not in _groq_model_cache:
        available = _groq_models(key)
        chosen = next((m for m in GROQ_PREFERRED if m in available), None)
        if chosen is None:
            chosen = next((m for m in available if not any(w in m.lower() for w in _NOT_CHAT)), GROQ_PREFERRED[0])
        _groq_model_cache["model"] = chosen
    return _groq_model_cache["model"]


def _error_text(r) -> str:
    try:
        return r.json()["error"]["message"]
    except Exception:
        return r.text[:300]


def _clean(text: str) -> str:
    # Some models write their thinking inside <think> ... </think>. Keep only the answer.
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    # Some models cite like 【3†L1-L4】 or [3†L1]. Turn every form into the plain [3] the app reads.
    text = re.sub(r"【\s*(\d+)[^】]*】", r"[\1]", text)
    text = re.sub(r"\[(\d+)†[^\]]*\]", r"[\1]", text)
    return text.strip()


def call_llm(question: str, hits: list[tuple[Chunk, float]]) -> str:
    import requests

    prompt = build_prompt(question, hits)
    provider = llm_provider()
    if provider == "groq":
        key = _secret("GROQ_API_KEY")
        model = _secret("GROQ_MODEL") or _pick_groq_model(key)
        for attempt in range(2):
            body = {"model": model, "temperature": 0,
                    "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                 {"role": "user", "content": prompt}]}
            if model.startswith("openai/gpt-oss"):
                body["reasoning_effort"] = "low"       # faster answers; the task is simple
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              headers={"Authorization": f"Bearer {key}"}, json=body, timeout=60)
            if r.status_code == 404 and attempt == 0:  # model retired: pick another one and retry
                _groq_model_cache.clear()
                model = _pick_groq_model(key)
                continue
            if not r.ok:
                raise RuntimeError(f"Groq said ({r.status_code}): {_error_text(r)}")
            return _clean(r.json()["choices"][0]["message"].get("content", ""))
    if provider == "gemini":
        model = _secret("GEMINI_MODEL") or "gemini-2.5-flash"
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": _secret("GEMINI_API_KEY")},
            json={
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0},
            },
            timeout=60,
        )
        if not r.ok:
            raise RuntimeError(f"Gemini said ({r.status_code}): {_error_text(r)}")
        parts = r.json()["candidates"][0]["content"]["parts"]
        return _clean("".join(p.get("text", "") for p in parts))
    raise RuntimeError("No LLM key found. Add GROQ_API_KEY or GEMINI_API_KEY to .streamlit/secrets.toml")


def current_model() -> str:
    """The model name to show in the sidebar."""
    provider = llm_provider()
    if provider == "groq":
        try:
            return _secret("GROQ_MODEL") or _pick_groq_model(_secret("GROQ_API_KEY"))
        except Exception:
            return "Groq"
    if provider == "gemini":
        return _secret("GEMINI_MODEL") or "gemini-2.5-flash"
    return ""


# --------------------------------------------------------------------------------------
# 4. CITE + NUMBER CHECK
# --------------------------------------------------------------------------------------

NUM_RE = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?")
# Numbers inside part names (6050, 6612, the 5 in "Pi 5" ...) are not facts to check.
PART_NAME_RE = re.compile(r"tb6612fng|tb6612|mpu[- ]?6050|mpu[- ]?6500|a1m8|pi ?5|ros ?2|sdg ?\d+", re.I)


HEX_RE = re.compile(r"\b0x[0-9a-f]+\b", re.I)
BIN_RE = re.compile(r"\bb[01][01 ]*[01x]\b", re.I)


def _numbers(text: str) -> set[str]:
    """Every number in a text, written in one standard form so the answer and sources can be compared.
    Hex (0x68) and binary (b110 1000) values are kept as written; other numbers become plain
    decimals ("0.80" and "0.8" both become "0.8")."""
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)     # all kinds of dashes -> "-"
    text = re.sub(r"[\u00a0\u2000-\u200b\u202f\u205f\u3000]", " ", text)   # all kinds of spaces -> " "
    text = PART_NAME_RE.sub(" ", text)
    text = re.sub(r"\[\d+\]", " ", text)                    # drop citation markers like [2]
    found = set()
    for h in HEX_RE.findall(text):
        found.add(h.lower())
    text = HEX_RE.sub(" ", text)
    for b in BIN_RE.findall(text):
        found.add("b" + re.sub(r"[^01x]", "", b.lower()[1:]))
    text = BIN_RE.sub(" ", text)
    found |= {f"{float(n):g}" for n in NUM_RE.findall(text)}
    return found


def cited_ids(answer: str, n_hits: int) -> list[int]:
    ids = sorted({int(i) for i in re.findall(r"\[(\d+)\]", answer)})
    return [i for i in ids if 1 <= i <= n_hits]


def number_check(answer: str, hits: list[tuple[Chunk, float]]) -> dict:
    """Check that every number in the answer appears in the sources it cites."""
    if NOT_FOUND[:12].lower() in answer.lower():
        return {"status": "refused", "missing": []}
    ids = cited_ids(answer, len(hits)) or list(range(1, len(hits) + 1))
    source_numbers: set[str] = set()
    for i in ids:
        source_numbers |= _numbers(hits[i - 1][0].text)
    answer_numbers = _numbers(answer)
    if not answer_numbers:
        return {"status": "no_numbers", "missing": []}
    missing = sorted(n for n in answer_numbers if n not in source_numbers)
    return {"status": "verified" if not missing else "unverified", "missing": missing}


def answer(index: RoverIndex, question: str) -> dict:
    """Full pipeline for one question. Returns everything the UI needs."""
    hits, info = index.search(question)
    result = {"question": question, "hits": hits, "info": info, "cited": [], "llm": llm_provider()}

    # Early "I don't know": nothing in the data is close enough to the question.
    if info["best_similarity"] < MIN_SIMILARITY:
        result.update(answer=NOT_FOUND, check={"status": "refused", "missing": []}, gate="low_score")
        return result

    if result["llm"] is None:
        # No API key: show the best passage instead of a generated answer.
        top = "\n\n".join(f"> {c.text} [{i}]" for i, (c, _) in enumerate(hits[:2], start=1))
        result.update(answer=f"No LLM key is set, so here are the two best matching passages:\n\n{top}",
                      check={"status": "no_llm", "missing": []}, cited=[1, 2], gate="no_llm")
        return result

    text = call_llm(question, hits)
    result.update(answer=text, check=number_check(text, hits), cited=cited_ids(text, len(hits)), gate="llm")
    return result


# --------------------------------------------------------------------------------------
# Page image with highlights (for showing the real datasheet page next to the answer)
# --------------------------------------------------------------------------------------

def page_image(pdf_name: str, page: int, highlight: list[str], zoom: float = 1.6) -> bytes:
    import pymupdf

    doc = pymupdf.open(DATA / "datasheets" / pdf_name)
    pg = doc[page - 1]
    for term in highlight:
        for rect in pg.search_for(term)[:6]:
            annot = pg.add_highlight_annot(rect)
            annot.set_colors(stroke=(1.0, 0.82, 0.25))
            annot.update()
    png = pg.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")
    doc.close()
    return png


def highlight_terms(answer_text: str) -> list[str]:
    """Strings worth highlighting on the page: the numbers that appear in the answer."""
    text = PART_NAME_RE.sub(" ", re.sub(r"\[\d+\]", " ", answer_text))
    nums = [n for n in NUM_RE.findall(text) if len(n) >= 2 or "." in n or n.isdigit()]
    return list(dict.fromkeys(nums))[:6]


if __name__ == "__main__":
    idx = RoverIndex()
    print(json.dumps(idx.stats(), indent=2))
    for q in ["What is the maximum output current per channel of the TB6612FNG?",
              "Why does the LiDAR disconnect during turns?",
              "What is the rover's top speed on grass?"]:
        hits, info = idx.search(q)
        print("\nQ:", q, "| parts:", info["parts"], "| best sim: %.2f" % info["best_similarity"])
        for c, s in hits[:3]:
            print(f"   {s:.2f}  {c.label}: {c.text[:110]}")
