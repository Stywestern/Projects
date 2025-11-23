# System Architecture

## 1. High-Level Data Flow
1.  **Ingestion:** User uploads PDF (Frontend) -> `main.py` (Backend).
2.  **Extraction:** `fitz` (PyMuPDF) extracts raw text.
3.  **Chunking:** Text is split based on the selected model's "Context Window" (see `text_utils.py`).
4.  **Processing (Map Phase):**
    * The backend yields "Progress Updates" (`PROGRESS:x/y`) after every chunk.
    * Chunks are processed sequentially to save RAM (Async Generator).
5.  **Synthesis (Reduce Phase):**
    * All chunk summaries are concatenated.
    * The LLM is called one last time to "Summarize the summaries."
6.  **Response:** The final text is streamed (`SUMMARY:text`) to the client.

## 2. Key Design Decisions

### The Streaming Protocol
Instead of WebSockets (complex), we use **Server-Sent Events (SSE)** via a standard HTTP POST with `Transfer-Encoding: chunked`.
* **Format:** The stream sends plain text lines.
* **Tags:**
    * `PROGRESS:CURRENT/TOTAL`: Updates the UI bar.
    * `SUMMARY:CONTENT`: Delivers the final payload.
    * `ERROR:MESSAGE`: Handles failures gracefully.

### Map-Reduce Strategy
We use Map-Reduce to handle PDFs larger than the LLM context window.
* **Map:** `summarize_{model}` iterates over chunks.
* **Reduce:** `finalize_{model}` takes the combined outputs and generates a cohesive narrative.

### Dynamic Chunking (Mistral)
Mistral uses a "Dynamic Density" calculation.
* *Formula:* `MaxTokens = SafeContext / TotalChunks`.
* *Reason:* If a PDF has 50 pages, we cannot generate 500-token summaries for each, or the final "Reduce" step will overflow the 4096 context limit. We dynamically shrink the summary size as the document grows.

# Process Chart
sequenceDiagram
    autonumber
    actor User
    participant FE as Frontend (main.js)
    participant API as Backend API (main.py)
    participant Router as Router (upload.py)
    participant Orch as Orchestrator (summarizer.py)
    participant Utils as Utilities (text_utils.py)
    participant Loader as Model Loader
    participant Worker as AI Workers (summarizers.py)

    Note over User, FE: Phase 1: Ingestion
    User->>FE: Uploads PDF + Selects Model
    FE->>API: POST /upload (FormData: file, model_choice)
    API->>Router: Routes request to upload_pdf()
    
    Note over Router, Orch: Phase 2: Processing
    Router->>Orch: Call summarize_text(file_bytes, model_choice)
    Orch->>Orch: fitz.open() -> Extract Raw Text
    
    Orch->>Loader: get_model_and_tokenizer(model_choice)
    Loader-->>Orch: Returns (model, tokenizer)
    
    Orch->>Utils: chunk_text(raw_text, tokenizer)
    Utils-->>Orch: Returns list[chunks]
    
    Note over Orch, Worker: Phase 3: Map (Summarize Chunks)
    loop For each Chunk
        Orch->>Worker: summarize_{model}(chunk)
        Worker-->>Orch: Yield partial_summary
        Orch-->>Router: Yield "PROGRESS: X/Y"
        Router-->>FE: Stream "PROGRESS: X/Y"
        FE->>FE: Update Progress Bar Width
    end
    
    Note over Orch, Worker: Phase 4: Reduce (Finalize)
    Orch->>Worker: finalize_{model}(combined_summaries)
    Worker-->>Orch: Return final_text
    
    Orch-->>Router: Yield "SUMMARY: final_text"
    Router-->>FE: Stream "SUMMARY: final_text"
    
    Note over FE, User: Phase 5: Display
    FE->>User: Display Text + Enable Download