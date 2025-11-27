VIDEO=$1

uv run python main.py extract-frames "$VIDEO"
uv run python main.py extract-audio "$VIDEO"
uv run python main.py caption-frames "$VIDEO"
uv run python main.py align "$VIDEO"  --no-merge-duplicate-transcriptions