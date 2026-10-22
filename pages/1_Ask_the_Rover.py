"""Page 2: ask questions about the rover. Answers come only from our notes, log and datasheets."""

import streamlit as st

import rag
from ui import esc, setup

setup("Ask the Rover", "💬")

EXAMPLES = [
    "Why does the LiDAR disconnect during turns?",
    "What is the peak output current of the TB6612FNG?",
    "What is the measuring range of the RPLiDAR A1M8?",
    "How much power does an on-spot turn need?",
    "How long does the battery last on one charge?",
]


@st.cache_resource(show_spinner="Reading the notes and datasheets (first start takes about a minute) ...")
def get_index():
    return rag.RoverIndex()


index = get_index()

# ---------------- sidebar: how it works ----------------
with st.sidebar:
    s = index.stats()
    st.markdown("### What it searches")
    st.markdown(
        f"- {s['datasheet']} datasheet pieces, including {s['table_rows']} table pieces\n"
        f"- {s['notes']} sections of our build notes\n"
        f"- {s['log']} items from our workflow")
    st.markdown("### How an answer is made")
    st.markdown(
        "1. **Search** with keywords (BM25) and meaning (embeddings) together.\n"
        "2. If the question names a part, only that part's datasheet is searched.\n"
        "3. If nothing is close enough, it says *I don't know* without asking the AI.\n"
        "4. The AI answers **only** from the passages found, with [n] citations.\n"
        "5. **Number check:** every number in the answer must appear in a cited passage.")
    provider = rag.llm_provider()
    st.caption(f"Language model: {provider.capitalize() + ', ' + rag.current_model() if provider else 'not set (showing passages only)'}")
    if st.button("Clear chat"):
        st.session_state.history = []
        st.rerun()

# ---------------- main area ----------------
st.markdown('<div class="rv-kicker">Retrieval-augmented question answering</div>'
            '<h1 class="rv-ask-title">Ask the Rover</h1>', unsafe_allow_html=True)
st.markdown('<p class="rv-lede">Questions about our rover, its parts and what we found while building it. '
            "Every answer shows where it came from: our build notes, our workflow, or the datasheets of the "
            "parts on the rover. If the answer is not there, it says so.</p>", unsafe_allow_html=True)

if "history" not in st.session_state:
    st.session_state.history = []


def badge(check: dict) -> str:
    status = check["status"]
    if status == "verified":
        return '<span class="rv-badge rv-ok">✓ Every number found in the cited source</span>'
    if status == "unverified":
        miss = ", ".join(str(m) for m in check["missing"])
        return f'<span class="rv-badge rv-warn">⚠ Not found in the sources: {esc(miss)}. Check before using.</span>'
    if status == "refused":
        return '<span class="rv-badge rv-info">Not in our data</span>'
    if status == "no_llm":
        return '<span class="rv-badge rv-info">Passage only, no language model set</span>'
    return '<span class="rv-badge rv-info">No numbers to check</span>'


def show_result(res: dict) -> None:
    st.markdown(res["answer"])
    st.markdown(badge(res["check"]), unsafe_allow_html=True)
    if res["check"]["status"] == "refused" and res.get("gate") == "low_score":
        st.caption(f"Closest match score {res['info']['best_similarity']:.2f}, below the {rag.MIN_SIMILARITY} "
                   "limit, so the language model was not asked.")
        return

    hits, cited = res["hits"], res["cited"]
    chips = "".join(
        f'<span class="rv-src{" on" if i in cited else ""}">[{i}] {esc(c.label)}</span>'
        for i, (c, _) in enumerate(hits, start=1))
    st.markdown(chips, unsafe_allow_html=True)

    with st.expander("Show the source passages"):
        for i, (c, score) in enumerate(hits, start=1):
            mark = "cited" if i in cited else "found, not cited"
            st.markdown(f"**[{i}] {c.label}**, match {score:.2f}, {mark}")
            st.text(c.text)

    # Show the real datasheet page for the first cited datasheet source.
    for i in (cited or [1]):
        c = hits[i - 1][0]
        if c.source_type == "datasheet":
            with st.expander(f"See {c.part} datasheet, page {c.page}"):
                st.image(rag.page_image(c.source, c.page, rag.highlight_terms(res["answer"])),
                         width="stretch")
            break


for res in st.session_state.history:
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(res["question"])
    with st.chat_message("assistant", avatar=":material/radar:"):
        show_result(res)

question = None
if not st.session_state.history:
    picked = st.pills("Try one of these:", EXAMPLES, key="example")
    if picked and st.session_state.get("example_used") != picked:
        st.session_state.example_used = picked
        question = picked

typed = st.chat_input("Ask about the rover, its parts, or a problem we faced")
question = typed or question

if question:
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(question)
    with st.chat_message("assistant", avatar=":material/radar:"):
        with st.spinner("Searching ..."):
            try:
                res = rag.answer(index, question)
            except Exception as e:
                st.error(f"The language model call failed. {e}")
                st.stop()
        show_result(res)
    st.session_state.history.append(res)
