"""
Audio Extraction Module for the Lecture Notes Pipeline.
Extracts audio from video files using FFmpeg.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional

import ffmpeg

from .utils import console, print_success, print_error, get_video_info


# Supported video formats
SUPPORTED_FORMATS = {'.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv', '.wmv', '.m4v'}


def validate_video_file(video_path: str) -> bool:
    """Validate that the input file exists and is a supported video format.
    
    Args:
        video_path: Path to the video file
        
    Returns:
        True if valid, raises exception otherwise
    """
    path = Path(video_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format: {path.suffix}. "
            f"Supported: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # Check if file has audio
    info = get_video_info(video_path)
    if not info.get('has_audio', False):
        raise ValueError("Video file has no audio track")
    
    return True


def extract_audio(
    video_path: str,
    output_dir: Optional[str] = None,
    output_filename: Optional[str] = None,
    sample_rate: int = 16000,
    mono: bool = True
) -> str:
    """Extract audio from a video file.
    
    Converts to WAV format at 16kHz mono (Whisper's preferred format).
    
    Args:
        video_path: Path to the input video file
        output_dir: Directory to save the audio file (default: temp directory)
        output_filename: Custom output filename (default: derived from video name)
        sample_rate: Audio sample rate in Hz (default: 16000 for Whisper)
        mono: Convert to mono audio (default: True for Whisper)
        
    Returns:
        Path to the extracted WAV file
    """
    # Validate input
    validate_video_file(video_path)
    
    video_path = Path(video_path)
    
    # Determine output path
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if output_filename is None:
        output_filename = f"{video_path.stem}_audio.wav"
    
    output_path = output_dir / output_filename
    
    console.print(f"[dim]Extracting audio from: {video_path.name}[/dim]")
    
    try:
        # Build FFmpeg command
        stream = ffmpeg.input(str(video_path))
        
        # Audio extraction options
        audio_options = {
            'acodec': 'pcm_s16le',  # 16-bit PCM
            'ar': sample_rate,       # Sample rate
        }
        
        if mono:
            audio_options['ac'] = 1  # Mono channel
        
        stream = ffmpeg.output(
            stream.audio,
            str(output_path),
            **audio_options
        )
        
        # Run with overwrite and quiet mode
        ffmpeg.run(
            stream,
            overwrite_output=True,
            quiet=True,
            capture_stdout=True,
            capture_stderr=True
        )
        
        # Verify output
        if not output_path.exists():
            raise RuntimeError("Audio extraction failed: output file not created")
        
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        print_success(f"Audio extracted: {output_path.name} ({file_size_mb:.1f} MB)")
        
        return str(output_path)
        
    except ffmpeg.Error as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print_error(f"FFmpeg error: {error_msg}")
        raise RuntimeError(f"Audio extraction failed: {error_msg}")
    
    except Exception as e:
        print_error(f"Extraction error: {e}")
        raise


def get_audio_duration(audio_path: str) -> float:
    """Get the duration of an audio file in seconds."""
    try:
        probe = ffmpeg.probe(audio_path)
        return float(probe['format']['duration'])
    except Exception:
        return 0.0
