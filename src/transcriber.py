"""
Transcription Module for the Lecture Notes Pipeline.
Uses faster-whisper for CPU-optimized speech-to-text.
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from faster_whisper import WhisperModel

from .utils import (
    console, 
    print_success, 
    print_warning,
    format_timestamp,
    format_duration,
    get_ram_usage,
    check_ram_available,
    get_cache_path,
    save_to_cache,
    load_from_cache,
    create_progress
)


# Model configurations
MODEL_CONFIGS = {
    'tiny': {'size': '~75MB', 'ram': 1, 'accuracy': '★★☆☆☆'},
    'base': {'size': '~150MB', 'ram': 1, 'accuracy': '★★★☆☆'},
    'small': {'size': '~500MB', 'ram': 2, 'accuracy': '★★★★☆'},
    'medium': {'size': '~1.5GB', 'ram': 4, 'accuracy': '★★★★☆'},
    'large-v3': {'size': '~3GB', 'ram': 8, 'accuracy': '★★★★★'},
}


class Transcriber:
    """Handles audio transcription using faster-whisper."""
    
    def __init__(
        self,
        model_size: str = "medium",
        compute_type: str = "int8",
        device: str = "cpu",
        cache_enabled: bool = True,
        cache_dir: str = ".cache"
    ):
        """Initialize the transcriber.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v3)
            compute_type: Computation type (int8 for CPU, float16 for GPU)
            device: Device to use (cpu or cuda)
            cache_enabled: Whether to cache transcripts
            cache_dir: Directory for cache files
        """
        self.model_size = model_size
        self.compute_type = compute_type
        self.device = device
        self.cache_enabled = cache_enabled
        self.cache_dir = cache_dir
        self.model: Optional[WhisperModel] = None
        
        # Validate model size
        if model_size not in MODEL_CONFIGS:
            raise ValueError(
                f"Invalid model size: {model_size}. "
                f"Choose from: {', '.join(MODEL_CONFIGS.keys())}"
            )
    
    def load_model(self) -> None:
        """Load the Whisper model into memory."""
        if self.model is not None:
            return  # Already loaded
        
        config = MODEL_CONFIGS[self.model_size]
        
        console.print(f"[cyan]Loading Whisper model: {self.model_size}[/cyan]")
        console.print(f"[dim]  Size: {config['size']} | RAM: ~{config['ram']}GB | Accuracy: {config['accuracy']}[/dim]")
        
        # Check RAM before loading
        check_ram_available(config['ram'])
        
        start_time = time.time()
        
        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            cpu_threads=4,  # Adjust based on your CPU
            num_workers=2
        )
        
        load_time = time.time() - start_time
        print_success(f"Model loaded in {load_time:.1f}s")
        
        # Report RAM usage after loading
        ram = get_ram_usage()
        console.print(f"[dim]  RAM usage: {ram['used']:.1f}GB / {ram['total']:.1f}GB ({ram['percent']:.0f}%)[/dim]")
    
    def unload_model(self) -> None:
        """Unload the model to free memory."""
        if self.model is not None:
            del self.model
            self.model = None
            console.print("[dim]Whisper model unloaded[/dim]")
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        beam_size: int = 5,
        word_timestamps: bool = True,
        source_file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe an audio file.
        
        Args:
            audio_path: Path to the audio file
            language: Language code (e.g., 'en', 'es') or None for auto-detect
            beam_size: Beam size for decoding (higher = more accurate but slower)
            word_timestamps: Whether to include word-level timestamps
            source_file_path: Original source file (e.g., video) for cache key.
                              If provided, cache is keyed by this file instead of audio.
            
        Returns:
            Dict containing:
                - text: Full transcript text
                - segments: List of segments with timestamps
                - language: Detected language
                - duration: Audio duration in seconds
                - metadata: Processing metadata
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Check cache first (use source file for cache key if provided)
        if self.cache_enabled:
            cache_key_file = source_file_path or str(audio_path)
            cache_path = get_cache_path(cache_key_file, self.cache_dir)
            cached = load_from_cache(cache_path)
            if cached:
                console.print("[green]✓[/green] Using cached transcript")
                return cached
        
        # Load model if not already loaded
        self.load_model()
        
        console.print(f"[cyan]Transcribing: {audio_path.name}[/cyan]")
        if language:
            console.print(f"[dim]  Language: {language}[/dim]")
        else:
            console.print("[dim]  Language: auto-detect[/dim]")
        
        start_time = time.time()
        
        # Run transcription
        segments_gen, info = self.model.transcribe(
            str(audio_path),
            language=language,
            beam_size=beam_size,
            word_timestamps=word_timestamps,
            vad_filter=True,  # Filter out silence
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200
            )
        )
        
        # Collect segments with progress
        segments: List[Dict[str, Any]] = []
        full_text_parts: List[str] = []
        
        duration = info.duration if hasattr(info, 'duration') else 0
        
        with create_progress() as progress:
            task = progress.add_task(
                f"[cyan]Transcribing ({format_duration(duration)})",
                total=duration if duration > 0 else 100
            )
            
            for segment in segments_gen:
                segment_dict = {
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip(),
                    'start_formatted': format_timestamp(segment.start),
                    'end_formatted': format_timestamp(segment.end)
                }
                
                # Add word-level timestamps if available
                if word_timestamps and segment.words:
                    segment_dict['words'] = [
                        {
                            'word': w.word,
                            'start': w.start,
                            'end': w.end,
                            'probability': w.probability
                        }
                        for w in segment.words
                    ]
                
                segments.append(segment_dict)
                full_text_parts.append(segment.text.strip())
                
                # Update progress
                progress.update(task, completed=segment.end)
        
        transcription_time = time.time() - start_time
        rtf = transcription_time / duration if duration > 0 else 0
        
        result = {
            'text': ' '.join(full_text_parts),
            'segments': segments,
            'language': info.language,
            'language_probability': info.language_probability,
            'duration': duration,
            'metadata': {
                'model': self.model_size,
                'compute_type': self.compute_type,
                'transcription_time': transcription_time,
                'rtf': rtf,  # Real-Time Factor
                'audio_file': str(audio_path),
                'segment_count': len(segments)
            }
        }
        
        # Report results
        print_success(
            f"Transcription complete: {len(segments)} segments, "
            f"{len(result['text'].split())} words"
        )
        console.print(
            f"[dim]  Time: {format_duration(transcription_time)} | "
            f"RTF: {rtf:.2f}x | Language: {info.language} ({info.language_probability:.0%})[/dim]"
        )
        
        # Cache the result
        if self.cache_enabled:
            save_to_cache(result, cache_path)
        
        return result


def transcribe(
    audio_path: str,
    model_size: str = "medium",
    language: Optional[str] = None,
    cache_dir: str = ".cache"
) -> Dict[str, Any]:
    """Convenience function for one-shot transcription.
    
    Args:
        audio_path: Path to the audio file
        model_size: Whisper model size
        language: Language code or None for auto-detect
        cache_dir: Directory for cache files
        
    Returns:
        Transcription result dict
    """
    transcriber = Transcriber(
        model_size=model_size,
        cache_dir=cache_dir
    )
    try:
        return transcriber.transcribe(audio_path, language=language)
    finally:
        transcriber.unload_model()
