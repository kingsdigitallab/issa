cd /scratch/users/k1217897/prj/framesense/ 

ANSWER_VIDEOS_VLM_MAX_TOKENS="30k" \
ANSWER_VIDEOS_VLM_VIDEO_TOKENS="64k" \
ANSWER_VIDEOS_VLM_SEED="43" \
ANSWER_VIDEOS_VLM_REASONING_EFFORT="xhigh" \
ANSWER_VIDEOS_VLM_MODEL=RedHatAI/Qwen3.8-27B-INT4 \
ANSWER_VIDEOS_VLM_API_BASE=http://localhost:30000/v1 \
ANSWER_VIDEOS_VLM_FILTER_QUESTIONS=programs_3xinc-35-27B-v12k-think-s43 \
FRAMESENSE_DEBUG=1 \
FRAMESENSE_COLLECTIONS=/scratch/prj/dh_issa/issa/workshops/ws1/collections.json \
./venv/bin/python framesense.py answer_videos_vlm -r -f 234

