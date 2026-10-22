"""
evaluate.py - checks how well each search method finds the right source.

For every test question we know which source holds the answer. We check whether
that source appears in the top 3 results for: BM25 only, embeddings only, and both
together (hybrid). Run:  python evaluate.py
"""

from rag import RoverIndex

# (question, a piece of text that the correct source's label must contain)
TESTS = [
    ("Why does the LiDAR disconnect during turns?", "LiDAR disconnects during turns"),
    ("What is the peak output current of the TB6612FNG?", "TB6612FNG datasheet, page 3"),
    ("What is the maximum supply voltage VM of the TB6612FNG?", "TB6612FNG datasheet, page 3"),
    ("What is the measuring range of the RPLiDAR A1M8?", "RPLiDAR A1M8 datasheet, page 7"),
    ("What is the I2C address of the MPU6050?", "MPU6050 datasheet, page 36"),
    ("How much power does an on-spot turn need?", "Turning on the spot"),
    ("Why did the odometry run backwards?", "Odometry ran backwards"),
    ("How was the WiFi lag fixed?", "WiFi"),
    ("How many goals did the rover reach in the first test run?", "First full test run"),
    ("Why is the IMU switched off?", "IMU"),
    ("What does the scan gate do?", "Odometry ran backwards"),
    ("What is the wheelbase and track of the rover?", "Measurements"),
    ("Which planner did we use in Isaac Sim?", "Isaac Sim"),
    ("What does the TB6612FNG do when IN1 and IN2 are both high?", "TB6612FNG datasheet, page 4"),
    ("What temperature did the Pi 5 reach while running Nav2?", "Pi 5 load"),
    # Paraphrased questions: different words from the source text.
    ("Why did the robot keep losing its laser scanner while spinning?", "LiDAR"),
    ("Why did the walls appear twice on the map?", "Map drawn twice"),
    ("How fast does the rover drive in a straight line?", "Straight-line speed"),
    ("Can the robot work outside in the sun?", "Limits"),
    ("Which part tells the motors how fast to spin?", "Main parts"),
]


def main():
    idx = RoverIndex()
    print(f"{len(TESTS)} questions, success = correct source in the top 3\n")
    totals = {}
    for mode in ("bm25", "dense", "hybrid"):
        ok = 0
        for q, expected in TESTS:
            hits, _ = idx.search(q, k=3, mode=mode)
            if any(expected.lower() in c.label.lower() for c, _ in hits):
                ok += 1
            elif mode == "hybrid":
                print(f"  hybrid missed: {q}  ->  {[c.label for c, _ in hits]}")
        totals[mode] = ok
    print("\n| Method | Correct source in top 3 |\n|---|---|")
    for mode, ok in totals.items():
        print(f"| {mode} | {ok}/{len(TESTS)} ({100 * ok / len(TESTS):.0f}%) |")


if __name__ == "__main__":
    main()
