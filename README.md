# 🎓 Lecture Notes Pipeline

A fully local, privacy-first pipeline that transforms lecture videos into structured study notes using AI. **No data leaves your device.**

## ✨ Features

- **100% Offline** - All processing happens locally
- **CPU Optimized** - Works great on systems without GPU
- **Smart Notes** - AI-generated summaries, key concepts, and study questions
- **Timestamps** - Notes linked to video timestamps for easy reference
- **Multiple Formats** - Supports MP4, MKV, AVI, WebM

## 💻 Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 8GB | 16GB |
| **Storage** | 5GB free | 10GB free |
| **Python** | 3.10+ | 3.11+ |
| **OS** | Linux, macOS, Windows (WSL) | Linux |

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/lecture-notes-pipeline.git
cd lecture-notes-pipeline
bash setup.sh
```

The setup script will:
- Check Python version
- Install FFmpeg (if needed)
- Install Ollama (if needed)
- Create virtual environment
- Install Python dependencies
- Pull the recommended LLM model

### 2. Activate Environment

```bash
source venv/bin/activate
```

### 3. Process a Lecture

```bash
python main.py path/to/lecture.mp4
```

Your notes will be saved as `lecture_notes.md` in the current directory.

## ⚙️ Configuration

### Command Line Options

```bash
python main.py lecture.mp4 [OPTIONS]

Options:
  --output, -o PATH       Output directory (default: current dir)
  --language, -l CODE     Language code, e.g., 'en', 'es' (default: auto)
  --whisper-model MODEL   Whisper model size (default: medium)
  --llm-model MODEL       Ollama model name (default: llama3.2:3b)
  --verbose, -v           Enable debug logging
  --help                  Show help message
```

### Model Options

#### Whisper (Speech-to-Text)

| Model | RAM | Speed | Accuracy | Use Case |
|-------|-----|-------|----------|----------|
| `small` | ~2GB | Fast | Good | Quick drafts |
| `medium` | ~4GB | Medium | Great | **Default** |
| `large-v3` | ~8GB | Slow | Best | Critical accuracy |

#### LLM (Note Generation)

| Model | RAM | Speed | Quality |
|-------|-----|-------|---------|
| `phi3:mini` | ~4GB | Fast | Good |
| `llama3.2:3b` | ~4GB | Fast | **Great** |
| `mistral:7b` | ~6GB | Medium | Excellent |

### Configuration File

Create `config.yaml` for persistent settings:

```yaml
whisper:
  model: medium
  language: null  # auto-detect

llm:
  model: llama3.2:3b
  temperature: 0.3

output:
  format: markdown
  include_timestamps: true
```

## 📊 Performance (16GB RAM, CPU)

| Lecture Length | Transcription | Notes | Total |
|----------------|---------------|-------|-------|
| 15 min | ~9 min | ~1 min | ~10 min |
| 60 min | ~36 min | ~5 min | ~41 min |
| 120 min | ~72 min | ~10 min | ~82 min |

*Times measured with `medium` Whisper + `llama3.2:3b`*

## 📁 Project Structure

```
lecture-notes-pipeline/
├── src/
│   ├── audio_extractor.py  # FFmpeg wrapper
│   ├── transcriber.py      # Whisper integration
│   ├── note_generator.py   # LLM note creation
│   └── utils.py            # Helpers
├── main.py                 # CLI entry point
├── config.yaml             # Settings
├── requirements.txt
├── setup.sh
└── README.md
```

## 🔧 Troubleshooting

### "Out of memory" error
- Use a smaller Whisper model: `--whisper-model small`
- Use a smaller LLM: `--llm-model phi3:mini`
- Close other applications

### Slow transcription
- This is normal for CPU-only systems
- Consider processing overnight for long lectures
- Enable caching to avoid re-transcription

### Poor transcription quality
- Use `--whisper-model large-v3` (slower but more accurate)
- Ensure good audio quality in source video
- Specify language explicitly: `--language en`

### Ollama not responding
```bash
# Restart Ollama service
sudo systemctl restart ollama
# Or start manually
ollama serve
```

## 🛡️ Privacy

- **No internet required** after initial setup
- **No data transmitted** - all AI runs locally
- **No telemetry** - zero tracking or analytics
- Transcripts cached locally in `.cache/` (gitignored)

## 📜 License

MIT License - see [LICENSE](LICENSE)

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

---

Made with ☕ for students who hate taking notes
