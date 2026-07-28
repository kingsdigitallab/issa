# Notebook

```bash
python -m venv venv
. venv/bin/activate
pip install -r requirements.txt
python -m jupyter lab
```

# Video pre-processing on HPC

If not already there, place the sample videos under sample11/X.32/X.32.mp4. Where X is the first column in sample-11.csv. `copy-video.bash` will help you with copying the video over.

```bash
# start sglang: 

. /scratch/prj/dh_issa/sglang/.venv/bin/activate

python -m sglang.launch_server --model-path Qwen/Qwen3.6-27B --port 30000 --tp-size 1 --mem-fraction-static 0.7 --context-length 49152 --enable-deterministic-inference --reasoning-parser qwen3  --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device

# Or
# python -m sglang.launch_server --model-path Qwen/Qwen3.5-27B-GPTQ-Int4 --port 30000 --tp-size 1 --mem-fraction-static 0.7 --context-length 49152 --enable-deterministic-inference --reasoning-parser qwen3  --mm-attention-backend fa3 --attention-backend fa3 --keep-mm-feature-on-device

# run framsense operator on NLS sample

cd /scratch/prj/dh_issa/framesense
FRAMESENSE_DEBUG=1 FRAMESENSE_COLLECTIONS=/scratch/prj/dh_issa/issa/workshops/ws1/collections.json python framesense.py answer_videos_vlm

```

