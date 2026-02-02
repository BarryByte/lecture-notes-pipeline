# Lecture to Notes Pipeline - Roadmap

## 🎯 Project Vision

Build a fully local, privacy-first, automated pipeline that transforms lecture videos (MP4) into structured, educational notes (Markdown) using state-of-the-art AI models as of 2026.

**Core Principles:**
- 🔒 **100% Offline**: No data leaves your device
- ⚡ **Optimized**: Tuned for CPU-only systems with 16GB RAM
- 🎯 **Accurate**: Best models for your hardware constraints
- 🛠️ **Simple**: Single command execution

---

## 💻 Hardware Profile

| Spec | Value | Impact |
|------|-------|--------|
| **GPU** | None | CPU-only inference required |
| **RAM** | 16GB DDR4 | Limits model size; quantization essential |
| **Storage** | — | ~5-8GB for models |

### CPU-Optimized Strategy

Given the hardware constraints, the pipeline uses:

1. **Whisper**: `faster-whisper` with `int8` quantization (CPU-optimized)
2. **LLM**: Smaller quantized models via Ollama

---

## 📋 Technology Stack (CPU-Optimized)

| Layer | Technology | CPU Configuration |
|-------|------------|-------------------|
| **Audio Extraction** | FFmpeg | Standard (CPU-native) |
| **Speech Recognition** | faster-whisper | `int8` compute, `medium` or `small` model |
| **Intelligence** | Ollama + Llama 3.2 (3B) or Phi-3 Mini | 4-bit quantized (Q4_K_M) |
| **Orchestration** | Python 3.10+ | Single-threaded to control RAM |

### Model Options for 16GB RAM (CPU)

#### Whisper Models (Speech-to-Text)

| Model | Size | RAM Usage | Speed (RTF) | Accuracy |
|-------|------|-----------|-------------|----------|
| `large-v3` | ~3GB | ~6-8GB | 0.8-1.2x | ⭐⭐⭐⭐⭐ |
| `medium` | ~1.5GB | ~3-4GB | 0.4-0.6x | ⭐⭐⭐⭐ |
| `small` | ~500MB | ~1-2GB | 0.2-0.3x | ⭐⭐⭐ |
| `base` | ~150MB | ~500MB | 0.1x | ⭐⭐ |

**Recommendation**: Start with `medium` for best speed/accuracy balance. Use `large-v3` only if quality is critical and you can wait.

> **RTF (Real-Time Factor)**: 0.5x means a 60-min lecture takes ~30 min to transcribe

#### LLM Models (Note Generation)

| Model | Size (Q4) | RAM Usage | Quality | Speed |
|-------|-----------|-----------|---------|-------|
| `llama3.2:3b` | ~2GB | ~4GB | ⭐⭐⭐⭐ | Fast |
| `phi3:mini` | ~2GB | ~4GB | ⭐⭐⭐⭐ | Fast |
| `mistral:7b-q4` | ~4GB | ~6GB | ⭐⭐⭐⭐⭐ | Medium |
| `llama3.1:8b-q4` | ~5GB | ~8GB | ⭐⭐⭐⭐⭐ | Slower |

**Recommendation**: Use `llama3.2:3b` or `phi3:mini` for speed. These handle note generation well despite smaller size.

> ⚠️ **Memory Warning**: Running Whisper `large-v3` + LLM simultaneously may exceed 16GB. Pipeline runs them sequentially to avoid this.

---

## 🗺️ Implementation Roadmap

### Phase 1: Environment Setup ✅

**Goal**: Prepare the development environment with all dependencies

**Tasks:**
- [x] Install Python 3.10+ and create virtual environment
- [x] Install system dependencies:
  - [x] `ffmpeg` (audio extraction)
  - [x] `ollama` (LLM runtime)
- [x] Install Python dependencies:
  - [x] `faster-whisper` + `ctranslate2` (CPU backend)
  - [x] `ollama` (Python client)
  - [x] `ffmpeg-python` or `pydub`
  - [x] `tqdm` (progress bars)
  - [x] `rich` (CLI formatting)
- [x] Pull AI models (CPU-optimized):
  - [x] `ollama pull llama3.2:3b` (recommended) OR `ollama pull phi3:mini`
  - [x] Whisper model auto-downloads on first run (`medium` recommended)
- [x] Verify RAM usage doesn't exceed limits during model loading

**Deliverables:**
- [x] `requirements.txt`
- [x] `setup.sh` (automated setup script)
- [x] `README.md` (installation instructions)
- [x] `.gitignore`
- [x] `config.yaml` (default settings)

---

### Phase 2: Core Pipeline Development ✅

**Goal**: Build the main processing pipeline

#### 2.1 Audio Extraction Module

**File**: `src/audio_extractor.py`

**Features:**
- [x] Extract audio from MP4 using FFmpeg
- [x] Convert to 16kHz mono WAV (Whisper's preferred format)
- [x] Handle various video formats (mp4, mkv, avi, webm)
- [x] Error handling for corrupted files
- [x] Cleanup temp files on failure

**Function Signature:**
```python
def extract_audio(video_path: str, output_dir: str) -> str:
    """Returns path to extracted WAV file"""
```

---

#### 2.2 Transcription Module

**File**: `src/transcriber.py`

**Features:**
- [x] Load faster-whisper model with CPU-optimized settings
- [x] Use `int8` compute type for CPU efficiency
- [x] Support configurable model size (`small`, `medium`, `large-v3`)
- [x] Transcribe with word-level timestamps
- [x] Return structured transcript with metadata
- [x] Cache transcripts to disk (avoid re-processing)

**CPU-Specific Configuration:**
```python
model = WhisperModel(
    "medium",           # Recommended for 16GB RAM
    device="cpu",
    compute_type="int8" # CPU-optimized quantization
)
```

**Function Signature:**
```python
def transcribe(
    audio_path: str, 
    model_size: str = "medium",
    language: str = None,
    cache_dir: str = ".cache"
) -> dict:
    """Returns {text, segments, metadata}"""
```

---

#### 2.3 Note Generation Module

**File**: `src/note_generator.py`

**Features:**
- [x] Connect to local Ollama instance
- [x] Design prompt engineering for educational notes
- [x] **Chunking strategy** for long transcripts (>10k tokens)
- [x] Stream LLM responses with progress indicator
- [x] Structure output in Markdown format
- [x] Graceful handling of context window limits

**Chunking Strategy for Long Lectures:**
```
For transcripts > 10,000 tokens:
1. Split by natural breaks (pauses, topic changes)
2. Process each chunk with overlap
3. Generate section notes for each
4. Final pass: Create unified summary + table of contents
```

**Prompt Template:**
```
You are an expert note-taker. Given a lecture transcript with timestamps,
create comprehensive study notes in Markdown format with:

1. **Title**: Derive from content
2. **Summary**: 2-3 sentence overview
3. **Key Concepts**: Bullet points with definitions
4. **Detailed Notes**: Organized by topic with timestamps [MM:SS]
5. **Action Items**: Study questions or exercises

Keep formatting clean and scannable. Use headers for major topics.

Transcript:
{transcript}
```

**Function Signature:**
```python
def generate_notes(
    transcript: dict, 
    model: str = "llama3.2:3b",
    chunk_size: int = 8000
) -> str:
    """Returns Markdown formatted notes"""
```

---

#### 2.4 Main Orchestrator

**File**: `main.py`

**Features:**
- [x] CLI argument parsing (video path, output dir, language, model options)
- [x] Progress tracking for each stage with ETA
- [x] **Sequential execution** (run one model at a time to manage RAM)
- [x] Temporary file cleanup
- [x] Comprehensive error handling with resume support
- [x] Logging (optional debug mode)

**CLI Interface:**
```bash
# Basic usage
python main.py lecture.mp4

# Full options
python main.py lecture.mp4 \
  --output ./notes \
  --language en \
  --whisper-model medium \
  --llm-model llama3.2:3b \
  --verbose
```

**Execution Flow:**
```
1. Validate input file
2. Check available RAM
3. Extract audio → /tmp/lecture_audio.wav
4. Transcribe → cache/{hash}.json (unload Whisper after)
5. Generate notes → lecture_notes.md (load LLM)
6. Save & cleanup
```

---

### Phase 3: Optimization & Enhancement 🔧

**Goal**: Improve performance and user experience

**Tasks:**
- [ ] **Batch Processing**: Handle multiple videos with queue
- [ ] **Resume Capability**: Detect existing transcripts, skip if cached
- [ ] **RAM Monitoring**: Warn if approaching limits
- [ ] **Progress UI**: Rich terminal UI with ETA
- [ ] **Configuration File**: YAML for default settings
- [ ] **Logging**: Structured logging with rotation

**Nice-to-Have Features:**
- [ ] Speaker diarization (identify different speakers) — *may be too heavy for CPU*
- [ ] Export to PDF/HTML
- [ ] Slide extraction at topic changes (using OCR)
- [ ] Interactive Q&A mode about the lecture

---

### Phase 4: Testing & Validation ✅

**Goal**: Ensure reliability and accuracy

#### Test Cases
- [ ] **Short Video** (<5 min): Verify basic functionality
- [ ] **Long Lecture** (60+ min): Test chunking and memory
- [ ] **Poor Audio**: Noisy/low-quality audio
- [ ] **Multiple Languages**: Test auto-detection
- [ ] **No Speech**: Handle silent videos gracefully
- [ ] **Large Files** (>1GB): Memory usage validation

#### Performance Benchmarks (CPU Targets)

Track on your 16GB RAM system:

| Metric | Target (Medium Whisper + 3B LLM) |
|--------|----------------------------------|
| Transcription RTF | < 0.6x (60 min lecture = ~36 min) |
| Note generation | < 5 min for 60 min lecture |
| Peak RAM | < 10GB (safe headroom) |
| Disk for models | ~5GB total |

---

### Phase 5: Documentation & Distribution 📚

**Goal**: Make it easy for others to use

**Deliverables:**
- [ ] **README.md**: Installation, usage, troubleshooting, hardware requirements
- [ ] **EXAMPLES.md**: Sample outputs with screenshots
- [ ] **ARCHITECTURE.md**: System design documentation
- [ ] **CONTRIBUTING.md**: For future contributors
- [ ] **requirements.txt**: Pinned versions
- [ ] **LICENSE**: MIT (recommended)

**Optional:**
- [ ] Docker container for portability
- [ ] Web UI (Gradio/Streamlit) for non-technical users

---

## 📁 Project Structure

```
lecture-notes-pipeline/
├── docs/
│   ├── roadmap.md         # This file (move here later)
│   ├── architecture.md    # System design
│   └── examples.md        # Sample outputs
├── src/
│   ├── __init__.py
│   ├── audio_extractor.py # FFmpeg wrapper
│   ├── transcriber.py     # faster-whisper integration
│   ├── note_generator.py  # Ollama + LLM logic
│   └── utils.py           # Helpers (file I/O, progress, RAM check)
├── tests/
│   ├── test_extractor.py
│   ├── test_transcriber.py
│   └── test_generator.py
├── .cache/                 # Transcript cache (gitignored)
├── examples/
│   ├── sample_lecture.mp4
│   └── sample_output.md
├── main.py                # CLI entry point
├── config.yaml            # Default settings
├── requirements.txt
├── setup.sh               # Automated setup
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start (After Implementation)

```bash
# 1. Clone and setup
git clone <your-repo>
cd lecture-notes-pipeline
bash setup.sh

# 2. Process a lecture
python main.py path/to/lecture.mp4

# 3. Find your notes
cat lecture_notes.md
```

---

## ⚠️ Known Limitations & Mitigations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| **No GPU** | Slower processing | Use smaller models, accept longer wait times |
| **16GB RAM** | Can't run large models | Sequential execution; quantized models only |
| **Context limits** | Long lectures may lose coherence | Chunk transcripts, merge notes in post-processing |
| **CPU thermals** | Long processing may throttle | Take breaks between long videos; monitor temps |
| **Accents/Dialects** | Whisper may struggle | Use `medium` or `large-v3` for better accuracy |

---

## 📊 Success Metrics (CPU-Adjusted)

- ✅ Process a 60-min lecture in <45 min (CPU, medium model)
- ✅ Notes are coherent, well-structured, and actionable
- ✅ Zero data transmitted over network
- ✅ Peak RAM stays under 10GB
- ✅ <5 commands to go from setup to first notes

---

## 🔮 Future Enhancements (Post-MVP)

### If You Get a GPU Later
- Switch to `large-v3` Whisper + `llama3.1:8b` for better quality
- Enable batch processing with parallel inference
- Real-time transcription during recording

### Advanced Features
- **Multimodal Processing**: Extract slides from video using OCR
- **Knowledge Graph**: Link concepts across multiple lectures
- **Anki Integration**: Auto-generate flashcards
- **RAG Integration**: Build a searchable lecture database

---

## 🤝 Contributing

This is currently a solo project. Once MVP is complete, contributions welcome for:
- Additional output formats
- Model benchmarking on various hardware
- GUI development
- Documentation improvements

---

## 📜 License

MIT License (recommended for maximum adoption)

---

**Last Updated**: 2026-02-02  
**Status**: Phase 1 🚧 → Ready to begin implementation