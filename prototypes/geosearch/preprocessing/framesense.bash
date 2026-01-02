python framesense.py make_clips_ffmpeg # laptop
python   framesense.py transcode_clips_ffmpeg # laptop
python   framesense.py make_shots_scenedetect # laptop
python     framesense.py make_frames_ffmpeg # laptop
python       framesense.py answer_frames_ollama # TODO: laptop with ollama/qwen3-vl:2b or 1080ti
python       framesense.py embed_frames_transformers # 4090 (18GB)
python   framesense.py extract_sound_ffmpeg # laptop
python     framesense.py transcribe_speech_parakeet # 4090 with CPU only for some clips
python       framesense.py answer_transcription_ollama # on 1080ti
