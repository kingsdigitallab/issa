'''
Write true program segments 
from those predicted by framesence.
Serves as draft before manual verification & editing.
'''

import json
from pathlib import Path

SOURCE_DIR = Path("./sample11")
TARGET_DIR = Path("./segments_true")
QUESTION = "programs_3x"


def main() -> None:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    for subdir in sorted(SOURCE_DIR.iterdir()):
        if not subdir.is_dir():
            continue

        answers_file = subdir / "video_answers.json"
        if not answers_file.exists():
            continue

        with open(answers_file) as f:
            data = json.load(f)

        answer = data["data"][QUESTION]["answer"]

        out_path = TARGET_DIR / f"{subdir.name}.json"
        with open(out_path, "w") as f:
            json.dump(answer, f, indent=2)


if __name__ == "__main__":
    main()
