# System Architecture

## 1. High-Level Data Flow

1. **Ingestion (Offline):** Administrator runs `ingestion.py` -> Loads raw text -> Splits into chunks -> Generates embeddings (HuggingFace) -> Stores in ChromaDB.

2. **Query Initiation:** User types a question (Frontend) -> `main.py` (Backend API).

3. **Routing:** `main.py` routes the request to `routes/chat.py`.

4. **Retrieval (RAG Core):**
   * The `rag.py` module receives the question.
   * It converts the question into a vector using the same HuggingFace model.
   * It queries ChromaDB for the top 3 most similar document chunks.

5. **Synthesis (Generation):**
   * The retrieved chunks + the user's question are packed into a prompt template.
   * This prompt is sent to the local **Ollama (Mistral)** instance.

6. **Response:** Mistral generates a natural language answer based *only* on the provided chunks, which is sent back to the Frontend as JSON.

## 2. Key Design Decisions

### Local-First Architecture

I prioritized privacy and zero-cost operation by running the entire stack locally.

* **Inference:** Uses **Ollama** to run quantized LLMs (like Mistral) efficiently on consumer hardware (GPU accelerated).
* **Embeddings:** Uses `sentence-transformers/all-MiniLM-L6-v2` via HuggingFace, running locally on the GPU.
* **Storage:** Uses **ChromaDB** in persistent mode, saving data to a local `vector_db/` folder rather than a cloud vector store.

### LangChain Expression Language (LCEL)

I decided to use modern **LCEL** pipelines for transparency instead of legacy `RetrievalQA` chains pipeline.

* **Pattern:** `Retriever | Formatter | Prompt | LLM | OutputParser`
* **Benefit:** This allows one to inspect the data flow at any stage and easily swap out components (e.g., changing the prompt template) without breaking the logic.

### Service-Based Folder Structure

I preferred to use a "Service Layout" to separate concerns while keeping execution simple.

* **`src/`**: Contains the core business logic (RAG, Ingestion).
* **`routes/`**: Handles HTTP transport and validation (Pydantic).
* **`frontend/`**: Contains the presentation layer.
* **`main.py`**: Acts as the entry point, tying the routes and static files together.

# Process Chart

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as Frontend (app.js)
    participant API as Backend API (main.py)
    participant Router as Router (routes/chat.py)
    participant Logic as RAG Logic (src/rag.py)
    participant DB as ChromaDB (Vector Store)
    participant LLM as Ollama (Mistral)

    Note over User, FE: Phase 1: User Interaction
    User->>FE: Types Question + Clicks Send
    FE->>API: POST /api/ask (JSON: {question})
    API->>Router: Routes request to ask_question()
    
    Note over Router, Logic: Phase 2: Retrieval & Synthesis
    Router->>Logic: Call query_rag(question)
    Logic->>Logic: Convert Question to Vector
    
    Logic->>DB: Similarity Search (Top 3 Chunks)
    DB-->>Logic: Returns [Chunk A, Chunk B, Chunk C]
    
    Logic->>Logic: Format Prompt (Context + Question)
    
    Logic->>LLM: Send Prompt
    LLM-->>Logic: Return Generated Answer
    
    Note over Logic, User: Phase 3: Response
    Logic-->>Router: Return Answer String
    Router-->>API: Return JSON {answer: "..."}
    API-->>FE: HTTP 200 OK
    FE->>User: Display Answer Bubble