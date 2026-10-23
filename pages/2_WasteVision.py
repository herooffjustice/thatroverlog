"""Page 3: WasteVision. Find waste items in a photo, give each one its waste stream,
and explain the disposal rule behind it. Uses its own data (data_waste/, index_waste/),
separate from the rover's."""

import base64
import hashlib
import io
import json

import streamlit as st
from PIL import Image

import rag
import waste_vision as wv
from ui import ROOT, esc, heading, setup

setup("WasteVision", "♻️")

st.markdown(
    """<style>
.wv-items { display: grid; gap: 12px; }
.wv-item { --c: #1E8F55; display: grid; grid-template-columns: 2.1rem 1fr; gap: .2rem .8rem; align-items: start;
  padding: .85rem 1rem .9rem; background: color-mix(in srgb, var(--c) 6%, #F7F8F4); border-left: 5px solid var(--c); }
.wv-item .n { width: 2.1rem; height: 2.1rem; display: flex; align-items: center; justify-content: center;
  background: var(--c); color: #fff; font: 700 1rem 'Bricolage Grotesque', sans-serif; }
.wv-item .lab { font: 700 1.12rem/1.3 'Bricolage Grotesque', sans-serif; color: #161D21; }
.wv-item .chip { display: inline-block; margin: .3rem .4rem 0 0; padding: .05rem .55rem; font-size: .84rem;
  font-weight: 700; color: #fff; background: var(--c); border-radius: 3px; }
.wv-item .conf { font-size: .85rem; color: #566166; }
.wv-item .bar { height: 5px; margin-top: .45rem; background: #DDE0D8; border-radius: 3px; overflow: hidden; }
.wv-item .bar i { display: block; height: 100%; background: var(--c); }
.wv-item .unsure { margin-top: .35rem; font-size: .9rem; color: #8A5A00; font-weight: 600; }
.wv-tally { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: .4rem 0 1.2rem; }
.wv-tally div { --c: #1E8F55; padding: .6rem .8rem; border-top: 4px solid var(--c);
  background: color-mix(in srgb, var(--c) 7%, #F7F8F4); }
.wv-tally b { display: block; font: 700 1.9rem/1 'Bricolage Grotesque', sans-serif; color: color-mix(in srgb, var(--c) 78%, #000); }
.wv-tally span { font-size: .9rem; color: #566166; }
.wv-shot { padding: 7px; background: #fff; border: 1px solid #D2D5CD; box-shadow: 8px 8px 0 0 rgba(30,143,85,.25); }
.wv-shot img { display: block; width: 100%; height: auto; }
.wv-honest { margin: 1rem 0 0; padding: .75rem 1rem; background: #F7F8F4; border-left: 4px solid #0F8B8D;
  font-size: .98rem; line-height: 1.55; color: #161D21; max-width: 80ch; }
.wv-honest b { color: #0B6E70; }
@media (max-width: 640px) { .wv-tally { grid-template-columns: 1fr 1fr; } }
</style>""",
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner="Loading the waste detection model ...")
def get_detector():
    return wv.WasteDetector()


@st.cache_resource(show_spinner="Loading the waste rules ...")
def get_rules():
    return rag.WasteIndex()


# ---------------- sidebar ----------------
with st.sidebar:
    st.markdown("### How it works")
    st.markdown(
        "1. **Detect:** a YOLOv8 model finds each waste item and names its material.\n"
        "2. **Sort:** each material is mapped to a waste stream from the Solid Waste Management Rules 2016: "
        "wet, dry or domestic hazardous. E-waste is kept apart, as the E-Waste Rules 2022 require.\n"
        "3. **Check:** if the model is less than "
        f"{int(wv.SURE_SCORE * 100)}% sure, you are asked to confirm.\n"
        "4. **Explain:** *Why?* asks the rules assistant, which answers only from the rules, with sources.")
    st.markdown("### What the rules assistant reads")
    st.markdown("- Solid Waste Management Rules 2016\n- Plastic Waste Management Rules 2016 (as amended)\n"
                "- E-Waste (Management) Rules 2022")
    st.caption("This is separate from the rover's notes. The two never mix.")
    st.markdown("### Know its limits")
    st.markdown(
        "The model was trained on about 2,000 photos. It is best at food waste, metal and paper, "
        "and weaker at plastic, glass and medical waste. Indian waste such as milk packets and "
        "multilayer sachets was not in its training photos, so always check its answer.")
    provider = rag.llm_provider()
    st.caption(f"Language model: {provider.capitalize() + ', ' + rag.current_model() if provider else 'not set'}")

# ---------------- header ----------------
st.markdown('<div class="rv-kicker">Computer vision for waste segregation</div>'
            '<h1 class="rv-ask-title">WasteVision</h1>', unsafe_allow_html=True)
st.markdown('<p class="rv-lede">Show it a photo of waste. It finds each item, tells you which stream it '
            "goes in, and explains the rule behind it, quoting India's waste management rules.</p>",
            unsafe_allow_html=True)



# ---------------- the rover sorting litter (simulation) ----------------
def waste_sim_html() -> tuple[str, dict]:
    """The animation, with the litter photos and our model's real results put inside it."""
    data = json.loads((ROOT / "static" / "waste_sim" / "items.json").read_text(encoding="utf-8"))
    cfg = {"items": data["items"], "labels": {k: list(v) for k, v in wv.LABELS.items()},
           "streams": wv.STREAMS, "sure": wv.SURE_SCORE, "base": "app/static/waste_sim/"}
    page = (ROOT / "components" / "waste_rover.html").read_text(encoding="utf-8")
    return page.replace("__WR_DATA__", json.dumps(cfg).replace("</", "<\\/")), data["stats"]


heading("Watch the rover sort litter")
st.markdown('<p class="rv-lede">Our rover\'s planned waste-collection mode. Litter appears as it patrols. '
            "Its camera spots each piece, the model names it, and the rover carries it to the right bin. "
            "Click the map to drop litter yourself.</p>", unsafe_allow_html=True)
sim_html, sim_stats = waste_sim_html()
st.html(sim_html, unsafe_allow_javascript=True)
legend = "".join(f'<span><i style="background:{s["colour"]}"></i>{esc(s["name"])} bin</span>' for s in wv.STREAMS.values())
st.markdown(
    f'<div class="rv-legend">{legend}'
    '<span><i style="background:rgba(15,139,141,.35)"></i>Camera view</span>'
    '<span><i class="pt"></i>LiDAR points</span>'
    '<span><i class="ln"></i>Planned path</span>'
    '<span><i style="background:rgba(217,102,31,.45)"></i>Where it found litter</span></div>',
    unsafe_allow_html=True)
st.markdown(
    '<div class="wv-honest"><b>What is real here.</b> The mapping and path planning follow our real rover. '
    "Every litter photo is a real photo from the TACO dataset, and every label and confidence you see is what "
    "our model actually said about that photo, wrong answers included. "
    f"On all {sim_stats['n']} TACO photos we tested, the model named the material right for "
    f"{sim_stats['material']} ({sim_stats['material'] / sim_stats['n']:.0%}) and chose the right bin for "
    f"{sim_stats['stream']} ({sim_stats['stream'] / sim_stats['n']:.0%}). The bin score is higher because most "
    "litter is dry waste, so a wrong material often still lands in the dry bin. "
    "<b>What is not real yet:</b> the camera and the arm are future hardware, and the rover is sped up.</div>",
    unsafe_allow_html=True)

heading("Try the classifier on your own photo")

# ---------------- input ----------------
samples = sorted(p for p in (ROOT / "static" / "waste_samples").glob("*")
                 if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}) \
    if (ROOT / "static" / "waste_samples").exists() else []
tab_names = ["Upload a photo", "Take a photo"] + (["Try a sample"] if samples else [])
tabs = st.tabs(tab_names)
photo_bytes = None
with tabs[0]:
    up = st.file_uploader("Photo of waste", type=["jpg", "jpeg", "png", "webp"], label_visibility="collapsed")
    if up is not None:
        photo_bytes = up.getvalue()
with tabs[1]:
    cam = st.camera_input("Point the camera at the waste", label_visibility="collapsed")
    if cam is not None:
        photo_bytes = cam.getvalue()
if samples:
    with tabs[2]:
        pick = st.radio("Sample", [p.stem.split("_", 1)[-1].replace("-", " ") for p in samples],
                        horizontal=True, index=None, label_visibility="collapsed")
        if pick:
            photo_bytes = samples[[p.stem.split("_", 1)[-1].replace("-", " ") for p in samples].index(pick)].read_bytes()

if photo_bytes is None:
    st.info("Upload or take a photo to start. A clear photo of one to five items, on a plain background, works best.")
    st.stop()

# ---------------- detect (once per photo) ----------------
key = hashlib.md5(photo_bytes).hexdigest()
if st.session_state.get("wv_key") != key:
    try:
        img = Image.open(io.BytesIO(photo_bytes))
        img.load()
    except Exception:
        st.error("That file could not be opened as a photo. Try a JPG or PNG.")
        st.stop()
    with st.spinner("Looking for waste ..."):
        items = get_detector().detect(img)
    st.session_state.update(wv_key=key, wv_items=items, wv_img=img, wv_fix={}, wv_why={})

items: list = st.session_state.wv_items
fixes: dict = st.session_state.wv_fix          # item number -> class chosen by the user

if not items:
    st.image(st.session_state.wv_img, width="stretch")
    st.warning("No waste item was found in this photo. Try a closer photo with the items on a plain background.")
    st.stop()


def current_class(n: int, it) -> str:
    return fixes.get(n, it.cls)


# ---------------- tally ----------------
counts = {s: 0 for s in wv.STREAMS}
for n, it in enumerate(items, start=1):
    counts[wv.LABELS[current_class(n, it)][1]] += 1
tally = "".join(f'<div style="--c:{wv.STREAMS[s]["colour"]}"><b>{c}</b><span>{wv.STREAMS[s]["name"]}</span></div>'
                for s, c in counts.items())
st.markdown(f'<div class="wv-tally">{tally}</div>', unsafe_allow_html=True)

# ---------------- photo + items ----------------
left, right = st.columns([1.15, 1], gap="large")
with left:
    drawn = wv.draw(st.session_state.wv_img, items)
    drawn.thumbnail((1400, 1400))
    buf = io.BytesIO()
    drawn.save(buf, "JPEG", quality=85)
    b64 = base64.b64encode(buf.getvalue()).decode()
    st.markdown(f'<div class="wv-shot"><img src="data:image/jpeg;base64,{b64}" '
                f'alt="The photo with a numbered box around each waste item"></div>', unsafe_allow_html=True)
    st.caption("Solid box: the model is sure. Dashed box: it is not sure, so please check that item.")

with right:
    for n, it in enumerate(items, start=1):
        cls = current_class(n, it)
        label, stream = wv.LABELS[cls]
        s = wv.STREAMS[stream]
        corrected = n in fixes and fixes[n] != it.cls
        conf_text = "you corrected this" if corrected else f"{it.score:.0%} sure"
        unsure = "" if (it.sure or n in fixes) else '<div class="unsure">Not sure. Please confirm below.</div>'
        st.markdown(
            f'<div class="wv-item" style="--c:{s["colour"]}"><div class="n">{n}</div><div>'
            f'<div class="lab">{esc(label)}</div><span class="chip">{esc(s["name"])}</span>'
            f'<span class="conf">{conf_text}</span>'
            f'<div class="bar"><i style="width:{100 if corrected else round(it.score * 100)}%"></i></div>'
            f'{unsure}</div></div>', unsafe_allow_html=True)

        c1, c2 = st.columns([1.4, 1])
        options = list(wv.LABELS)
        needs_check = not it.sure and n not in fixes
        box = c1 if needs_check else c1.expander("Wrong label?")
        choice = box.selectbox(f"What is item {n}?", options, index=options.index(cls),
                               format_func=lambda c: wv.LABELS[c][0], key=f"fix_{key}_{n}")
        if choice != cls:
            fixes[n] = choice
            st.rerun()
        if needs_check and c1.button("Yes, that's right", key=f"ok_{key}_{n}"):
            fixes[n] = it.cls
            st.rerun()
        if c2.button("Why?", key=f"why_{key}_{n}", width="stretch"):
            q = wv.WHY_QUESTIONS[cls]
            if q not in st.session_state.wv_why:
                with st.spinner("Checking the rules ..."):
                    try:
                        st.session_state.wv_why[q] = rag.answer(get_rules(), q)
                    except Exception as e:
                        st.session_state.wv_why[q] = {"error": str(e)}
            st.session_state.wv_open = q
        st.write("")


# ---------------- the rule behind it ----------------
def badge(check: dict) -> str:
    status = check["status"]
    if status == "verified":
        return '<span class="rv-badge rv-ok">✓ Every number found in the cited rule</span>'
    if status == "unverified":
        miss = ", ".join(str(m) for m in check["missing"])
        return f'<span class="rv-badge rv-warn">⚠ Not found in the rules: {esc(miss)}. Check before using.</span>'
    if status == "refused":
        return '<span class="rv-badge rv-info">Not covered by the rules we have</span>'
    if status == "no_llm":
        return '<span class="rv-badge rv-info">Passage only, no language model set</span>'
    return '<span class="rv-badge rv-info">No numbers to check</span>'


open_q = st.session_state.get("wv_open")
if open_q and open_q in st.session_state.wv_why:
    res = st.session_state.wv_why[open_q]
    st.markdown('<h2 class="rv-h">What the rules say</h2>', unsafe_allow_html=True)
    st.markdown(f'<p class="rv-lede">{esc(open_q)}</p>', unsafe_allow_html=True)
    if "error" in res:
        st.error(f"The language model call failed. {res['error']}")
    else:
        st.markdown(res["answer"])
        st.markdown(badge(res["check"]), unsafe_allow_html=True)
        hits, cited = res["hits"], res["cited"]
        if res["check"]["status"] != "refused":
            chips = "".join(f'<span class="rv-src{" on" if i in cited else ""}">[{i}] {esc(c.label)}</span>'
                            for i, (c, _) in enumerate(hits, start=1))
            st.markdown(chips, unsafe_allow_html=True)
            with st.expander("Show the rule passages"):
                for i, (c, score) in enumerate(hits, start=1):
                    st.markdown(f"**[{i}] {c.label}**, match {score:.2f}, {'cited' if i in cited else 'found, not cited'}")
                    st.text(c.text)
            first = next((hits[i - 1][0] for i in cited if hits[i - 1][0].source_type == "rules"), None)
            if first is not None:
                with st.expander(f"See the page: {first.part}, page {first.page}"):
                    st.image(rag.page_image(first.source, first.page, [], kb=rag.WASTE), width="stretch")

st.caption("WasteVision gives general guidance from the central rules. Your city may have its own "
           "collection days and bin colours, so follow your local body's instructions too.")
