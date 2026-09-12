cd framesense

FRAMESENSE_DEBUG=1 \
FRAMESENSE_COLLECTIONS="/scratch/prj/dh_issa/issa/workshops/ws1/collections-batches.json" \
./venv/bin/python framesense.py answer_separators_vlm -f "sample100" 
