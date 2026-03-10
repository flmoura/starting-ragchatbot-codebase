# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Always use `uv` to run Python — never invoke `pip` or `python` directly.

```bash
# Install dependencies (from project root)
uv sync

# Run the application
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

The app runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

Requires a `.env` file in the project root:
```
ANTHROPIC_API_KEY=your_key_here
```

## Architecture

This is a RAG chatbot with a FastAPI backend and vanilla JS frontend. All backend code runs from the `backend/` directory — imports are relative to it (e.g., `from config import config`).

### Query pipeline

1. `frontend/script.js` — POSTs `{ query, session_id }` to `/api/query`
2. `backend/app.py` — creates a session if needed, calls `RAGSystem.query()`
3. `backend/rag_system.py` — fetches conversation history, calls `AIGenerator.generate_response()` with the `search_course_content` tool attached
4. `backend/ai_generator.py` — calls Claude; if `stop_reason == "tool_use"`, executes the tool and makes a second Claude call with the results
5. `backend/search_tools.py` — `CourseSearchTool` performs the vector search and formats chunks for Claude
6. `backend/vector_store.py` — queries ChromaDB using `SentenceTransformer` embeddings; resolves partial course names via semantic search on the `course_catalog` collection before filtering `course_content`

### ChromaDB collections

Two persistent collections (stored at `./chroma_db`):
- `course_catalog` — one document per course (title, instructor, lesson metadata as JSON); used for fuzzy course-name resolution
- `course_content` — chunked text with metadata `{ course_title, lesson_number, chunk_index }`; used for semantic search

Course title is used as the ChromaDB document ID in `course_catalog`, so it must be unique.

### Document ingestion

`document_processor.py` parses `.txt`/`.pdf`/`.docx` files from `docs/` at startup into `Course` + `List[CourseChunk]` objects (800-char chunks, 100-char overlap). Already-loaded courses are skipped by title to avoid duplicates.

### Key configuration (`backend/config.py`)

| Setting | Default |
|---|---|
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` |
| `CHUNK_SIZE` | 800 |
| `CHUNK_OVERLAP` | 100 |
| `MAX_RESULTS` | 5 |
| `MAX_HISTORY` | 2 (conversation exchanges) |

### Adding a new tool

1. Subclass `Tool` in `backend/search_tools.py`, implement `get_tool_definition()` and `execute()`
2. Register with `tool_manager.register_tool(your_tool)` in `RAGSystem.__init__()`

Claude will automatically receive the tool definition and can invoke it during query handling.
