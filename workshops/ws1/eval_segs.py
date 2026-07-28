import argparse
import json
from pathlib import Path
from segments import compare_segments, load_segments

SOURCE_DIR = Path("./sample11")
SEGMENTS_TRUE_DIR = Path("./segments_true")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", action="store_true", help="print diffs for all F")
    parser.add_argument("-q", default="programs_3x", help="question key to evaluate (default: programs_3x)")
    args = parser.parse_args()

    rows = []
    for subdir in sorted(SOURCE_DIR.iterdir()):
        if not subdir.is_dir():
            continue

        answers_file = subdir / "video_answers.json"
        if not answers_file.exists():
            continue

        segments_true = load_segments(subdir.name, SEGMENTS_TRUE_DIR)

        with open(answers_file) as f:
            data = json.load(f)
        segments_predict = data["data"].get(args.q, {}).get("answer", None)
        
        result = compare_segments(segments_true, segments_predict)
        result["F"] = subdir.name
        rows.append(result)

    if args.v:
        for r in rows:
            print(f"--- {r['F']} ---")
            print(r.get('diff', ''))
            print()

    print(f"{'File':<20} {'Score':>6} {'Extra':>5}  Summary")
    print("-" * 60)
    for r in rows:
        print(f"{r['F']:<20} {r['score']:>6.2f} {r['extra']:>5d}  {r['summary']}")

    if rows:
        avg = sum(r['score'] for r in rows) / len(rows)
        print(f"\n{'Average':<20} {avg:>6.2f}")


if __name__ == "__main__":
    main()
