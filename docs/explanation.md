# Lecture Notes Pipeline - MVP Version 1 Explanation

This document explains what we built for **MVP Version 1**, why we made these choices, and how all the pieces fit together.

---

## What is This Pipeline?

This is a tool that takes a **lecture video** as input and produces **structured study notes** as output. The entire process happens on your own computer - no data is sent to the internet. Think of it like having a smart assistant that watches your lecture, writes down everything, and then organizes it into neat notes.

---

## Why We Built It This Way

### The Core Problem

Students often:
- Don't have time to take good notes during lectures
- Miss important points while trying to write things down
- Need to re-watch lectures multiple times to capture everything

### Our Solution Philosophy

1. **Privacy First**: Your lecture recordings might contain sensitive academic content. We made sure nothing leaves your computer.

2. **Works Without a GPU**: Not everyone has an expensive graphics card. The pipeline is optimized to run on regular CPUs.

3. **Simple to Use**: One command to process a video. No complicated setup required.

4. **Quality Over Speed**: We chose models that produce good results, even if they take longer.

---

## The Four Steps of the Pipeline

The pipeline works in 4 simple steps:

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   VIDEO      │───▶│    AUDIO     │───▶│  TRANSCRIPT  │───▶│    NOTES     │
│   (Input)    │    │  (Extracted) │    │   (Text)     │    │   (Output)   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
     Step 1              Step 2              Step 3              Step 4
```

### Step 1: Video Validation

**What happens**: The system checks if your video file is valid and has audio.

**Why this step exists**: We need to catch problems early. If the video has no audio track, there's nothing to transcribe!

**Component**: `main.py` (entry point)

---

### Step 2: Audio Extraction

**What happens**: We extract just the audio from your video file and save it as a WAV file.

**Why we do this**: 
- Video files are large and contain visual data we don't need
- The speech-to-text model only needs audio
- WAV format at 16kHz mono is exactly what Whisper expects

**Why WAV format?**: It's uncompressed and gives the best accuracy. The extra disk space is worth it.

**Why 16kHz?**: This is the sample rate Whisper was trained on. Using this rate gives the most accurate results.

**Component**: `src/audio_extractor.py`

**Tool Used**: FFmpeg (a widely-used, reliable tool for handling audio/video)

---

### Step 3: Transcription (Speech to Text)

**What happens**: We use the Whisper AI model to convert spoken words into written text with timestamps.

**Why Whisper?**: 
- Created by OpenAI, trained on 680,000 hours of audio
- Handles different accents, background noise, and multiple languages
- Provides word-level timestamps (tells you exactly when each word was spoken)

**Why faster-whisper (not regular Whisper)?**:
- Same accuracy as regular Whisper
- Uses CTranslate2 which is optimized for CPUs
- 4x faster and uses less memory
- Supports int8 quantization (makes it even faster on CPU)

**Why "medium" model by default?**:
- Good balance between speed and accuracy
- Works well on systems with 8GB RAM
- Smaller models miss words; larger models are too slow on CPU

**The Caching System**:
- We save transcripts so you don't wait again if you run the same video twice
- Cache is based on the video file's hash (fingerprint)
- Even if you rename the file, we recognize it's the same content

**Component**: `src/transcriber.py`

---

### Step 4: Note Generation

**What happens**: We send the transcript to a local AI model (LLM) which reads it and writes organized study notes.

**Why Ollama?**:
- Runs AI models locally on your computer
- Easy to install and manage models
- Supports many different models
- Free and open source

**Why llama3.2:3b by default?**:
- Small enough to run on 8GB RAM
- Fast enough to generate notes in a few minutes
- Smart enough to understand lecture content and create useful notes
- Good at following our note-taking prompt structure

**The Smart Chunking System**:
- Long lectures (over ~30 minutes) produce too much text for the AI to process at once
- We split the transcript into chunks, summarize each chunk, then combine them
- This keeps the quality high even for 2-hour lectures

**What the AI produces**:
- A descriptive title
- 2-3 sentence summary
- Key concepts with definitions
- Detailed notes organized by topic (with timestamps!)
- Study questions to test yourself

**Component**: `src/note_generator.py`

---

## How Things Connect Together

Here's how all the pieces work as a team:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              main.py                                     │
│                         (The Conductor)                                  │
│  - Reads config.yaml                                                    │
│  - Parses command line arguments                                        │
│  - Orchestrates the whole pipeline                                      │
│  - Handles errors gracefully                                            │
│  - Manages memory (unloads Whisper before loading LLM)                  │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        audio_extractor.py                                │
│                         (The Converter)                                  │
│  - Validates video files                                                │
│  - Uses FFmpeg to extract audio                                         │
│  - Converts to Whisper-friendly format (16kHz, mono, WAV)               │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         transcriber.py                                   │
│                         (The Listener)                                   │
│  - Loads the Whisper model                                              │
│  - Converts speech to text                                              │
│  - Creates timestamps for each sentence                                 │
│  - Uses VAD filter to skip silence                                      │
│  - Caches results for reuse                                             │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        note_generator.py                                 │
│                         (The Writer)                                     │
│  - Connects to Ollama                                                   │
│  - Formats transcript with timestamps                                   │
│  - Chunks long transcripts                                              │
│  - Asks AI to create structured notes                                   │
│  - Streams output so you see progress                                   │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT                                         │
│                    video_name_notes.md                                   │
│  - Title and summary                                                    │
│  - Key concepts                                                         │
│  - Detailed notes with timestamps                                       │
│  - Study questions                                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration Files

### config.yaml

This file stores your preferences. Instead of typing long commands every time, you set your defaults here:

| Setting | What it controls |
|---------|------------------|
| `whisper.model` | Which speech-to-text model to use |
| `whisper.language` | Force a specific language (or auto-detect) |
| `llm.model` | Which AI writes the notes |
| `llm.temperature` | How "creative" the AI should be (lower = more focused) |
| `processing.chunk_size` | How to split long lectures |
| `processing.cache_enabled` | Whether to save transcripts for reuse |

---

## Why These Specific Choices?

### Why Local/Offline?

| Cloud-based | Local (our choice) |
|-------------|-------------------|
| Requires internet | Works offline |
| Privacy concerns | Your data stays on your device |
| May cost money per use | Free after setup |
| Rate limits | No limits |
| Dependent on service availability | Always available |

### Why These Default Models?

| Model | Why we chose it |
|-------|----------------|
| **Whisper medium** | Best speed/accuracy ratio for 8GB RAM systems |
| **llama3.2:3b** | Small, fast, but still writes good notes |
| **int8 computation** | Uses less memory, almost same accuracy |

### Why Caching?

- Transcription is slow (can take 30+ minutes for a 1-hour lecture)
- If you want to try different note generation settings, you shouldn't wait for transcription again
- Cache is based on file content hash, not filename

### Why Streaming Output?

- Note generation can take 5-10 minutes
- Watching the notes appear in real-time shows progress
- You know the system isn't stuck

---

## Known Limitations of MVP V1

Things we know aren't perfect yet:

1. **No GPU support**: Works on CPU only (GPU support could be added later)
2. **English-focused prompts**: Note generation prompts are in English
3. **No editing**: Can't edit the transcript before generating notes
4. **Single file only**: Process one video at a time
5. **Markdown only**: Output is only in Markdown format

---

## Summary

MVP Version 1 is designed to be:

| Goal | How we achieved it |
|------|-------------------|
| **Private** | All processing is local |
| **Accessible** | Works on regular computers without GPU |
| **Simple** | One command to go from video to notes |
| **Reliable** | Uses proven tools (FFmpeg, Whisper, Ollama) |
| **Smart** | Handles long lectures with chunking |
| **Efficient** | Caches transcripts to save time |

The pipeline is built in a modular way - each component does one job well. This makes it easy to upgrade individual parts in future versions without breaking everything else.
