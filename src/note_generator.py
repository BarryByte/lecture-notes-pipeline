"""
Note Generation Module for the Lecture Notes Pipeline.
Uses Ollama with local LLMs to generate structured notes from transcripts.
"""

import time
from typing import Dict, Any, List, Optional, Generator

import ollama

from .utils import (
    console,
    print_success,
    print_warning,
    print_error,
    format_timestamp,
    format_duration,
    get_ram_usage,
    create_progress
)


# Default prompt template for note generation
NOTE_PROMPT_TEMPLATE = """You are an expert educational note-taker. Given a lecture transcript with timestamps, create comprehensive study notes in Markdown format.

## Instructions:
1. **Title**: Derive a clear, descriptive title from the content
2. **Summary**: Write a 2-3 sentence overview of the main topic
3. **Key Concepts**: Extract the most important concepts as bullet points with brief definitions
4. **Detailed Notes**: Organize content by topic with section headers. Include timestamps [MM:SS] for key points
5. **Action Items**: Create 3-5 study questions or exercises based on the content

## Formatting Guidelines:
- Use proper Markdown headers (##, ###)
- Keep bullet points concise
- Include timestamps for important concepts so students can review the video
- Bold key terms
- Use code blocks for any technical content or formulas

## Transcript:
{transcript}

---
Now generate the study notes:"""


CHUNK_SUMMARY_PROMPT = """Summarize this section of a lecture transcript into key points and notes.
Include timestamps [MM:SS] for important topics mentioned.

Transcript section:
{transcript}

Provide a structured summary with:
- Main topics covered
- Key definitions or concepts
- Important details with timestamps"""


MERGE_NOTES_PROMPT = """You are merging notes from different sections of the same lecture into a cohesive document.

Combine these section notes into a single, well-organized study document:

{section_notes}

Create a unified document with:
1. **Title** - A descriptive title for the entire lecture
2. **Summary** - 2-3 sentence overview of all topics
3. **Table of Contents** - List major sections with timestamps
4. **Key Concepts** - Combined list of important terms/definitions
5. **Detailed Notes** - Merged, organized by topic with timestamps
6. **Action Items** - 3-5 study questions covering the full lecture

Ensure smooth transitions and remove any redundancy."""


class NoteGenerator:
    """Generates structured notes from transcripts using Ollama."""
    
    def __init__(
        self,
        model: str = "llama3.2:3b",
        temperature: float = 0.3,
        chunk_size: int = 8000,
        ollama_host: Optional[str] = None
    ):
        """Initialize the note generator.
        
        Args:
            model: Ollama model name
            temperature: Generation temperature (0-1, lower = more focused)
            chunk_size: Maximum tokens per chunk for long transcripts
            ollama_host: Ollama server URL (default: localhost:11434)
        """
        self.model = model
        self.temperature = temperature
        self.chunk_size = chunk_size
        self.client = ollama.Client(host=ollama_host) if ollama_host else ollama.Client()
        
    def check_model_available(self) -> bool:
        """Check if the specified model is available in Ollama."""
        try:
            models_response = self.client.list()
            
            # Handle both object-based response (newer ollama lib) and dict-based (older)
            models = getattr(models_response, 'models', None) or models_response.get('models', [])
            
            model_names = []
            for m in models:
                # Handle Model objects (newer) or dictionaries (older)
                name = getattr(m, 'model', None) or (m.get('model') if hasattr(m, 'get') else None) or (m.get('name') if hasattr(m, 'get') else None)
                if name:
                    model_names.append(name)
            
            # Check for exact match or base name match
            if self.model in model_names:
                return True
            
            # Check without tag (e.g., 'llama3.2:3b' -> 'llama3.2')
            base_name = self.model.split(':')[0]
            for name in model_names:
                if name.startswith(base_name):
                    return True
                    
            return False
        except Exception as e:
            print_error(f"Could not connect to Ollama: {e}")
            return False
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough estimation of token count (words * 1.3)."""
        return int(len(text.split()) * 1.3)
    
    def _chunk_transcript(self, transcript: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split a long transcript into manageable chunks.
        
        Chunks are split at segment boundaries to maintain context.
        """
        segments = transcript.get('segments', [])
        if not segments:
            return [transcript]
        
        chunks: List[Dict[str, Any]] = []
        current_chunk_segments: List[Dict] = []
        current_token_count = 0
        
        for segment in segments:
            segment_tokens = self._estimate_tokens(segment['text'])
            
            if current_token_count + segment_tokens > self.chunk_size and current_chunk_segments:
                # Save current chunk
                chunks.append(self._create_chunk_transcript(current_chunk_segments))
                current_chunk_segments = []
                current_token_count = 0
            
            current_chunk_segments.append(segment)
            current_token_count += segment_tokens
        
        # Don't forget the last chunk
        if current_chunk_segments:
            chunks.append(self._create_chunk_transcript(current_chunk_segments))
        
        return chunks
    
    def _create_chunk_transcript(self, segments: List[Dict]) -> Dict[str, Any]:
        """Create a transcript dict from a list of segments."""
        return {
            'text': ' '.join(s['text'] for s in segments),
            'segments': segments,
            'start_time': segments[0]['start'] if segments else 0,
            'end_time': segments[-1]['end'] if segments else 0
        }
    
    def _format_transcript_for_prompt(self, transcript: Dict[str, Any]) -> str:
        """Format transcript with timestamps for the prompt."""
        segments = transcript.get('segments', [])
        
        if not segments:
            return transcript.get('text', '')
        
        formatted_parts = []
        for seg in segments:
            timestamp = seg.get('start_formatted', format_timestamp(seg.get('start', 0)))
            text = seg.get('text', '')
            formatted_parts.append(f"[{timestamp}] {text}")
        
        return '\n'.join(formatted_parts)
    
    def _stream_generate(self, prompt: str) -> Generator[str, None, str]:
        """Generate text with streaming output."""
        full_response = ""
        
        try:
            stream = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': self.temperature,
                    'num_predict': 4096,  # Max tokens to generate
                },
                stream=True
            )
            
            for chunk in stream:
                text = chunk.get('response', '')
                full_response += text
                yield text
                
        except Exception as e:
            print_error(f"Generation error: {e}")
            raise
        
        return full_response
    
    def generate_notes(
        self,
        transcript: Dict[str, Any],
        stream_output: bool = True
    ) -> str:
        """Generate notes from a transcript.
        
        Args:
            transcript: Transcript dict from the transcriber
            stream_output: Whether to stream output to console
            
        Returns:
            Generated notes in Markdown format
        """
        # Check model availability
        if not self.check_model_available():
            raise RuntimeError(
                f"Model '{self.model}' not found. "
                f"Run: ollama pull {self.model}"
            )
        
        # Report RAM before generation
        ram = get_ram_usage()
        console.print(
            f"[dim]RAM before generation: {ram['used']:.1f}GB / {ram['total']:.1f}GB[/dim]"
        )
        
        # Check if we need to chunk
        total_tokens = self._estimate_tokens(transcript.get('text', ''))
        
        console.print(f"[cyan]Generating notes with {self.model}[/cyan]")
        console.print(f"[dim]  Transcript: ~{total_tokens} tokens[/dim]")
        
        start_time = time.time()
        
        if total_tokens > self.chunk_size:
            # Process in chunks
            notes = self._generate_chunked(transcript, stream_output)
        else:
            # Direct generation
            notes = self._generate_single(transcript, stream_output)
        
        generation_time = time.time() - start_time
        print_success(f"Notes generated in {format_duration(generation_time)}")
        
        return notes
    
    def _generate_single(
        self,
        transcript: Dict[str, Any],
        stream_output: bool = True
    ) -> str:
        """Generate notes for a single (short) transcript."""
        formatted_transcript = self._format_transcript_for_prompt(transcript)
        prompt = NOTE_PROMPT_TEMPLATE.format(transcript=formatted_transcript)
        
        if stream_output:
            console.print("\n[bold]Generated Notes:[/bold]\n")
            full_response = ""
            for chunk in self._stream_generate(prompt):
                console.print(chunk, end="")
                full_response += chunk
            console.print("\n")
            return full_response
        else:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={'temperature': self.temperature}
            )
            return response.get('response', '')
    
    def _generate_chunked(
        self,
        transcript: Dict[str, Any],
        stream_output: bool = True
    ) -> str:
        """Generate notes for a long transcript in chunks, then merge."""
        chunks = self._chunk_transcript(transcript)
        
        console.print(f"[yellow]Long transcript detected. Processing in {len(chunks)} chunks...[/yellow]")
        
        section_notes: List[str] = []
        
        with create_progress() as progress:
            task = progress.add_task("[cyan]Processing chunks", total=len(chunks))
            
            for i, chunk in enumerate(chunks):
                start_time = format_timestamp(chunk.get('start_time', 0))
                end_time = format_timestamp(chunk.get('end_time', 0))
                
                console.print(f"\n[dim]Chunk {i+1}/{len(chunks)} [{start_time} - {end_time}][/dim]")
                
                formatted = self._format_transcript_for_prompt(chunk)
                prompt = CHUNK_SUMMARY_PROMPT.format(transcript=formatted)
                
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    options={'temperature': self.temperature}
                )
                
                section_notes.append(
                    f"## Section {i+1} [{start_time} - {end_time}]\n\n"
                    f"{response.get('response', '')}"
                )
                
                progress.update(task, advance=1)
        
        # Merge all sections
        console.print("\n[cyan]Merging sections into final notes...[/cyan]")
        
        merged_sections = "\n\n---\n\n".join(section_notes)
        merge_prompt = MERGE_NOTES_PROMPT.format(section_notes=merged_sections)
        
        if stream_output:
            console.print("\n[bold]Generated Notes:[/bold]\n")
            full_response = ""
            for chunk in self._stream_generate(merge_prompt):
                console.print(chunk, end="")
                full_response += chunk
            console.print("\n")
            return full_response
        else:
            response = self.client.generate(
                model=self.model,
                prompt=merge_prompt,
                options={'temperature': self.temperature}
            )
            return response.get('response', '')


def generate_notes(
    transcript: Dict[str, Any],
    model: str = "llama3.2:3b",
    chunk_size: int = 8000
) -> str:
    """Convenience function for one-shot note generation.
    
    Args:
        transcript: Transcript dict from the transcriber
        model: Ollama model name
        chunk_size: Maximum tokens per chunk
        
    Returns:
        Generated notes in Markdown format
    """
    generator = NoteGenerator(model=model, chunk_size=chunk_size)
    return generator.generate_notes(transcript)
