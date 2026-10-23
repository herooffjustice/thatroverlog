"""Page 1: the rover showcase. Run with:  streamlit run Home.py"""

import csv
import tomllib
from collections import OrderedDict

import streamlit as st

from ui import (AMBER, BLUE, PATH, PHASE_COLOURS, PIPE_COLOURS, RESULT_COLOURS, ROOT, STATUS_COLOURS,
                caption_from_name, esc, frame, heading, photo_files, rail_gradient, setup, static_url)

setup("Autonomous Mobile Rover")

with open(ROOT / "site.toml", "rb") as f:
    site = tomllib.load(f)

# ---------------- top ----------------
st.markdown(
    f'<div class="rv-kicker">{esc(site["kicker"])}</div>'
    f'<h1 class="rv-title">{esc(site["name"])}</h1>'
    f'<div class="rv-tag">{esc(site["tagline"])}</div>', unsafe_allow_html=True)

# The live map: a small browser version of what the rover does (scan, map, plan, drive).
st.html((ROOT / "components" / "lidar_map.html").read_text(encoding="utf-8"), unsafe_allow_javascript=True)
st.markdown(
    '<div class="rv-legend">'
    '<span><i style="background:#161D21"></i>Wall, seen by the LiDAR</span>'
    '<span><i style="background:#F7F8F4"></i>Free space</span>'
    '<span><i style="background:#CDD0C8"></i>Not seen yet</span>'
    '<span><i style="background:#F4E4E7"></i>Safety zone</span>'
    '<span><i class="pt"></i>LiDAR points</span>'
    '<span><i class="ln"></i>Planned path</span>'
    '</div>'
    f'<div class="rv-note">{esc(site["map_note"])}</div>', unsafe_allow_html=True)

specs = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in site["specs"])
st.markdown(f'<div class="rv-about"><p>{esc(site["intro"].strip())}</p>'
            f'<dl class="rv-specs">{specs}</dl></div>', unsafe_allow_html=True)
st.write("")
c1, c2 = st.columns([1, 1.6])
c1.page_link("pages/1_Ask_the_Rover.py", label="Ask a question about the rover", icon="💬")
c2.page_link("pages/2_WasteVision.py", label="Also from our team: WasteVision, waste sorting from a photo", icon="♻️")

# ---------------- photos of the finished rover ----------------
photos = photo_files("photos")
if photos:
    heading("The rover")
    figs = "".join(frame(static_url("photos", p.name), caption_from_name(p), PATH) for p in photos)
    st.markdown(f'<div class="rv-gallery{" one" if len(photos) == 1 else ""}">{figs}</div>', unsafe_allow_html=True)

# ---------------- results ----------------
heading("Results on the real rover")
res = "".join(f'<div style="--c:{RESULT_COLOURS[i % len(RESULT_COLOURS)]}"><b>{esc(a)}</b><span>{esc(b)}</span></div>'
              for i, (a, b) in enumerate(site["results"]))
st.markdown(f'<div class="rv-results">{res}</div><div class="rv-note">{esc(site["results_note"])}</div>',
            unsafe_allow_html=True)

# ---------------- how it works ----------------
heading("How it works")
steps = "".join(
    f'<div style="--c:{PIPE_COLOURS[(i - 1) % len(PIPE_COLOURS)]}"><span class="n">{i}</span>'
    f'<div class="t">{esc(t)}</div><div class="d">{esc(d)}</div></div>'
    for i, (t, d) in enumerate(site["pipeline"], start=1))
st.markdown(f'<div class="rv-pipe">{steps}</div>', unsafe_allow_html=True)

# ---------------- sim to real ----------------
heading("What the simulation never showed")
st.markdown('<p class="rv-lede">The same software worked in simulation first. '
            "These problems only appeared once we built and drove the real rover.</p>", unsafe_allow_html=True)
rows = "".join(f'<div class="row"><div class="p">{esc(p)}</div><div class="f">{esc(f)}</div></div>'
               for p, f in site["lessons"])
st.markdown('<div class="rv-ledger"><div class="row head"><div>On the real rover</div><div>What we did</div></div>'
            f'{rows}</div>', unsafe_allow_html=True)

# ---------------- videos ----------------
videos = [v for v in site.get("videos", []) if v.get("url")]
if videos:
    heading("Videos")
    cols = st.columns(min(len(videos), 2))
    for i, v in enumerate(videos):
        with cols[i % len(cols)]:
            st.video(v["url"])
            st.caption(v["title"])

# ---------------- workflow ----------------
heading("How we built it")
st.markdown('<p class="rv-lede">The order we worked in, from the first simulation to the final run.</p>',
            unsafe_allow_html=True)
with open(ROOT / "data" / "log.csv", encoding="utf-8") as f:
    log = list(csv.DictReader(f))

by_phase: "OrderedDict[str, list]" = OrderedDict()
for r in log:
    by_phase.setdefault(r["phase"], []).append(r)


def item_photos(r: dict, colour: str) -> str:
    """Photos for one item: file names in the "photos" column and captions in the "captions"
    column, each separated by ";". The files live in static/workflow/"""
    names = [n.strip() for n in (r.get("photos") or "").split(";")]
    caps = [c.strip() for c in (r.get("captions") or "").split(";")]
    figs = []
    for i, n in enumerate(names):
        if not n or not (ROOT / "static" / "workflow" / n).exists():
            continue
        cap = caps[i] if i < len(caps) and caps[i] else caption_from_name(ROOT / n)
        figs.append(frame(static_url("workflow", n), cap, colour, label=f'{r["no"]}.'))
    return f'<div class="rv-shots">{"".join(figs)}</div>' if figs else ""


sections, weights, colours = [], [], []
for k, (phase, items) in enumerate(by_phase.items()):
    colour = PHASE_COLOURS[k % len(PHASE_COLOURS)]
    parts = [f'<div class="rv-phase"><span class="mk"></span><span class="tag">{esc(phase)}</span></div>']
    weight = 0.6                                    # the phase label itself
    for r in items:
        shots = item_photos(r, colour)
        weight += 3.5 if shots else 1               # items with photos are taller
        parts.append(
            f'<div class="rv-item{" has-shots" if shots else ""}"><div class="txt">'
            f'<span class="no">{esc(r["no"])}.</span><span class="rv-wp"></span>'
            f'<div class="hd"><span class="ttl">{esc(r["title"])}</span>'
            f'<span class="st" style="--sc:{STATUS_COLOURS.get(r["status"], "#566166")}">{esc(r["status"])}</span></div>'
            f'<div class="det">{esc(r["details"])}</div></div>{shots}</div>')
    sections.append(f'<section class="rv-ph" style="--pc:{colour}">{"".join(parts)}</section>')
    weights.append(weight)
    colours.append(colour)

st.markdown(f'<div class="rv-flow" style="--railgrad:{rail_gradient(weights, colours)}">{"".join(sections)}</div>',
            unsafe_allow_html=True)

# ---------------- status ----------------
heading("Where it stands now")
cols = "".join(
    f'<div style="--c:{c}"><h4>{head}</h4><ul>{"".join(f"<li>{esc(i)}</li>" for i in items)}</ul></div>'
    for head, items, c in (("Working", site["working"], PATH), ("In progress", site["in_progress"], BLUE),
                           ("Paused", site["paused"], AMBER)))
st.markdown(f'<div class="rv-status">{cols}</div>', unsafe_allow_html=True)

st.markdown(
    f'<div class="rv-foot"><div>{esc(", ".join(site["team"]))}<br>Guide: {esc(site["guide"])}</div>'
    f'<div>{esc(site["college"])}</div></div>', unsafe_allow_html=True)
