import re

def chunk_text(text, tokenizer=None, max_tokens=256, overlap_tokens=30):
    """
    Split text into smaller, safer chunks to avoid context window overflows.
    Defaults: max_tokens=256 (was 400), overlap=30 (was 50).
    """
    
    # --- 1. Define Helper Functions for Counting/Slicing ---
    if tokenizer:
        def get_token_count(t):
            # add_special_tokens=False is crucial
            return len(tokenizer.encode(t, add_special_tokens=False))
            
        def encode_text(t):
            return tokenizer.encode(t, add_special_tokens=False)
            
        def decode_tokens(ids):
            return tokenizer.decode(ids, skip_special_tokens=True)
    else:
        # Fallback for Mistral/API
        # Heuristic Changed: 1 token ~= 3 characters (was 4).
        # This estimates a HIGHER token count, forcing the code to split text SOONER.
        def get_token_count(t):
            return len(t) // 3 
            
        def encode_text(t):
            return t 
            
        def decode_tokens(ids):
            return ids

    # --- 2. Paragraph Splitting ---
    # Split by double newline to respect paragraphs
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    
    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = get_token_count(para)

        # --- 3. Handle Oversized Paragraphs ---
        if para_tokens > max_tokens:
            # We need to split this specific paragraph
            if tokenizer:
                sub_ids = encode_text(para)
                step = max_tokens - overlap_tokens
                for i in range(0, len(sub_ids), step):
                    chunk_ids = sub_ids[i : i + max_tokens]
                    chunks.append(decode_tokens(chunk_ids))
            else:
                # Heuristic split
                # Since we use len(t)//3 for count, we use max_tokens * 3 for slicing limits
                char_limit = max_tokens * 3
                overlap_chars = overlap_tokens * 3
                step = char_limit - overlap_chars
                
                for i in range(0, len(para), step):
                    chunks.append(para[i : i + char_limit])
            continue
        
        # --- 4. Build Chunks ---
        if current_tokens + para_tokens > max_tokens:
            # Finalize current chunk
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            
            # Handle Overlap
            if overlap_tokens > 0 and chunks:
                previous_text = chunks[-1]
                
                if tokenizer:
                    prev_ids = encode_text(previous_text)
                    overlap_ids = prev_ids[-overlap_tokens:]
                    overlap_text = decode_tokens(overlap_ids)
                else:
                    # Heuristic overlap
                    overlap_chars = overlap_tokens * 3
                    overlap_text = previous_text[-overlap_chars:]

                current_chunk = [overlap_text]
                current_tokens = get_token_count(overlap_text)
            else:
                current_chunk = []
                current_tokens = 0
        
        current_chunk.append(para)
        current_tokens += para_tokens

    # Add final chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks