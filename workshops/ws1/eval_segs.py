import argparse
import json
import re
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
    durations = []
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
        
        durations.append(data["data"].get(args.q, {}).get('stats', {}).get('duration_seconds', 0.0))

    if args.v:
        for r in rows:
            print(f"--- {r['F']} ---")
            print(r.get('diff', ''))
            print()

    print(f"{'File':<15} {'score':>6} {'exp.':>4} {'miss':>4} {'extra':>5} {'beyond':>6}")
    print("-" * 45)
    for r in rows:
        beyond = r['duration_diff_ratio']
        beyond = "" if beyond < 1.5 else f"{r['duration_diff_ratio']:.1f}"
        missing = r['expected'] - r['matched']
        missing = str(missing) if missing else ""
        extra = str(r['extra']) if r['extra'] else ""
        print(f"{r['F']:<15} {r['score']*100:>6.0f} {r['expected']:>4d} {missing:>4} {extra:>5} {beyond:>6}")

    if rows:
        avg = sum(r['score'] for r in rows) / len(rows)
        print(f"\n{'Average':<15} {avg*100:>6.0f}")
        print(f"Duration: {int(sum(durations))} secs   Question: {args.q}")


if __name__ == "__main__":
    main()
