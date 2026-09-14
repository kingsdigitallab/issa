cd framesense

FRAMESENSE_DEBUG=1 \
FRAMESENSE_COLLECTIONS="/scratch/prj/dh_issa/issa/workshops/ws1/collections-batches.json" \
ANSWER_SEPARATORS_VLM_API_BASE="http://localhost:30000/v1" \
./venv/bin/python framesense.py answer_separators_vlm -e "239343226.32" 

# ./venv/bin/python framesense.py answer_separators_vlm -f "4.32|5.32|6.32"  -e "239343226.32"
# ./venv/bin/python framesense.py answer_separators_vlm -f "7.32|8.32|9.32" -e "239343226.32"
# ./venv/bin/python framesense.py answer_separators_vlm -f "1.32|2.32|3.32" -e "239343226.32"
# ./venv/bin/python framesense.py answer_separators_vlm -f "298572.32"  -r
# ./venv/bin/python framesense.py answer_separators_vlm -f "4.32|5.32|6.32" 


# FRAMESENSE_DEBUG=1 FRAMESENSE_COLLECTIONS="/scratch/prj/dh_issa/issa/workshops/ws1/collections-batches.json" ./venv/bin/python framesense.py detect_speech_vad
 