# ==========================================
# 1. IMPORTS & SETUP
# ==========================================

# Third-Party Libraries
import re
import logging

# Logger setup to print info to console
logger = logging.getLogger("uvicorn.error")

# ==========================================
# 2. MAIN PROCESS
# ==========================================

def chunk_text(text, tokenizer=None, max_tokens=256, overlap_tokens=30):
    """
    Splits text into chunks that fit the specific model's context window.
    """
    
    # ==========================================
    # A. SETUP
    # ==========================================.

    if tokenizer:
        # STRATEGY A: Precise Counting (T5, BART)
        def get_token_count(t):
            return len(tokenizer.encode(t, add_special_tokens=False))
            
        def encode_text(t):
            return tokenizer.encode(t, add_special_tokens=False)
            
        def decode_tokens(ids):
            return tokenizer.decode(ids, skip_special_tokens=True)
            
    else:
        # STRATEGY B: Estimation (Mistral, API)
        def get_token_count(t):
            return len(t) // 3 
            
        def encode_text(t):
            return t
            
        def decode_tokens(ids):
            return ids

    # ==========================================
    # B. PRE-SPLITTING
    # ==========================================
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    
    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = get_token_count(para)

        # ==========================================
        # C. HANDLING THE "GIANT PARAGRAPH"
        # ==========================================

        if para_tokens > max_tokens:
            
            # If tokenizer, slice by ID (very precise)
            if tokenizer:
                sub_ids = encode_text(para)
                step = max_tokens - overlap_tokens
                for i in range(0, len(sub_ids), step):
                    chunk_ids = sub_ids[i : i + max_tokens]
                    chunks.append(decode_tokens(chunk_ids))
            
            # If don't, slice by characters (heuristic)
            else:
                char_limit = max_tokens * 3
                overlap_chars = overlap_tokens * 3
                step = char_limit - overlap_chars
                
                for i in range(0, len(para), step):
                    chunks.append(para[i : i + char_limit])
            
            continue
        
        # ==========================================
        # D. BUILDING THE CHUNK
        # ==========================================
        if current_tokens + para_tokens > max_tokens:
            
            # A. Save the current accumulator as a finished chunk
            if current_chunk:
                chunks.append(" ".join(current_chunk))
            
            # B. Handle Overlap
            if overlap_tokens > 0 and chunks:
                previous_text = chunks[-1]
                
                if tokenizer:
                    prev_ids = encode_text(previous_text)
                    # Grab the last N tokens
                    overlap_ids = prev_ids[-overlap_tokens:] 
                    overlap_text = decode_tokens(overlap_ids)
                else:
                    overlap_chars = overlap_tokens * 3
                    overlap_text = previous_text[-overlap_chars:]

                # Start the new bucket containing the overlap
                current_chunk = [overlap_text]
                current_tokens = get_token_count(overlap_text)
            else:
                current_chunk = []
                current_tokens = 0
        
        # Add the paragraph to the current bucket
        current_chunk.append(para)
        current_tokens += para_tokens

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks