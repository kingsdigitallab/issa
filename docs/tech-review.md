# Tech Review

*A list of tools or methods relevant to ISSA's DEERINs. For each entry,
please supply a title, a **link** to their online home (e.g. github or
arxiv), a **publication (or last update) date,** and a **entry category
(e.g. benchmark, algorithm, model, ...)**. Optionally, for tools, list
key/distinctive **features**; and for articles, one sentence
highlighting the relevance to ISSA. Indicate if tool is not fully **open
source**.*



Guiding questions:

- GN: identifying performance gaps in current models in
  extracting/"understanding" information from moving images relevant to
  screen archives or their users
- GN: any standard, schema, taxonomy, tool or method that DEERINs could
  be built on top of (rather than reproducing)
- GN: trends spotting, what is the AI landscape likely to offer in 2, 5
  or 10 years for screen archives

# 0. Existing tech used by some archives

- [Cambria File Transcoder](https://www.capellasystems.net/cambria-ftc)
  (FTC) (proprietary) service used by NLW. (Upcoming, as of May 25)
  features according to their website, include:
    - Detect and remove black frames and color bars
    - Detect score changes to help with making highlight clips
    - Gauge source file complexity to optimize encoding settings
    - Locate ad insertion points
    - Identify registered images
    - Perform Speech to Text conversion
- [Reuters Imagen](https://imagen.io/about) Used by YFA (and others,
  e.g. Imperial War Museum Moving Image Archive, and the BFI until a few
  years ago, before they went in-house). "At Imagen, we
  are going beyond traditional models of AI-generated metadata such as
  transcription and facial recognition to truly surface the meaning
  behind video." By the sounds of it, they basically mean some kind of
  semantic search under the hood.
    - partners with [WSC Sports](https://wsc-sports.com/platform/)
    (proprietary): offers proprietary AI-driven platform to produce
    personalised sport content
    - partners with [SpeechMatics](https://www.speechmatics.com/)
    (proprietary): "Enterprise-grade APIs for Speech-to-Text and Voice AI
    Agents". Real-time transcription and translation.

# 1. Enrichment/ETL

## Shot segmentation / shot boundary detection (SBD)

[papers with
code](https://paperswithcode.com/task/camera-shot-boundary-detection) -
[leaderboard](https://paperswithcode.com/sota/camera-shot-boundary-detection-on-clipshots)

### [AutoShot](https://github.com/wentaozhu/AutoShot) (2023)

### [MSU Shot Boundary Detection Benchmark](https://videoprocessing.ai/benchmarks/shot-boundary-detection.html) (2020-2021)

GN: test for cuts, dissolves and fades

### [TransNetV2](https://github.com/soCzech/TransNetV2) (2020)

### [Comparison](https://github.com/albanie/shot-detection-benchmarks?tab=readme-ov-file) (2016) b/w [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) (2014-2024), [ffprobe](https://stackoverflow.com/q/28269871)/[ffmpeg](https://superuser.com/a/1256814) and [ShotDetect](https://github.com/johmathe/Shotdetect) (2012-2023)

## Scene Segmentation

### [SceneRAG: Scene-level Retrieval-Augmented Generation for Video Understanding](https://arxiv.org/abs/2506.07600) (Workflow, June 2025, Shenzhen University)

> Current RAG approaches typically segment videos into fixed-length
> chunks, which often disrupts the continuity of contextual information
> and fails to capture authentic scene boundaries. Inspired by the human
> ability to naturally organize continuous experiences into coherent
> scenes, we present SceneRAG, a unified framework that leverages large
> language models to segment videos into narrative-consistent scenes by
> processing ASR transcripts alongside temporal metadata. SceneRAG
> further sharpens these initial boundaries through lightweight
> heuristics and iterative correction. For each scene, the framework
> fuses information from both visual and textual modalities to extract
> entity relations and dynamically builds a knowledge graph, enabling
> robust multi-hop retrieval and generation that account for long-range
> dependencies.

## Visual embeddings

### [VLM2Vec-V2: Advancing Multimodal Embedding for Videos, Images, and Visual Documents](https://tiger-ai-lab.github.io/VLM2Vec/) (Benchmark and Model, July 2025, Waterloo, Santa Barbara, Tsinghua unis, Salresforce)

> We propose VLM2Vec framework to learn a single multimodal embedding
> model that can encode a series of images and text for any downstream
> task. Unlike traditional CLIP or BLIP embeddings, VLM2Vec can handle
> images **with any resolution and text with any length**. It can also
> **follow instruction to produce instruction-guided representation**,
> which fits the downstream tasks better than other task-agnostic
> multimodal emebddings.

## Visual Question Answering (VQA)

[Papers with code /
vqa](https://paperswithcode.com/task/visual-question-answering/latest)

## Cinematic feature classification

### [ShotBench: Expert-Level Cinematic Understanding in Vision-Language Models](https://vchitect.github.io/ShotBench-project/) (Dataset (ShotQA), Benchmark (SoftBench), and model (ShotVL), June 2025)

  

GN: New benchmark (ShotBench) and model (ShotVL) for detection of Shot
size, Shot framing, Camera angle, Lens size, Lighting type, Lighting
condition, Composition and Camera movement. They also tested a lot of
third-party VLMs on each feature. Relevant to us: the **shot taxonomy
and trend towards all-in-one specialised classifier**. Also shows the
current "understanding" gaps in general purpose VLMs for cinematographic
features (mainly Lightning conditions, Shot composition and Camera
movement). Their 3B model (ShotVL) matches performances of much larger
ones (e.g. Qwen 32/72B) on their own benchmark. Another way to interpret
the benchmark result is that, if you set the acceptance bar at ~80%
accuracy, the best VLMs are currently only usable for Shot size/scale
and Shot framing classification.

## Video Understanding

[Papers with code / video
understanding](https://paperswithcode.com/task/video-understanding/latest)

### [Flash-VStream: Efficient Real-Time Understanding for Long Video Streams](https://zhang9302002.github.io/vstream-iccv-page/) (Video LM with new architecture, June 2025, Tsinghua & Beijing Jiatong unis, ByteDance Seed)

> Most existing work treats long videos in the same way as short videos,
> which is inefficient for real-world applications and hard to
> generalize to even longer videos. To address these issues, we propose
> Flash-VStream, an efficient video language model capable of processing
> extremely long videos and responding to user queries in real time.
> Particularly, we design a Flash Memory module, containing a
> low-capacity context memory to aggregate long-context temporal
> information and model the distribution of information density, and a
> high-capacity augmentation memory to retrieve detailed spatial
> information based on this distribution. Compared to existing models,
> Flash-VStream achieves significant reductions in inference latency.

GN: I think this is a 7B model which works at 1fps, with output quality
similar to Qwen2-VL (but not sure with size? 7B as well?) although with
faster processing speed, lower resource consumption and real-time
capabilities. Q: what is practically meant by realtime here and which
compute set up is needed to achieve that level of responsiveness?

There is a [7B model on
HuggingFace](https://huggingface.co/IVGSZ/Flash-VStream-7b) but it was
uploaded in June 2024. I believe there's a new model based on Qwen
coming up soon.

### [Video-STaR: Self-Training Enables Video Instruction Tuning with Any Supervision](https://orrzohar.github.io/projects/video-star/) (Training method, July 24, Google)

  

> Video-STaR is a self-training for video language models, allowing the
> use of any labeled video dataset for video instruction tuning. It
> cycles between generating and filtering answers to ensure only those
> containing the correct video labels are used for training, effectively
> leveraging existing video labels as weak supervision. This iterative
> process enhances both general video understanding and the adaptability
> of LVLMs to novel tasks, resulting in significant performance
> improvements in video question-answering and various downstream
> applications.

I think this is very interesting, connects to our conversations about
using existing metadata, e.g. clip descriptions and film data in our
MovieClips dataset, to enrich generated metadata. The promise of
adaptability to different source material is relevant to ISSA.

Code here:
[https://github.com/orrzohar/Video-STaR](https://github.com/orrzohar/Video-STaR)

  

### [VideoAgent: Long-form Video Understanding with Large Language Model as Agent](https://wxh1996.github.io/VideoAgent-Website/) (Agent-based system, 2024)

  

> Long-form video understanding represents a significant challenge
> within computer vision, demanding a model capable of reasoning over
> long multi-modal sequences. Motivated by the human cognitive process
> for long-form video understanding, we emphasize interactive reasoning
> and planning over the ability to process lengthy visual inputs. We
> introduce a novel agent-based system, VideoAgent, that employs a large
> language model as a central agent to iteratively identify and compile
> crucial information to answer a question, with vision-language
> foundation models serving as tools to translate and retrieve visual
> information. Evaluated on the challenging EgoSchema and NExT-QA
> benchmarks, VideoAgent achieves 54.1% and 71.3% zero-shot accuracy
> with only 8.4 and 8.2 frames used on average. These results
> demonstrate superior effectiveness and efficiency of our method over
> the current state-of-the-art methods, highlighting the potential of
> agent-based approaches in advancing long-form video understanding.

This also connects with previous conversations about hierarchical agents
and agent-like behaviours used to grab additional frames or info based
on interactive querying. Code here:
[https://github.com/wxh1996/VideoAgent](https://github.com/wxh1996/VideoAgent)

  

### [Shot2Story](https://mingfei.info/shot2story/) (Benchmark, 2023-)

> A short clip of video may contain progression of multiple events and
> an interesting story line. A human need to capture both the event in
> every shot and associate them together to understand the story behind
> it.  
> In this work, we present a new multi-shot video understanding
> benchmark \dataset with detailed shot-level captions, comprehensive
> video summaries and question-answering pairs. To facilitate better
> semantic understanding of videos, we provide captions for both visual
> signals and human narrations. We design several distinct tasks
> including single-shot video captioning, multi-shot video
> summarization, and multi-shot video question answering.

Shot-level captions and multi-shot summaries caught my eye. I invited
the author of the paper to our technical exchange meeting on the 30th.
Demo is broken at the moment, but the code is available here:
[https://github.com/bytedance/Shot2Story/tree/master/code](https://github.com/bytedance/Shot2Story/tree/master/code)

  

### [Eagle 2.5](https://nvlabs.github.io/EAGLE/) (VLM, April 2025)

> Despite significant advances in multimodal learning, many
> vision-language models (VLMs) remain focused on short-context tasks,
> with long-context understanding under-explored. This gap is
> particularly evident in both long video comprehension and
> high-resolution image/video understanding, where the processing of
> extended visual contexts remains an open challenge.  
> The development of long-context VLMs is still in its early stages,
> hindered by fundamental challenges in dataset construction,
> architecture design, training strategies, and computation/memory
> bottlenecks. While prior studies have explored extending context
> length, key limitations remain: suboptimal performance compared to
> proprietary models, inconsistent improvements as visual input
> increases, and unclear optimal training strategies.

Code here:
[https://github.com/NVlabs/EAGLE](https://github.com/NVlabs/EAGLE)

### [Twelve Labs](https://www.twelvelabs.io/) (video understanding platform, 2025)

> Find anything, discover deep insights, analyze, remix and automate
> workflows with AI that can see, hear, and reason across your entire
> video content.

Web platforms available here:
[https://playground.twelvelabs.io/](https://playground.twelvelabs.io/)

Two custom proprietary models: Pegasus and Marengo. See models overview
here:
[https://www.twelvelabs.io/product/models-overview](https://www.twelvelabs.io/product/models-overview)

## Audio description

- [DANTE-AD: Dual-Vision Attention Network for Long-Term Audio
  Description](https://andrewjohngilbert.github.io/DANTE-AD/) (2025)

> Audio Description is a narrated commentary designed to aid
> vision-impaired audiences in perceiving key visual elements in a
> video. While short-form video understanding has advanced rapidly, a
> solution for maintaining coherent long-term visual storytelling
> remains unresolved. Existing methods rely solely on frame-level
> embeddings, effectively describing object-based content but lacking
> contextual information across scenes. We introduce DANTE-AD, an
> enhanced video description model leveraging a dual-vision
> Transformer-based architecture to address this gap. DANTE-AD
> sequentially fuses both frame and scene level embeddings to improve
> long-term contextual understanding. We propose a novel,
> state-of-the-art method for sequential cross-attention to achieve
> contextual grounding for fine-grained audio description generation.
> Evaluated on a broad range of key scenes from well-known movie clips,
> DANTE-AD outperforms existing methods across traditional NLP metrics
> and LLM-based evaluations.

  

- [AutoAD III: The Prequel -- Back to the
  Pixels](https://www.robots.ox.ac.uk/~vgg/research/autoad/) (2024)

> Generating Audio Description (AD) for movies is a challenging task
> that requires fine-grained visual understanding and an awareness of
> the characters and their names. Currently, visual language models for
> AD generation are limited by a lack of suitable training data, and
> also their evaluation is hampered by using performance measures not
> specialized to the AD domain. In this paper, we make three
> contributions: (i) We propose two approaches for constructing AD
> datasets with aligned video data, and build training and evaluation
> datasets using these. These datasets will be publicly released; (ii)
> We develop a Q-former-based architecture which ingests raw video and
> generates AD, using frozen pre-trained visual encoders and large
> language models; and (iii) We provide new evaluation metrics to
> benchmark AD quality that are well-matched to human performance. Taken
> together, we improve the state of the art on AD generation.

## Subtitling

- [Look, Listen and Recognise: character-aware audio-visual
  subtitling](https://www.robots.ox.ac.uk/~vgg/research/look-listen-recognise/)
  (2023)

> The goal of this paper is automatic character-aware subtitle
> generation. Given a video and a minimal amount of metadata, we propose
> an audio-visual method that generates a full transcript of the
> dialogue, with precise speech timestamps, and the character speaking
> identified. The key idea is to first use audio-visual cues to select a
> set of high-precision audio exemplars for each character, and then use
> these exemplars to classify all speech segments by speaker identity.
> Notably, the method does not require face detection or tracking. We
> evaluate the method over a variety of TV sitcoms, including Seinfeld,
> Fraiser and Scrubs. We envision this system being useful for the
> automatic generation of subtitles to improve the accessibility of the
> vast amount of videos available on modern streaming services.

## Speaker detection

- [GestSync: Determining who is speaking without a talking head (also
  works for Audio and video
  Synchronisation)](https://www.robots.ox.ac.uk/~vgg/research/gestsync/)

> Gesture-Sync: determining if a person's gestures are correlated with
> their speech or not. In comparison to Lip-Sync, Gesture-Sync is far
> more challenging as there is a far looser relationship between the
> voice and body movement than there is between voice and lip motion. We
> introduce a dual-encoder model for this task, and compare a number of
> input representations including RGB frames, keypoint images, and
> keypoint vectors, assessing their performance and advantages. We show
> that the model can be trained using self-supervised learning alone,
> and evaluate its performance on the LRS3 dataset. Finally, we
> demonstrate applications of Gesture-Sync for audio-visual
> synchronisation, and in determining who is the speaker in a crowd,
> without seeing their faces.

Demo here:
[https://huggingface.co/spaces/sindhuhegde/gestsync](https://huggingface.co/spaces/sindhuhegde/gestsync)

# 2. Exploration

### Language Models

*Specify input and output modalities (e.g. image, video, sound, text),
and model size.*

  

[Towards Fine-Grained Video Question
Answering](https://arxiv.org/pdf/2503.06820): integrated architecture
for video understanding (25Q1)
\[[slack](https://kingsdigitallab.slack.com/archives/C074F6MKZB5/p1741887814221949)\]

  

- [Collection Space
  Navigator](https://collection-space-navigator.github.io/) (2023)

> The Collection Space Navigator (CSN) is an explorative visualization
> tool for researching collections and their multidimensional
> representations. We designed this tool to better understand
> multidimensional data, its methods, and semantic qualities through
> spatial navigation and filtering. CSN can be used with any image
> collection and can be customized for specific research needs (see
> [Jupyter
> Notebook](https://github.com/Collection-Space-Navigator/CSN/blob/main/CSN_notebook.ipynb)
> or [Google
> Colab](https://github.com/Collection-Space-Navigator/CSN/blob/main/CSN_colab.ipynb)).

# 3. Retrieval

## Semantic Search

  

## RAGs and Integrated systems for Video Collection

  

### [How We Built Multimodal RAG for Audio and Video](https://www.ragie.ai/blog/how-we-built-multimodal-rag-for-audio-and-video) (workflow, July 2025, Ragie.ai)

GN: Break down of a Video RAG workflow.

### [Towards An Improved Video RAG Workflow With Orchestration Support in A Visual Data Management System](https://dl.acm.org/doi/10.1145/3735654.3735945) (workflow, June 2025, Intel & IIT Hyderabad)

> In this paper, we propose a video RAG workflow that utilizes the
> Visual Data Management System (VDMS) interfaced with the Kubernetes
> (K8s) orchestration framework to design an enhanced video RAG workflow
> (VRAG) for faster video context generation in the pre-processing phase
> and a faster response generation with no impact on response accuracy.

  

> **CRAG** \[9\]: We consider the CRAG flows as the ones that run an
> exhaustive pre-processing module to get the data context from the
> videos. The video clips are converted into long-text documents using
> the AI models and stored in a vector database.  
> **iRAG** \[1\]: iRAG is the incremental alternative to CRAG. It runs a
> less complex and faster-running set of AI models in the preprocessing
> phase to get the data context from the videos. If iRAG is not able to
> give a response for a user query, it runs the model that was run by
> CRAG to update the data context and answer the query

### [Reuters Imagen](https://imagen.io/) (closed source): cloud-based media asset management platform

- Used by Yorkshire Film Archive
- TODO: key features

### [VideoRAG](https://github.com/HKUDS/VideoRAG): Retrieval-Augmented Generation with Extreme Long-Context Videos (Workflow, Feb 2025, HK Uni & Baidu)

> VideoRAG introduces a novel dual-channel architecture that
> synergistically combines graph-driven textual knowledge grounding for
> modeling cross-video semantic relationships with hierarchical
> multimodal context encoding to preserve spatiotemporal visual
> patterns, enabling unbounded-length video understanding through
> dynamically constructed knowledge graphs that maintain semantic
> coherence across multi-video contexts while optimizing retrieval
> efficiency via adaptive multimodal fusion mechanisms.

### [Video-RAG: Visually-aligned Retrieval-Augmented Long Video Comprehension](https://video-rag.github.io/) (Workflow, Dec 2024, Xiamen & Rochester unis)

> we propose Video RetrievalAugmented Generation (Video-RAG), a
> training-free and cost-effective pipeline that employs
> visually-aligned auxiliary texts to help facilitate cross-modality
> alignment while providing additional information beyond the visual
> content. Specifically, we leverage open-source external tools to
> extract visually-aligned information from pure video data (e.g.,
> audio, optical character, and object detection), and incorporate the
> extracted information into an existing LVLM as auxiliary texts,
> alongside video frames and queries, in a plug-and-play manner. Our
> Video-RAG offers several key advantages: (i) lightweight with low
> computing overhead due to single-turn retrieval; (ii) easy
> implementation and compatibility with any LVLM; and (iii) significant,
> consistent performance gains across long video understanding
> benchmarks, including Video-MME, MLVU, and LongVideoBench

### Proof of concept, Moving image archive (by Stormid?):

- video broken down into scene
- summary generated from subtitles
- OpenAI VIsion used to describe frame content, to compensate for lack
  of speech/narration
- chapterisation of content, generate titles
- word cloud of recurring theme
- occurrences placed on an interactive timeline (people, place, theme,
  brand) to jump to clip, also show related keywords

### [Neuravid](https://www.neuravid.io/): closed source, \[[slack\]](https://kingsdigitallab.slack.com/archives/C074F6MKZB5/p1741718687099909)

- chat to a video (e.g. list people)
- search for moments (it returns timestamps and short sentence
  summarising the action)
- transcription and conversion to scripts or articles (summary according
  to particular format/purpose, e.g. a report)
- speaker detection
- search for actions across a collection of videos
- multilingual support (40 languages)
- search moments by describing a sound
- semantic segmentation by chapters
- highlight detection
- generate video clips automatically from long videos

  

# 4. Interaction & Generative

## Interfaces

  

- [WISE 2](https://gitlab.com/vgg/wise/wise/-/tree/wise2) (2025)

> WISE is a search engine for images, videos, and audio powered by
> multimodal AI, allowing you to quickly and easily search through large
> collections of audiovisual media. You can search using natural
> language, an uploaded image/audio file, or a combination of these
> modalities. Use WISE locally on your own collections of images/videos.

## Visualisation

  

# 5. Standards

## [TempCompass: Do Video LLMs Really Understand Videos?](https://llyx97.github.io/tempcompass/) (2024)

> Recently, there is a surge in interest surrounding video large
> language models (Video LLMs). However, existing benchmarks fail to
> provide a comprehensive feedback on the temporal perception ability of
> Video LLMs. On the one hand, most of them are unable to distinguish
> between different temporal aspects (e.g., speed, direction) and thus
> cannot reflect the nuanced performance on these specific aspects. On
> the other hand, they are limited in the diversity of task formats
> (e.g., only multi-choice QA), which hinders the understanding of how
> temporal perception performance may vary across different types of
> tasks.

Video understanding community is picking up on the limitations of
temporal reasoning. To what extent these models actually understand time
or the perception of time? This benchmark is now part of
[VLMEvalKit](https://github.com/open-compass/VLMEvalKit), "an
open-source evaluation toolkit of large vision-language models (LVLMs).
It enables one-command evaluation of LVLMs on various benchmarks,
without the heavy workload of data preparation under multiple
repositories".


# 6. Research Groups and projects

- [Oxford Visual Geometry Group
  (VGG)](https://www.robots.ox.ac.uk/~vgg/)
- [Centre for Creative Arts and Technologies](https://c-cats.ac/)
- [2nd Data Challenge of the Data Competence Centre
  HERMES](https://hermes-hub.de/forschen/datachallenges/challenges/challenge-2025.html):
  to develop an "advanced discovery system that enables multimodal
  search across the dataset" (40 hours of .mp4 video (20 hours from the
  German Archives and 20 hours from the Netherlands Institute for Sound
  and Vision). Results: Dec 25
