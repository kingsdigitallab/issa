## v0.2.0-segment (2026-01-12)

### Feat

- **segment**: Add thumbnail grid view
- **segment**: Add Inter font and set it as the default font family for Pico CSS
- **segment**: Add metadata aggregation command
- **segment**: Add processing metadata to ETL components
- **segment**: Add metadata utilities and tests
- **segment**: Add backend option for processing methods
- **segment**: Add support for API inference
- **segment**: Add support for API inference
- **segment**: Add support for API inference
- **segment**: Add example environment configuration for API settings

### Refactor

- **segment**: Move the frames thumbnails to the same section as the video
- **segment**: Change evaluation page layout and styles
- **segment**: Conditionally display video and data sections
- **segment**: Render dates with locale
- **segment**: Refine summary prompt and add content priority
- **segment**: Remove redundant classes
- **segment**: Improve metadata layout and step display
- **segment**: Enable trust_remote_code when loading processor

## v0.1.0-segment (2025-11-27)

### Feat

- **segment**: Add shell scripts to run parts/all of the pipeline
- **segment**: Improvement to evaluation dashboard
- **segment**: Add option to set the chunking size for summarisation
- **segment**: Add chunking to summarise segments
- **segment**: Implement 3-frame context boundary detection
- **segment**: Implement 3-frame context boundary detection
- **segment**: Add video segmentation evaluation prototype
- **segment**: Add CLI commands to merge, summarise and classify segments
- **segment**: Add merge, summarise and classify segment functions
- **segment**: Add prompts for boundary detection, classification and summarisation tasks
- **segment**: Add independent boundary detection functionality
- **segment**: Update boundary detection prompt
- **segment**: Implement boundary detection in segment generation
- **segment**: Add boundary detection prompt
- **segment**: Add text generation function
- **segment**: Add function to load Hugging Face causal language model
- **segment**: Add alignment step for captions and audio to README
- **segment**: Add align command for caption and transcription alignment
- **segment**: Add segment generation with prompt-only option
- **segment**: Add alignment module for captions and transcriptions
- **seggment**: Implement semantic video segmentation pipeline with frame extraction, audio transcription, and captioning
- **qwen3-vl**: Added support for MoE variants
- **geosearch**: Added a bash script to zip the prototype to let others try it
- improved the video interactions; added a list of units for each clip
- First version of prototype 2: geocode place names mentioned in clips and show them on a map
- added script to test qwen 3 on video input

### Fix

- **segment**: Ensure frames are kept in timestamp order
- **qwen3-vl**: Fixed the python requirements
- **geosearch**: Better initial view of NI on the map; updated the nominatim cache
- **tech-review**: removed reference to internal Slack thread
- **tech-review**: fixed some formatting issues

### Refactor

- **segment**: Refine merging of duplicate transcriptions
- **segment**: Adapt boundary detection prompt to 3-frame context
- **segment**: Increase max_new_tokens to 128000
- **segment**: Replace segment function with detect_boundaries
- **segment**: Replace direct model generation logic with the utility function
- **segment**: Update prompt handling in generate_segments function
- **segment**: Rename prompt_path to prompt_folder
- **segment**: Remove unused constant
