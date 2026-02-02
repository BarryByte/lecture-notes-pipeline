#!/bin/bash
# Lecture Notes Pipeline - Setup Script
# Optimized for CPU-only systems with 16GB RAM

set -e

echo "🎓 Lecture Notes Pipeline - Setup"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "📋 Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        echo -e "${GREEN}✓ Python $PYTHON_VERSION detected${NC}"
    else
        echo -e "${RED}✗ Python 3.10+ required, found $PYTHON_VERSION${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

# Check FFmpeg and FFprobe
echo ""
echo "📋 Checking FFmpeg and FFprobe..."
MISSING_DEPS=0

if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠ ffmpeg not found.${NC}"
    MISSING_DEPS=1
fi

if ! command -v ffprobe &> /dev/null; then
    echo -e "${YELLOW}⚠ ffprobe not found.${NC}"
    MISSING_DEPS=1
fi

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "${YELLOW}Attempting to install FFmpeg...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y ffmpeg
    elif command -v pacman &> /dev/null; then
        sudo pacman -S ffmpeg
    else
        echo -e "${RED}✗ Please install FFmpeg manually (it should include ffprobe)${NC}"
        exit 1
    fi
else
    FFMPEG_VERSION=$(ffmpeg -version | head -n1 | cut -d' ' -f3)
    echo -e "${GREEN}✓ FFmpeg $FFMPEG_VERSION and FFprobe detected${NC}"
fi

# Check Ollama
echo ""
echo "📋 Checking Ollama..."
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✓ Ollama detected${NC}"
else
    echo -e "${YELLOW}⚠ Ollama not found. Installing...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Create virtual environment
echo ""
echo "🐍 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
fi

# Activate and install dependencies
echo ""
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Python dependencies installed${NC}"

# Create project directories
echo ""
echo "📁 Creating project directories..."
mkdir -p src tests docs examples .cache output
touch src/__init__.py
echo -e "${GREEN}✓ Project structure created${NC}"

# Pull LLM model
echo ""
echo "🤖 Pulling LLM model (llama3.2:3b - recommended for 16GB RAM)..."
echo -e "${YELLOW}This may take a few minutes on first run...${NC}"
ollama pull llama3.2:3b

# Summary
echo ""
echo "=================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo ""
echo "📊 Your Configuration:"
echo "   • Whisper Model: medium (will download on first run, ~1.5GB)"
echo "   • LLM Model: llama3.2:3b (~2GB)"
echo "   • Expected RAM usage: ~8GB peak"
echo ""
echo "🚀 Quick Start:"
echo "   1. Activate environment: source venv/bin/activate"
echo "   2. Run pipeline: python main.py path/to/lecture.mp4"
echo ""
echo "📖 See README.md for more options"
echo "=================================="
