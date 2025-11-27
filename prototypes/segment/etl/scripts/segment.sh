VIDEO=$1

uv run python main.py detect-boundaries "$VIDEO"
uv run python main.py merge-segments "$VIDEO"
uv run python main.py summarise-segments "$VIDEO"
uv run python main.py classify-segments "$VIDEO"