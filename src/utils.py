"""
Utility functions for the Lecture Notes Pipeline.
Provides helpers for file I/O, RAM monitoring, caching, and progress display.
"""

import hashlib
import json
import os
import psutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

console = Console()


def get_ram_usage() -> Dict[str, float]:
    """Get current RAM usage statistics.
    
    Returns:
        Dict with 'total', 'available', 'used', 'percent' in GB
    """
    mem = psutil.virtual_memory()
    return {
        'total': mem.total / (1024 ** 3),
        'available': mem.available / (1024 ** 3),
        'used': mem.used / (1024 ** 3),
        'percent': mem.percent
    }


def check_ram_available(required_gb: float = 4.0) -> bool:
    """Check if sufficient RAM is available.
    
    Args:
        required_gb: Minimum required available RAM in GB
        
    Returns:
        True if sufficient RAM available
    """
    available = get_ram_usage()['available']
    if available < required_gb:
        console.print(
            f"[yellow]⚠ Low RAM: {available:.1f}GB available, "
            f"{required_gb:.1f}GB recommended[/yellow]"
        )
        return False
    return True


def get_file_hash(file_path: str) -> str:
    """Generate a hash for a file (for caching purposes).
    
    Uses first 1MB + file size + modification time for speed.
    """
    path = Path(file_path)
    stat = path.stat()
    
    # Read first 1MB for hashing (fast for large files)
    with open(path, 'rb') as f:
        first_chunk = f.read(1024 * 1024)
    
    hash_input = f"{first_chunk}{stat.st_size}{stat.st_mtime}".encode()
    return hashlib.md5(hash_input).hexdigest()[:12]


def get_cache_path(file_path: str, cache_dir: str = ".cache") -> Path:
    """Get the cache file path for a given input file.
    
    Args:
        file_path: Path to the input file
        cache_dir: Directory to store cache files
        
    Returns:
        Path to the cache JSON file
    """
    cache_path = Path(cache_dir)
    cache_path.mkdir(exist_ok=True)
    
    file_hash = get_file_hash(file_path)
    file_name = Path(file_path).stem
    
    return cache_path / f"{file_name}_{file_hash}.json"


def save_to_cache(data: Dict[str, Any], cache_path: Path) -> None:
    """Save data to cache file."""
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"[dim]💾 Cached to {cache_path}[/dim]")


def load_from_cache(cache_path: Path) -> Optional[Dict[str, Any]]:
    """Load data from cache file if it exists."""
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} minutes"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} hours"


def get_video_info(file_path: str) -> Dict[str, Any]:
    """Get basic info about a video file."""
    import ffmpeg
    
    try:
        probe = ffmpeg.probe(file_path)
        
        # Get duration
        duration = float(probe['format'].get('duration', 0))
        
        # Get file size
        size_bytes = int(probe['format'].get('size', 0))
        size_mb = size_bytes / (1024 * 1024)
        
        # Get audio stream info
        audio_streams = [s for s in probe['streams'] if s['codec_type'] == 'audio']
        has_audio = len(audio_streams) > 0
        
        return {
            'duration': duration,
            'duration_formatted': format_duration(duration),
            'size_mb': size_mb,
            'has_audio': has_audio,
            'format': probe['format'].get('format_name', 'unknown')
        }
    except Exception as e:
        console.print(f"[red]Error probing video: {e}[/red]")
        return {}


def create_progress() -> Progress:
    """Create a Rich progress bar instance."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    )


def print_header(title: str) -> None:
    """Print a styled header."""
    console.print()
    console.print(f"[bold blue]{'═' * 50}[/bold blue]")
    console.print(f"[bold blue]  {title}[/bold blue]")
    console.print(f"[bold blue]{'═' * 50}[/bold blue]")
    console.print()


def print_step(step: int, total: int, description: str) -> None:
    """Print a step indicator."""
    console.print(f"[cyan]Step {step}/{total}:[/cyan] {description}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def ensure_dir(path: str) -> Path:
    """Ensure a directory exists, create if not."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cleanup_temp_files(*paths: str) -> None:
    """Remove temporary files."""
    for path in paths:
        try:
            p = Path(path)
            if p.exists():
                p.unlink()
        except Exception:
            pass  # Ignore cleanup errors
