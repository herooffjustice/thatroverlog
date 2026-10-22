# Autonomous Mobile Rover: website and "Ask the Rover" assistant

A two-page website for our LiDAR rover, built for the GAT Hack Hour "From Text to Insight" (22 Oct 2026).

- **Home:** a live map you can click (a small browser version of what the rover does: scan, map, plan, drive), what the rover is, results from the real robot, what the simulation never showed, and our workflow from the first simulation to the final run.
- **Ask the Rover:** a RAG (Retrieval-Augmented Generation) assistant. Ask a question in plain English. It answers only from our build notes, our workflow and the datasheets of the parts on the rover, shows the source of every answer, and says "I don't know" when the data does not have the answer.

## How an answer is made

| Step | What happens |
|---|---|
| 1. Ingest | Datasheet PDFs are read with `pdfplumber`. **Each table row becomes one full sentence** (for example: *"TB6612FNG (page 3) - Characteristics: Output current; Symbol: Iout (peak); Rating: 3.2"*), so a number never gets separated from its label. Notes are split by heading. Each item of our workflow is one piece. |
| 2. Retrieve | Two searches run together: **BM25** (exact keywords, good for part numbers and error messages) and **embeddings** (`all-MiniLM-L6-v2`, good for questions worded differently from the notes). Their scores are mixed (70% meaning, 30% keywords). If the question names a part, the other parts' datasheets are left out. |
| 3. Refuse early | If even the best match is weak (similarity below 0.25), the app says "I don't know" without calling the language model. |
| 4. Generate | The language model (Groq's `openai/gpt-oss-120b` by default, or Gemini) gets the top 6 passages and must answer only from them, with `[n]` citations. If Groq retires the model, the app asks Groq which models the key can use and picks one by itself. |
| 5. Number check | Every number in the answer is checked against the passages it cites. Green badge if all are found, red warning if not. |
| 6. Show the page | For datasheet answers, the real PDF page is shown with the numbers highlighted. |

## Search test (`python evaluate.py`)

20 questions where we know which source holds the answer. Success = the right source is in the top 3 results.

| Method | Correct source in top 3 |
|---|---|
| BM25 only | 17/20 (85%) |
| Embeddings only | 16/20 (80%) |
| **Both (hybrid)** | **19/20 (95%)** |

Honest note: this is a small test set, and the 70/30 weight was chosen on these same questions, so the real accuracy on new questions may be lower.

## Run it on your laptop (Windows)

1. Install Python 3.11 or newer.
2. Open a terminal in this folder and run:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Get a free API key from Groq (https://console.groq.com/keys) or Google AI Studio (https://aistudio.google.com/apikey).
4. Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste the key.
5. Run:
   ```
   streamlit run Home.py
   ```
   The first start downloads the small embedding model (about 90 MB) and reads all PDFs, so it takes about a minute. After that it starts in seconds.

Without a key, the app still works, but shows the best matching passages instead of a written answer.

## Add your photos and videos

Use real photos only. Resize each to about 1600 px wide first, so the page loads fast.

- **Rover photos** (the "The rover" section): put them in `static/photos/`. They appear in name order, and the first one is shown large. The part after the first `_` becomes the caption, so `1_front-view.jpg` shows "front view". 3, 5 or 7 photos fill the layout best.
- **Workflow photos:** put them in `static/workflow/`, then open `data/log.csv` and write the file name in the `photos` column of that item, and a short caption in the `captions` column. For more than one photo, separate the names (and the captions, in the same order) with `;`, for example `cable-soldering.jpg; cable-test.jpg`. The photos appear next to that item, and clicking one opens it full size.
- **Videos:** upload to YouTube as *Unlisted* and paste the links in `site.toml` under `[[videos]]`.
- **Text:** all home page text is in `site.toml`. The workflow is in `data/log.csv` (open it in Excel). Keep the `no` column in order. After changing the workflow or notes, the assistant re-reads them on the next start.

## Put it online (Streamlit Community Cloud, free)

1. Upload this folder to a GitHub repository. `secrets.toml` is in `.gitignore`, so your key stays private.
2. Go to https://share.streamlit.io, choose the repository and set the main file to `Home.py`.
3. In the app's **Settings → Secrets**, paste the same lines as your `secrets.toml`.
4. Set a spending limit on your API account, since anyone with the link can ask questions.

A free app sleeps when nobody uses it and takes about a minute to wake up.

## Design

The site is drawn like the rover's own map: map paper with a faint grid, dark walls, Nav2's green for paths and red for LiDAR points. The live map at the top (`components/lidar_map.html`) is plain JavaScript: it ray-casts a 360° scan 7 times a second, fills an occupancy grid, plans with A* around a safety zone and follows the path. The green line beside "How we built it" fills as you scroll, like the rover moving along its path (in browsers that support CSS scroll-driven animations; others show it full).

## Data

| Source | What it is |
|---|---|
| `data/notes/*.md` | Our build notes: overview, problems and fixes, calibration and results, simulation |
| `data/log.csv` | Our workflow: 30 items in 6 phases, with a column for photos |
| `data/datasheets/TB6612FNG_datasheet.pdf` | Toshiba motor driver datasheet (via SparkFun) |
| `data/datasheets/MPU-6050_product_spec.pdf` | InvenSense MPU-6000/6050 product specification (via SparkFun) |
| `data/datasheets/RPLIDAR_A1M8_datasheet.pdf` | Slamtec RPLIDAR A1 datasheet v1.0 (2016) |
| `data/datasheets/Raspberry_Pi_5_product_brief.pdf` | Raspberry Pi 5 product brief (images reduced for size) |

Datasheets belong to their makers and are included only so the assistant can cite them.

## Known limits

- PDF tables with rotated text or diagrams do not convert cleanly. Those tables are skipped, and the page text is used instead.
- The number check confirms that a number appears in the cited source, not that it is used correctly.
- The RPLIDAR datasheet here is version 1.0 (range 0.15 to 6 m). Newer A1M8 units are sold with a 12 m range. The app answers from the document it has.

## Team

Abdul Rahman Khan, M. Yashwanth, Pranav Pujari. Guide: Prof. Vijaya Dalawai, Assistant Professor, Dept of AIML, Global Academy of Technology, Bengaluru.
