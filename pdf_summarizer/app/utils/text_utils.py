import re
from transformers import T5Tokenizer

tokenizer = T5Tokenizer.from_pretrained("t5-small")  # You can switch dynamically later

def chunk_text(text, max_tokens=400, overlap_tokens=50):
    """
    Split text into coherent chunks with paragraph-awareness and optional overlap.
    
    Args:
        text (str): The full text to chunk.
        max_tokens (int): Approximate max tokens per chunk.
        overlap_tokens (int): Tokens to overlap between consecutive chunks.

    Returns:
        List[str]: List of text chunks.
    """
    # 1. Split by paragraphs (also handles double newlines)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    
    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = len(tokenizer.encode(para))

        if para_tokens > max_tokens:
            # Split paragraph into smaller sub-paragraphs
            sub_ids = tokenizer.encode(para)
            for i in range(0, len(sub_ids), max_tokens - overlap_tokens):
                sub_text = tokenizer.decode(sub_ids[i:i + (max_tokens - overlap_tokens)])
                chunks.append(sub_text)
            continue
        
        # If adding this paragraph exceeds max_tokens, finalize current chunk
        if current_tokens + para_tokens > max_tokens:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            
            # Start new chunk, include overlap from previous if needed
            if overlap_tokens > 0 and chunks:
                # Take last N tokens from previous chunk as overlap
                overlap_text = " ".join(current_chunk)
                overlap_ids = tokenizer.encode(overlap_text)[-overlap_tokens:]
                overlap_text = tokenizer.decode(overlap_ids)
                current_chunk = [overlap_text]
                current_tokens = len(overlap_ids)
            else:
                current_chunk = []
                current_tokens = 0
        
        current_chunk.append(para)
        current_tokens += para_tokens

    # Add final chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks
