"""Shared look for both pages.

Design idea: the site looks like the rover's own map. The page is map paper with a faint
grid, walls and text are dark ink, LiDAR points are red and Nav2's path is green. The
"signal" gradient (red -> green) is the data flowing from the LiDAR to the wheels. Each
phase of the build has its own colour, like regions on a map, and photos sit in frames
with corner marks like a robot's detection box.
"""

import html
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent

PAPER = "#EEEFEA"     # map paper
PANEL = "#F7F8F4"     # free space on the map
UNKNOWN = "#CDD0C8"   # not seen yet
INK = "#161D21"       # walls, text
MUTED = "#566166"
LINE = "#D2D5CD"
PATH = "#1E8F55"      # Nav2 path green
PATH_TEXT = "#17744A" # darker green for text (better contrast)
SCAN = "#D3263E"      # LiDAR points red
SCAN_TEXT = "#B81F35"
ORANGE = "#D9661F"
GOLD = "#B8860B"
AMBER = "#C77D0A"
TEAL = "#0F8B8D"
BLUE = "#2E6FD8"
VIOLET = "#6C4AB6"

SIGNAL = f"linear-gradient(90deg, {SCAN}, {ORANGE}, {GOLD}, {TEAL}, {PATH})"   # LiDAR -> wheels
PIPE_COLOURS = [SCAN, ORANGE, GOLD, TEAL, PATH]
PHASE_COLOURS = [VIOLET, AMBER, TEAL, BLUE, SCAN, PATH]
RESULT_COLOURS = [PATH, AMBER, BLUE, VIOLET]

STATUS_COLOURS = {
    "Done": PATH_TEXT,
    "Fixed": PATH_TEXT,
    "Problem found": SCAN_TEXT,
    "In progress": "#2459B0",
    "Paused": "#8A5A00",
}

FONTS = ("https://fonts.googleapis.com/css2?"
         "family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,400..800"
         "&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400"
         "&family=Source+Serif+4:ital,opsz,wght@1,8..60,400;1,8..60,500&display=swap")

CSS = f"""
<style>
@import url('{FONTS}');
:root {{ --rv-line: {LINE}; }}

/* ---------- page ---------- */
.stApp {{
  background-color: {PAPER};
  background-image:
    linear-gradient(to right, rgba(22,29,33,.045) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(22,29,33,.045) 1px, transparent 1px);
  background-size: 40px 40px;
  color: {INK};
}}
[data-testid="stHeader"] {{ background: rgba(238, 239, 234, .88); backdrop-filter: blur(6px); }}
[data-testid="stSidebar"] {{ background: {PANEL}; border-right: 1px solid {LINE}; }}
[data-testid="stSidebar"]::before {{ content: ""; position: absolute; left: 0; right: 0; top: 0; height: 4px; background: {SIGNAL}; }}
.block-container {{ max-width: 1120px; padding-top: 2.4rem; padding-bottom: 5rem; }}
html, body, .stMarkdown, p, li, label {{ font-family: 'Source Sans 3', system-ui, sans-serif; }}
.stMarkdown p, .stMarkdown li {{ font-size: 1.04rem; line-height: 1.6; text-wrap: pretty; }}
a {{ color: {PATH_TEXT}; }}

h2.rv-h {{ font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-variation-settings: "wdth" 88;
  font-size: clamp(1.7rem, 3.2vw, 2.3rem); line-height: 1.05; letter-spacing: -0.02em;
  margin: 4.4rem 0 1.1rem; padding: 0; text-wrap: balance; color: {INK}; }}
h2.rv-h::after {{ content: ""; display: block; width: 64px; height: 5px; margin-top: .7rem; border-radius: 3px;
  background: {SIGNAL}; }}
.rv-lede {{ color: {MUTED}; font-size: 1.08rem; line-height: 1.55; max-width: 60ch; margin: -.2rem 0 1.4rem; text-wrap: pretty; }}

/* ---------- top ---------- */
.rv-kicker {{ color: {MUTED}; font-size: .98rem; margin-bottom: .9rem; display: flex; align-items: center; gap: .6rem; }}
.rv-kicker::before {{ content: ""; width: 26px; height: 5px; border-radius: 3px; background: {SIGNAL}; flex: none; }}
h1.rv-title, .rv-title {{ font-family: 'Bricolage Grotesque', sans-serif !important; font-weight: 800 !important;
  font-variation-settings: "wdth" 84; font-size: clamp(3.1rem, 9.2vw, 6.8rem) !important; line-height: .9 !important;
  letter-spacing: -0.022em !important; margin: 0 !important; padding: 0 !important; color: {INK}; text-wrap: balance; }}
.rv-tag {{ font-size: clamp(1.15rem, 2.2vw, 1.45rem); line-height: 1.4; max-width: 38ch; margin: 1.1rem 0 1.6rem;
  color: {INK}; text-wrap: balance; }}

.rv-legend {{ display: flex; flex-wrap: wrap; gap: .45rem 1.3rem; margin: .8rem 0 0; font-size: .92rem; color: {MUTED}; }}
.rv-legend span {{ display: inline-flex; align-items: center; gap: .45rem; }}
.rv-legend i {{ display: inline-block; width: 14px; height: 14px; border: 1px solid rgba(22,29,33,.25); }}
.rv-legend i.pt {{ width: 7px; height: 7px; border-radius: 50%; border: 0; background: {SCAN}; }}
.rv-legend i.ln {{ width: 18px; height: 3px; border: 0; background: {PATH}; border-radius: 2px; }}

.rv-about {{ display: grid; grid-template-columns: 1.15fr 1fr; gap: 2.4rem; margin-top: 2.2rem; align-items: start; }}
.rv-about p {{ margin: 0; font-size: 1.06rem; line-height: 1.65; color: {INK}; max-width: 58ch; text-wrap: pretty; }}
.rv-specs {{ display: grid; grid-template-columns: max-content 1fr; margin: 0; padding-top: 5px;
  background: {SIGNAL} top / 100% 5px no-repeat; }}
.rv-specs dt, .rv-specs dd {{ padding: .5rem 0; border-bottom: 1px solid {LINE}; margin: 0; font-size: .98rem; }}
.rv-specs dt {{ color: {MUTED}; padding-right: 1.4rem; }}
.rv-specs dd {{ font-weight: 600; }}
@media (max-width: 760px) {{ .rv-about {{ grid-template-columns: 1fr; gap: 1.4rem; }} }}

/* ---------- photo frames: a print on the map, with detection-box corners ---------- */
.rv-frame {{ position: relative; display: block; padding: 7px; background: #FFFFFF; border: 1px solid {LINE};
  box-shadow: 8px 8px 0 0 color-mix(in srgb, var(--pc, {PATH}) 32%, transparent);
  transition: transform .18s ease, box-shadow .18s ease; }}
.rv-frame img {{ display: block; width: 100%; height: auto; background: {UNKNOWN}; }}
.rv-frame::after {{ content: ""; position: absolute; inset: -7px; pointer-events: none;
  --c: var(--pc, {PATH}); --l: 22px; --w: 3px;
  background:
    linear-gradient(var(--c), var(--c)) left top / var(--l) var(--w) no-repeat,
    linear-gradient(var(--c), var(--c)) left top / var(--w) var(--l) no-repeat,
    linear-gradient(var(--c), var(--c)) right top / var(--l) var(--w) no-repeat,
    linear-gradient(var(--c), var(--c)) right top / var(--w) var(--l) no-repeat,
    linear-gradient(var(--c), var(--c)) left bottom / var(--l) var(--w) no-repeat,
    linear-gradient(var(--c), var(--c)) left bottom / var(--w) var(--l) no-repeat,
    linear-gradient(var(--c), var(--c)) right bottom / var(--l) var(--w) no-repeat,
    linear-gradient(var(--c), var(--c)) right bottom / var(--w) var(--l) no-repeat; }}
.rv-frame .lbl {{ position: absolute; left: 15px; top: 15px; background: var(--pc, {PATH}); color: #FFFFFF;
  font: 700 .78rem/1.5 'Source Sans 3', sans-serif; padding: 1px 8px; font-variant-numeric: tabular-nums; }}
.rv-frame:focus-visible {{ outline: 3px solid var(--pc, {PATH}); outline-offset: 10px; }}
@media (hover: hover) and (prefers-reduced-motion: no-preference) {{
  .rv-frame:hover {{ transform: translate(-3px, -3px);
    box-shadow: 11px 11px 0 0 color-mix(in srgb, var(--pc, {PATH}) 48%, transparent); }} }}
figcaption {{ font-family: 'Source Serif 4', serif; font-style: italic; font-size: .93rem; line-height: 1.45;
  color: {MUTED}; margin-top: .85rem; text-wrap: pretty; }}

.rv-gallery {{ display: grid; grid-template-columns: repeat(6, 1fr); grid-auto-rows: 240px; gap: 22px; }}
.rv-gallery figure {{ margin: 0; grid-column: span 2; display: flex; flex-direction: column; min-height: 0; }}
.rv-gallery figure:first-child {{ grid-column: span 4; grid-row: span 2; }}
.rv-gallery .rv-frame {{ flex: 1; min-height: 0; display: flex; }}
.rv-gallery .rv-frame img {{ height: 100%; object-fit: cover; }}
.rv-gallery.one {{ grid-template-columns: 1fr; grid-auto-rows: auto; }}
.rv-gallery.one figure {{ grid-column: auto; grid-row: auto; }}
.rv-gallery.one .rv-frame img {{ aspect-ratio: 16 / 9; height: auto; }}
@media (max-width: 760px) {{ .rv-gallery {{ grid-template-columns: 1fr; grid-auto-rows: auto; }}
  .rv-gallery figure, .rv-gallery figure:first-child {{ grid-column: auto; grid-row: auto; }}
  .rv-gallery .rv-frame img {{ aspect-ratio: 4 / 3; height: auto; }} }}

/* ---------- results ---------- */
.rv-results {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }}
.rv-results > div {{ --c: {PATH}; padding: 1rem 1.1rem 1.15rem; background: color-mix(in srgb, var(--c) 7%, {PANEL});
  border-top: 5px solid var(--c); }}
.rv-results b {{ display: block; font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700;
  font-variation-settings: "wdth" 80; font-size: clamp(2.2rem, 4.2vw, 3.3rem); line-height: 1;
  letter-spacing: -0.02em; font-variant-numeric: tabular-nums; margin-bottom: .5rem;
  color: color-mix(in srgb, var(--c) 78%, #000); }}
.rv-results span {{ color: {MUTED}; font-size: .95rem; line-height: 1.45; display: block; }}
.rv-note {{ color: {MUTED}; font-size: .95rem; margin-top: 1rem; max-width: 75ch; line-height: 1.55; }}
@media (max-width: 760px) {{ .rv-results {{ grid-template-columns: 1fr 1fr; }} }}
@media (max-width: 420px) {{ .rv-results {{ grid-template-columns: 1fr; }} }}

/* ---------- pipeline (a real sequence, so numbered) ---------- */
.rv-pipe {{ display: grid; grid-template-columns: repeat(5, 1fr); padding-top: 6px;
  background: {SIGNAL} top / 100% 6px no-repeat; }}
.rv-pipe > div {{ --c: {PATH}; padding: 1rem 1.1rem 1rem 0; }}
.rv-pipe > div + div {{ padding-left: 1.1rem; border-left: 1px solid {LINE}; }}
.rv-pipe .n {{ display: inline-flex; align-items: center; justify-content: center; width: 1.7rem; height: 1.7rem;
  border-radius: 50%; background: var(--c); color: #FFFFFF; font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700; font-size: .95rem; font-variant-numeric: tabular-nums; }}
.rv-pipe .t {{ font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.12rem; margin: .55rem 0 .35rem;
  color: color-mix(in srgb, var(--c) 72%, #000); }}
.rv-pipe .d {{ color: {MUTED}; font-size: .95rem; line-height: 1.5; }}
@media (max-width: 820px) {{ .rv-pipe {{ grid-template-columns: 1fr; }}
  .rv-pipe > div + div {{ border-left: 0; padding-left: 0; border-top: 1px solid {LINE}; }} }}

/* ---------- sim-to-real ---------- */
.rv-ledger .row {{ display: grid; grid-template-columns: 1fr 1.35fr; gap: 1.6rem; padding: .85rem 0;
  border-bottom: 1px solid {LINE}; align-items: baseline; }}
.rv-ledger .head {{ font-size: .9rem; font-weight: 600; padding: .5rem 0; border-bottom: 2px solid {INK}; }}
.rv-ledger .head div:first-child {{ color: {SCAN_TEXT}; }}
.rv-ledger .head div:last-child {{ color: {PATH_TEXT}; }}
.rv-ledger .p {{ color: {SCAN_TEXT}; font-weight: 600; padding-left: 1.2rem; position: relative; }}
.rv-ledger .p::before {{ content: ""; position: absolute; left: 0; top: .5em; width: 8px; height: 8px; border-radius: 50%;
  background: {SCAN}; }}
.rv-ledger .f {{ padding-left: 1.6rem; position: relative; }}
.rv-ledger .f::before {{ content: "✓"; position: absolute; left: 0; top: 0; color: {PATH}; font-weight: 700; }}
@media (max-width: 640px) {{ .rv-ledger .row {{ grid-template-columns: 1fr; gap: .3rem; }}
  .rv-ledger .head {{ display: none; }} }}

/* ---------- workflow: drawn like a Nav2 path with waypoints ----------
   Every marker is placed from the same two numbers, so they always sit exactly on the line:
   --rail = where the line's centre is, --gut = where the text starts. */
.rv-flow {{ --rail: 3.2rem; --gut: 5.2rem; position: relative; padding-left: var(--gut); view-timeline-name: --flow; }}
.rv-flow::before, .rv-flow::after {{ content: ""; position: absolute; left: calc(var(--rail) - 2px); top: 1.3rem;
  bottom: 1.3rem; width: 4px; border-radius: 2px; }}
.rv-flow::before {{ background: {UNKNOWN}; }}
.rv-flow::after {{ background: var(--railgrad, {PATH}); }}
@supports (animation-timeline: view()) {{
  @media (prefers-reduced-motion: no-preference) {{
    .rv-flow::after {{ animation: rv-grow linear both; animation-timeline: --flow; animation-range: entry 10% exit 55%; }}
    .rv-wp {{ animation: rv-pass linear both; animation-timeline: view(); animation-range: cover 30% cover 45%; }}
  }}
}}
@keyframes rv-grow {{ from {{ clip-path: inset(0 0 100% 0); }} to {{ clip-path: inset(0 0 0 0); }} }}
@keyframes rv-pass {{ from {{ background: {PAPER}; border-color: {UNKNOWN}; }} to {{ background: var(--pc); border-color: var(--pc); }} }}

.rv-ph {{ --pc: {PATH}; }}
.rv-phase {{ position: relative; display: flex; align-items: center; min-height: 2.6rem; margin: 2.6rem 0 .9rem; }}
.rv-ph:first-child .rv-phase {{ margin-top: 0; }}
.rv-phase .mk {{ position: absolute; left: calc(var(--rail) - var(--gut)); top: 50%; width: 16px; height: 16px;
  border-radius: 2px; background: var(--pc); box-shadow: 0 0 0 4px {PAPER};
  transform: translate(-50%, -50%) rotate(45deg); }}
.rv-phase .tag {{ font-family: 'Source Serif 4', serif; font-style: italic; font-weight: 500; font-size: 1.28rem;
  line-height: 1.5; padding: .15rem .85rem .2rem; border-left: 4px solid var(--pc);
  background: color-mix(in srgb, var(--pc) 13%, transparent); color: color-mix(in srgb, var(--pc) 62%, #000); }}

.rv-item {{ position: relative; padding: .5rem 0 1.25rem; }}
.rv-item .no {{ position: absolute; left: calc(var(--rail) - var(--gut) - 1.15rem); top: .5rem;
  transform: translateX(-100%); line-height: 1.5rem; font-family: 'Bricolage Grotesque', sans-serif;
  font-weight: 700; font-size: 1.02rem; color: {MUTED}; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.rv-wp {{ position: absolute; left: calc(var(--rail) - var(--gut)); top: 1.25rem; width: 14px; height: 14px;
  border-radius: 50%; box-sizing: border-box; background: var(--pc); border: 3px solid var(--pc);
  box-shadow: 0 0 0 4px {PAPER}; transform: translate(-50%, -50%); }}
.rv-item .ttl {{ font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; font-size: 1.16rem; line-height: 1.5rem; }}
.rv-item .hd {{ display: flex; flex-wrap: wrap; align-items: center; gap: .3rem .6rem; min-height: 1.5rem; }}
.rv-item .st {{ display: inline-block; font-size: .82rem; font-weight: 700; padding: 0 .5rem;
  line-height: 1.35rem; border-radius: 3px; white-space: nowrap;
  color: var(--sc); background: color-mix(in srgb, var(--sc) 11%, transparent); }}
.rv-item .det {{ color: {MUTED}; font-size: 1rem; line-height: 1.58; margin-top: .3rem; max-width: 70ch; text-wrap: pretty; }}
.rv-item.has-shots {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(220px, 330px); column-gap: 2.4rem;
  align-items: start; padding-bottom: 2rem; }}
.rv-shots {{ display: grid; gap: 22px; padding: 7px 8px 0 0; }}
.rv-shots figure {{ margin: 0; }}
@media (max-width: 900px) {{ .rv-item.has-shots {{ display: block; }}
  .rv-shots {{ grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); margin-top: 1rem; max-width: 520px; }} }}
@media (max-width: 640px) {{ .rv-flow {{ --rail: .95rem; --gut: 2.5rem; }}
  .rv-item .no {{ position: static; transform: none; display: inline; margin-right: .3rem; }}
  .rv-item .hd {{ display: inline; }} .rv-item .hd .st {{ margin-left: .45rem; }}
  .rv-shots {{ padding-left: 7px; padding-right: 12px; }} }}

/* ---------- status + footer ---------- */
.rv-status {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }}
.rv-status > div {{ --c: {PATH}; padding: .9rem 1.1rem 1rem; border-top: 5px solid var(--c);
  background: color-mix(in srgb, var(--c) 7%, {PANEL}); }}
.rv-status h4 {{ font-family: 'Bricolage Grotesque', sans-serif; font-size: 1.1rem; margin: 0 0 .5rem; padding: 0;
  color: color-mix(in srgb, var(--c) 72%, #000); }}
.rv-status ul {{ margin: 0; padding-left: 1.1rem; }}
.rv-status li {{ margin: .25rem 0; line-height: 1.45; text-wrap: wrap; }}
.rv-status li::marker {{ color: var(--c); }}
@media (max-width: 760px) {{ .rv-status {{ grid-template-columns: 1fr; }} }}
.rv-foot {{ margin-top: 5rem; padding-top: 1.2rem; color: {MUTED}; font-size: .95rem; position: relative;
  display: flex; flex-wrap: wrap; justify-content: space-between; gap: 1rem; }}
.rv-foot::before {{ content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px; background: {SIGNAL}; opacity: .7; }}

/* ---------- ask page ---------- */
h1.rv-ask-title {{ font-family: 'Bricolage Grotesque', sans-serif !important; font-weight: 800 !important;
  font-variation-settings: "wdth" 84; font-size: clamp(2.8rem, 7vw, 4.8rem) !important; line-height: .9 !important;
  letter-spacing: -0.02em !important; margin: 0 0 .9rem !important; padding: 0 !important; color: {INK}; }}
.rv-badge {{ display: inline-block; font-size: .86rem; font-weight: 600; padding: .2rem .65rem;
  border-radius: 3px; margin: .3rem 0 .5rem; }}
.rv-ok {{ background: #E1F0E6; color: {PATH_TEXT}; }}
.rv-warn {{ background: #F8E2E5; color: {SCAN_TEXT}; }}
.rv-info {{ background: #E4E6E0; color: {MUTED}; }}
.rv-src {{ display: inline-block; font-size: .86rem; padding: .12rem .55rem; margin: 0 .35rem .35rem 0;
  border-radius: 3px; background: {PANEL}; border: 1px solid {LINE}; color: {MUTED}; }}
.rv-src.on {{ border-color: {PATH}; box-shadow: inset 3px 0 0 {PATH}; font-weight: 600; color: {INK}; }}
[data-testid="stChatMessage"] {{ background: {PANEL}; border: 1px solid {LINE}; border-radius: 4px; }}
[data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] {{ background: {PAPER}; }}
[data-testid="stExpander"] details {{ background: {PANEL}; border-color: {LINE}; border-radius: 4px; }}
</style>
"""


def setup(title: str, icon: str = "🛰️") -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


def esc(text) -> str:
    return html.escape(str(text))


def heading(text: str) -> None:
    st.markdown(f'<h2 class="rv-h">{esc(text)}</h2>', unsafe_allow_html=True)


def frame(url: str, caption: str, colour: str = PATH, label: str = "") -> str:
    """One photo in a frame with detection-box corners. Clicking opens the full-size photo."""
    lbl = f'<span class="lbl">{esc(label)}</span>' if label else ""
    return (f'<figure style="--pc:{colour}"><a class="rv-frame" href="{url}" target="_blank" rel="noopener">'
            f'<img src="{url}" alt="{esc(caption)}" loading="lazy">{lbl}</a>'
            f'<figcaption>{esc(caption)}</figcaption></figure>')


def rail_gradient(weights: list[float], colours: list[str]) -> str:
    """Colour the workflow line phase by phase, blending at the borders between phases."""
    total = sum(weights) or 1
    stops, start = [], 0.0
    for w, c in zip(weights, colours):
        end = start + w / total * 100
        pad = (end - start) * 0.2
        stops += [f"{c} {start + pad:.1f}%", f"{c} {end - pad:.1f}%"]
        start = end
    return "linear-gradient(to bottom, " + ", ".join(stops) + ")"


def photo_files(folder: str) -> list[Path]:
    """Photos in static/<folder>, sorted by name."""
    d = ROOT / "static" / folder
    if not d.exists():
        return []
    return sorted(p for p in d.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})


def caption_from_name(p: Path) -> str:
    """'03_lidar-mount.jpg' -> 'lidar mount'."""
    stem = p.stem.split("_", 1)[-1] if "_" in p.stem else p.stem
    return stem.replace("-", " ").replace("_", " ").strip()


def static_url(folder: str, name: str) -> str:
    """Files in the static/ folder are served by Streamlit at app/static/..."""
    return f"app/static/{folder}/{name}"
