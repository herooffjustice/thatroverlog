# Test sheet: 5 questions

Run on 22 Oct 2026 with Groq `openai/gpt-oss-120b`. Each answer came back in about 1 second.

| # | Question | Expected answer | Expected source | Correct? | Notes |
|---|---|---|---|---|---|
| 1 | Why does the LiDAR disconnect during turns? | Electrical noise (EMI) from the motors drops the LiDAR USB during on-spot turns. Fixed with the LiDAR guard, capacitors on the motors, driver and converter, and our custom-made LiDAR cable. | Our notes: Problems and fixes / Our workflow, 17 | Yes | Cited workflow item 17 and the problems notes. No numbers, so no number check. |
| 2 | What is the peak output current of the TB6612FNG? | 3.2 A for a single 10 ms pulse. Continuous: 1.2 A per channel. | TB6612FNG datasheet, page 3 (table) | Yes | Gave 2 A (20 ms pulses, duty ≤ 20%) and 3.2 A (one 10 ms pulse), page 3. Number check passed. Did not mention the 1.2 A continuous rating. |
| 3 | What is the measuring range of the RPLiDAR A1M8? | 0.15 to 6 m for white objects (this is the v1.0 datasheet). | RPLiDAR A1M8 datasheet, page 7 | Yes | 0.15 to 6 m, page 7. Number check passed. |
| 4 | How much power does an on-spot turn need? | About 32 to 35% to start. 35% gives about 0.4 rad/s. | Our notes: Calibration and results | Yes | 32 to 35% to start. Number check passed. |
| 5 | How long does the battery last on one charge? | "I don't know." We never measured battery life. | None (should refuse) | Yes | Refused before calling the model (best match 0.20, below the 0.25 limit). |

## Failure cases we noticed

- Questions with no shared words and a different meaning (for example "How fast does the rover drive in a straight line?") can rank a related section (Nav2 top speed) above the one with the measured speed.
- Tables made of rotated text (some MPU6050 and RPLIDAR pages) are skipped, so those values only come from the page text.
- The number check highlights "10" inside "100" on the page image, because PDF search matches parts of numbers.
- Asked for the MPU6050 I2C address, the model gave b1101000 (correct, from the datasheet) and added 0x68, its own conversion. The datasheet never writes 0x68, so the number check shows a red warning. The value is right, but the warning is doing its job: it flags any number that did not come from a source.
- Groq retires models over time. The app now picks a working model by itself if the chosen one is gone.

# WasteVision tests (23 Oct 2026)

**Detector, 18 photos from another public garbage dataset (not its training data):** 7 correct.
- Correct: 4 of 4 metal cans and tins, newspaper, flyer, foam cup (plastic).
- Wrong: foil (called cardboard), shredded and black paper, a folded newspaper, and 6 of 6 plastic items (bottles, bags, caps, milk jug).
- A photo collage of 4 items was seen as one large "paper" item: it works best with real, separated items.

**"Why?" answers (Groq `openai/gpt-oss-120b`), all 8 classes:** every answer cited the rules. Two needed fixes:
- Medical: the first question mixed sanitary waste and medicines, and the model said "not covered". Asking about expired medicines and domestic hazardous waste fixed it.
- E-waste: the first answer added advice about batteries that the rules we have do not contain. Asking "who should e-waste be handed over to?" gives the grounded answer: a registered producer, refurbisher or recycler (E-Waste Rules 2022, page 24).
- A rover question ("What is the rover's top speed?") on the waste page was refused before calling the model, so the two knowledge bases stay separate.

**Detector on real litter photos (TACO, 104 crops, labels from TACO's own annotations):** material right for 36 of 104 (35%), right bin for 89 of 104 (86%), nothing found in 2. Most mistakes stay inside dry waste (for example a plastic bottle called cardboard). Worst: plastic, only 3 of 28 named right.

**Animation (`Watch the rover sort litter`):** ran for 140 seconds in Chrome on desktop and on a phone-sized screen with no errors. It found, picked up and binned 8 items; it asked for help once and the answer was used; dropping litter by clicking worked; a page rerun (uploading a photo) did not reset it; with "reduce motion" turned on it waits for Play.
