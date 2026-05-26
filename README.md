# MathTales AI

**Enhancing Small Language Models for Co-Creative Mathematical Storytelling using RAG**

A CPU-deployable co-creative storytelling system where an AI and user collaboratively build mathematical stories for Grade 1–6 learners. The project uses a small open-source LLM (Phi-3-mini, quantized) with an optional RAG pipeline over curated math content to improve narrative coherence and mathematical accuracy.

## Project Objectives

1. **Co-creative storytelling** — AI and user build math stories together; the AI poses problems and waits for the child’s answer.
2. **Small, CPU-friendly model** — Lightweight quantized LLM (e.g. Phi-3-mini-4k-instruct GGUF) runs on CPU.
3. **Long-story coherence** — Investigate and mitigate coherence degradation over 10–20+ turns (e.g. topic drift, entity consistency).
4. **RAG pipeline** — FAISS + lightweight embeddings (BGE-small-en-v1.5) over Grade 1–6 math content (arithmetic, fractions, geometry, ratios, word problems).
5. **Evaluation** — Compare **base small model** vs **RAG-enhanced** small model on narrative coherence and mathematical correctness.

## Tech Stack

- **Backend**: FastAPI, LangChain, LlamaCpp (Phi-3-mini GGUF), FAISS, HuggingFace Embeddings
- **Frontend**: React, Vite, Tailwind, Framer Motion
- **Knowledge**: Structured Markdown in `backend/knowledge/` + optional PDF

## Setup

### Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` in `backend/` if you use any optional env vars (e.g. `GEMINI_API_KEY` is not required for the default local RAG pipeline).

### Build the knowledge base (RAG)

From `backend/`:

```bash
# Ingest curated knowledge (knowledge/*.md) + optional PDF if present
python ingest.py

# Only curated knowledge
python ingest.py --knowledge-only

# Only PDF (e.g. Story-Based_Mathematics_Grades_1-6.pdf)
python ingest.py --pdf-only
```

This creates the `vectorstore/` directory used by the API.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Run

1. Start the backend (from `backend/`):  
   `python main.py` or `uvicorn main:app --host 0.0.0.0 --port 8000`
2. Start the frontend: `npm run dev` (e.g. http://localhost:5173)
3. Open the app and start a story (e.g. “Tell a story about a farmer and apples”).

## API

- **POST /api/chat**  
  - Body: `{ "message": "...", "history": [...], "use_rag": true }`  
  - `use_rag: true` (default) — retrieval-augmented response.  
  - `use_rag: false` — same small LLM without retrieval (for base vs RAG comparison).
- **GET /health** — Returns `llm_ready` and `rag_ready`.

## Evaluation

From `backend/` with the API running:

```bash
python evaluate.py           # Single-turn tests + comparative (base vs RAG)
python evaluate.py --multi-turn   # Plus 20-turn coherence simulation
```

Metrics:

- **Narrative coherence**: topic drift, entity consistency, sentence stats, question/exclamation counts.
- **Mathematical accuracy**: concept coverage, correct answer presence, confusing numbers.
- **Comparative**: RAG vs base (same small LLM) — word count, ROUGE-1 vs prompt, math-term specificity.
- **Human scoring**: flow, consistency, engagement (1–5) — see `backend/human_evaluation/README.md` and use `scores_template.json` to record scores.

Results are written to `evaluation_results.json`.

## Research Questions Addressed

- How does long-form narrative coherence degrade in small language models?
- Can RAG improve mathematical accuracy, concept integration, and logical/narrative consistency?
- What trade-offs exist between model size, retrieval quality, and fluency?

## Expected Outcomes

- A **CPU-deployable** AI storytelling prototype.
- **Quantitative analysis** of long-story coherence in a small model.
- **Demonstration of RAG** as a capability amplifier for small LLMs.
- **Technical report** and live system demo (see evaluation results and this README).

## Example interaction (matches project idea)

1. **User**: "I want a story about a boy named Ali and a fruit shop."
2. **AI**: Begins story (Ali, fruit shop), then e.g. "How many apples are left?" — does not give the answer.
3. **User**: "7 apples"
4. **AI**: "Correct! 10 − 3 = 7 apples. [continues story] How many remain now?"
5. The AI keeps one continuous story, gives feedback + equation when the child answers, then continues and poses the next question. RAG (when enabled) grounds problems in Grade 1–6 content.

## License

See repository or project terms.
