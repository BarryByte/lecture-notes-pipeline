#!/usr/bin/env python3
"""
Lecture Notes Pipeline - Main CLI Entry Point

Transforms lecture videos into structured study notes using local AI.
100% offline, privacy-first processing.

Usage:
    python main.py lecture.mp4
    python main.py lecture.mp4 --output ./notes --whisper-model medium
"""

import sys
import time
from pathlib import Path
from typing import Optional

import click
import yaml

from src.audio_extractor import extract_audio, get_audio_duration
from src.transcriber import Transcriber
from src.note_generator import NoteGenerator
from src.utils import (
    console,
    print_header,
    print_step,
    print_success,
    print_error,
    print_warning,
    get_video_info,
    get_ram_usage,
    check_ram_available,
    format_duration,
    cleanup_temp_files,
    ensure_dir
)


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            return yaml.safe_load(f) or {}
    
    return {}


@click.command()
@click.argument('video_path', type=click.Path(exists=True))
@click.option(
    '--output', '-o',
    type=click.Path(),
    default=None,
    help='Output directory for notes (default: current directory)'
)
@click.option(
    '--language', '-l',
    default=None,
    help='Language code (e.g., en, es, de). Auto-detect if not specified'
)
@click.option(
    '--whisper-model', '-w',
    type=click.Choice(['tiny', 'base', 'small', 'medium', 'large-v3']),
    default=None,
    help='Whisper model size (default: medium)'
)
@click.option(
    '--llm-model', '-m',
    default=None,
    help='Ollama model name (default: llama3.2:3b)'
)
@click.option(
    '--no-cache',
    is_flag=True,
    help='Disable transcript caching'
)
@click.option(
    '--no-stream',
    is_flag=True,
    help='Disable streaming output for note generation'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
@click.option(
    '--extract-actions/--no-extract-actions',
    default=None,
    help='Extract upcoming classes, homework, and deadlines (default: from config)'
)
@click.option(
    '--config', '-c',
    type=click.Path(),
    default='config.yaml',
    help='Path to config file'
)
def main(
    video_path: str,
    output: Optional[str],
    language: Optional[str],
    whisper_model: Optional[str],
    llm_model: Optional[str],
    no_cache: bool,
    no_stream: bool,
    verbose: bool,
    extract_actions: Optional[bool],
    config: str
):
    """
    Transform lecture videos into structured study notes.
    
    VIDEO_PATH: Path to the video file (MP4, MKV, AVI, WebM, etc.)
    """
    start_time = time.time()
    temp_audio_path = None
    
    try:
        # Load config file
        cfg = load_config(config)
        
        # Merge CLI options with config (CLI takes precedence)
        whisper_model = whisper_model or cfg.get('whisper', {}).get('model', 'medium')
        llm_model = llm_model or cfg.get('llm', {}).get('model', 'llama3.2:3b')
        language = language or cfg.get('whisper', {}).get('language')
        cache_enabled = not no_cache and cfg.get('processing', {}).get('cache_enabled', True)
        cache_dir = cfg.get('processing', {}).get('cache_dir', '.cache')
        chunk_size = cfg.get('processing', {}).get('chunk_size', 8000)
        output_dir = output or cfg.get('output', {}).get('directory', '.')
        extract_actions_enabled = extract_actions if extract_actions is not None else cfg.get('output', {}).get('extract_action_items', True)
        
        # Determine total steps
        total_steps = 5 if extract_actions_enabled else 4
        
        # Print header
        print_header("🎓 Lecture Notes Pipeline")
        
        video_path = Path(video_path)
        
        # Step 1: Validate and get video info
        print_step(1, total_steps, "Analyzing video file")
        
        video_info = get_video_info(str(video_path))
        if not video_info:
            print_error("Could not read video file")
            sys.exit(1)
        
        console.print(f"  📁 File: [bold]{video_path.name}[/bold]")
        console.print(f"  ⏱️  Duration: {video_info.get('duration_formatted', 'unknown')}")
        console.print(f"  💾 Size: {video_info.get('size_mb', 0):.1f} MB")
        
        if not video_info.get('has_audio'):
            print_error("Video has no audio track!")
            sys.exit(1)
        
        print_success("Video validated")
        
        # Check RAM
        ram = get_ram_usage()
        console.print(f"\n  💻 System RAM: {ram['available']:.1f}GB available / {ram['total']:.1f}GB total")
        
        if ram['available'] < 4:
            print_warning("Low RAM available. Consider using smaller models.")
        
        # Estimate processing time
        duration = video_info.get('duration', 0)
        est_transcription = duration * 0.6  # RTF ~0.6 for medium model on CPU
        est_generation = 300  # ~5 min for note generation
        console.print(f"\n  ⏳ Estimated time: {format_duration(est_transcription + est_generation)}")
        
        console.print()
        
        # Step 2: Extract audio
        print_step(2, total_steps, "Extracting audio")
        
        temp_audio_path = extract_audio(
            str(video_path),
            output_dir=cache_dir  # Store in cache directory
        )
        
        console.print()
        
        # Step 3: Transcribe
        print_step(3, total_steps, f"Transcribing with Whisper ({whisper_model})")
        
        transcriber = Transcriber(
            model_size=whisper_model,
            cache_enabled=cache_enabled,
            cache_dir=cache_dir
        )
        
        try:
            transcript = transcriber.transcribe(
                temp_audio_path,
                language=language,
                source_file_path=str(video_path)  # Use video for cache key
            )
        finally:
            # Unload Whisper to free RAM for LLM
            transcriber.unload_model()
        
        if verbose:
            console.print(f"\n[dim]Transcript preview: {transcript['text'][:500]}...[/dim]\n")
        
        console.print()
        
        # Step 4: Generate notes
        print_step(4, total_steps, f"Generating notes with {llm_model}")
        
        generator = NoteGenerator(
            model=llm_model,
            chunk_size=chunk_size
        )
        
        notes = generator.generate_notes(
            transcript,
            stream_output=not no_stream
        )
        
        # Save notes
        output_dir = ensure_dir(output_dir)
        output_filename = f"{video_path.stem}_notes.md"
        output_path = output_dir / output_filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            # Add metadata header
            f.write(f"<!-- Generated by Lecture Notes Pipeline -->\n")
            f.write(f"<!-- Source: {video_path.name} -->\n")
            f.write(f"<!-- Duration: {video_info.get('duration_formatted', 'unknown')} -->\n")
            f.write(f"<!-- Language: {transcript.get('language', 'unknown')} -->\n\n")
            f.write(notes)
        
        # Step 5: Extract action items (if enabled)
        action_items_path = None
        if extract_actions_enabled:
            console.print()
            print_step(5, 5, "Extracting action items")
            
            action_items = generator.extract_action_items(
                transcript,
                stream_output=not no_stream
            )
            
            # Save action items
            action_items_filename = f"{video_path.stem}_action_items.md"
            action_items_path = output_dir / action_items_filename
            
            with open(action_items_path, 'w', encoding='utf-8') as f:
                f.write(f"<!-- Extracted by Lecture Notes Pipeline -->\n")
                f.write(f"<!-- Source: {video_path.name} -->\n\n")
                f.write(action_items)
        
        # Final summary
        total_time = time.time() - start_time
        
        console.print()
        print_header("✅ Complete!")
        
        console.print(f"  📝 Notes saved to: [bold green]{output_path}[/bold green]")
        if action_items_path:
            console.print(f"  📋 Action items saved to: [bold green]{action_items_path}[/bold green]")
        console.print(f"  ⏱️  Total time: {format_duration(total_time)}")
        console.print(f"  📊 Transcript: {len(transcript['segments'])} segments, {len(transcript['text'].split())} words")
        console.print()
        
        # Cleanup
        if temp_audio_path and not cache_enabled:
            cleanup_temp_files(temp_audio_path)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        sys.exit(130)
        
    except FileNotFoundError as e:
        print_error(str(e))
        sys.exit(1)
        
    except Exception as e:
        print_error(f"Error: {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)
        
    finally:
        # Cleanup temp files on error
        if temp_audio_path and not cache_enabled:
            cleanup_temp_files(temp_audio_path)


if __name__ == '__main__':
    main()
