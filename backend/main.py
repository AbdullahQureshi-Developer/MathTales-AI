from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import List, Dict, Optional, Tuple
import re
from huggingface_hub import hf_hub_download
from langchain_community.llms import LlamaCpp
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
import pickle

class CustomEnsembleRetriever:
    def __init__(self, retrievers, weights):
        self.retrievers = retrievers
        self.weights = weights
        
    def invoke(self, query):
        all_docs = {}
        for r, w in zip(self.retrievers, self.weights):
            docs = r.invoke(query)
            for i, doc in enumerate(docs):
                if doc.page_content not in all_docs:
                    all_docs[doc.page_content] = {"doc": doc, "score": 0}
                all_docs[doc.page_content]["score"] += w * (1.0 / (i + 60))
        sorted_docs = sorted(all_docs.values(), key=lambda x: x["score"], reverse=True)
        return [item["doc"] for item in sorted_docs][:5]


# OPTIONAL (better results)
from sentence_transformers import CrossEncoder

load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MathTales AI - Clean RAG")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# LOAD MODELS
# =========================

print("Loading embedding model...")
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)

print("Loading vector store...")
vectorstore = FAISS.load_local(
    "vectorstore",
    embeddings,
    allow_dangerous_deserialization=True
)
faiss_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

print("Loading BM25 index...")
try:
    with open("vectorstore_bm25.pkl", "rb") as f:
        bm25_retriever = pickle.load(f)
    bm25_retriever.k = 3
    retriever = CustomEnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever], weights=[0.5, 0.5]
    )
    print("CustomEnsembleRetriever (Hybrid RAG) loaded successfully.")
except FileNotFoundError:
    print("BM25 index not found. Using FAISS only.")
    retriever = faiss_retriever

model_path = hf_hub_download(
    repo_id="microsoft/Phi-3-mini-4k-instruct-gguf",
    filename="Phi-3-mini-4k-instruct-q4.gguf"
)

print("Loading LLM...")
llm = LlamaCpp(
    model_path=model_path,
    temperature=0.2,        # better math accuracy
    max_tokens=400,
    top_p=0.9,
    n_ctx=4096,
    repeat_penalty=1.2,
    n_threads=8,           # 🔥 use your CPU cores
    n_batch=256,           # 🔥 improves speed
    stop=["<|end|>", "<|user|>"]
)

# OPTIONAL: RERANKER
print("Loading reranker...")
reranker = CrossEncoder("BAAI/bge-reranker-base")


# =========================
# REQUEST / RESPONSE
# =========================

class ChatRequest(BaseModel):
    session_id: str = "default"
    message: str
    history: List[Dict] = []
    use_rag: bool = True

class SessionState(BaseModel):
    characters: str = ""
    setting: str = ""
    math_used: str = ""
    summary: str = ""

active_sessions: Dict[str, SessionState] = {}


class StoryElements(BaseModel):
    characters: str = ""
    setting: str = ""


class ChatResponse(BaseModel):
    response: str
    context_used: List[str]
    turn_number: int = 0
    story_elements: Optional[StoryElements] = None
    correct_answer: Optional[int] = None

# =========================
# RAG FUNCTIONS
# =========================

def retrieve_docs(query: str):
    # 🔥 IMPORTANT: BGE prefix
    query = "Represent this sentence for searching relevant passages: " + query

    docs = retriever.invoke(query)
    return docs


def rerank_docs(query: str, docs):
    pairs = [[query, d.page_content] for d in docs]
    scores = reranker.predict(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:3]]


def build_context(docs):
    return "\n\n".join([doc.page_content for doc in docs])


# =========================
# PROMPT
# =========================

def build_prompt(context: str, question: str, history: str = "", mode: str = "story", state: SessionState = None):
    """
    Build a clean prompt specifically tailored to the current conversational mode.
    """
    state_text = ""
    if state and (state.characters or state.setting):
        state_text = f"\nNotebook:\n- Characters: {state.characters}\n- Setting: {state.setting}\n- Math Used: {state.math_used[-100:]}\n"

    if mode == "story":
        prompt = f"""<|user|>
You are the Great Sage of MathTales, a wise and friendly math teacher having a 1-on-1 conversation with your student. 

Context:
{context}
{state_text}
Our conversation history:
{history}

The student's new topic request or input is: "{question}"

CRITICAL RULES FOR YOUR RESPONSE:
1. HUMAN-TO-HUMAN CONVERSATION: Speak warmly and conversationally directly to the student. 
2. ANSWER QUESTIONS FIRST: If the student asks a question, answer it nicely before giving the problem.
3. CHANGE TOPIC IF REQUESTED: If the student wants a new topic or characters, you MUST abandon the old ones and use the new ones.
4. MATH WORD PROBLEM: After conversing, present a short math word problem based on the topic.
5. KEEP THE MATH SIMPLE: A short setup, an action, and a final question (e.g., "Alice had 3 apples and her friend gave her 2 more. How many apples does Alice have now?").
6. NO SPOILERS: ONLY pose the question. Do NOT include the solution, hints, or tell them the answer.<|end|>
<|assistant|>
"""
    elif mode == "evaluate":
        prompt = f"""<|user|>
You are the Great Sage of MathTales, a friendly and conversational AI math teacher having a 1-on-1 conversation with your student.

The student has responded: "{question}"

History for context:
{history}

CRITICAL RULES FOR YOUR RESPONSE:
1. CONVERSATIONAL EVALUATION: Naturally and warmly evaluate their answer based on the history. 
2. ANSWER QUESTIONS: If the student asked a question, answer it clearly and helpfully.
3. BE ENCOURAGING: Acknowledge their effort. If they are wrong or don't know, gently explain the answer step-by-step.
4. ENGAGE FOR NEXT TOPIC: Finish by asking if they are ready for a new math problem and what topic they would like!
5. DO NOT GENERATE A NEW MATH PROBLEM YET: Wait for them to choose a topic.<|end|>
<|assistant|>
"""
    else:
        prompt = f"""<|user|>
You are the Great Sage of MathTales. Chat warmly and friendly with the student.
Student says: {question}<|end|>
<|assistant|>
"""
    return prompt


# =========================
# HISTORY (optimized for long narrative coherence)
# =========================

def build_history(history: List[Dict], max_turns=20):
    if not history:
        return ""

    recent = history[-max_turns:]
    text = ""

    for msg in recent:
        role = msg.get("role")
        content = msg.get("content", "")

        if role == "user":
            text += f"Student: {content}\n"
        elif role == "assistant":
            text += f"Teacher: {content}\n"

    return text


def extract_story_elements(text: str) -> StoryElements:
    """Lightweight parse of a word problem for sidebar display."""
    characters = ""
    setting = ""
    names = []
    for m in re.finditer(
        r"\b([A-Z][a-z]+)\s+(?:had|has|have|was|were|got|gave|found|bought|picked|ate|left|made|sold|shared)\b",
        text,
    ):
        if m.group(1) not in names:
            names.append(m.group(1))
    if names:
        characters = ", ".join(names[:4])
    place = re.search(
        r"\b(?:at|in|inside|near|outside)\s+(?:the\s+)?([A-Za-z][A-Za-z\s]{2,48}?)(?=[\.,\?]|\.{3}|$)",
        text,
        re.IGNORECASE,
    )
    if place:
        setting = place.group(1).strip()
    return StoryElements(characters=characters, setting=setting)


def refine_story_response(raw: str) -> str:
    """Keep the response through the final math question (to avoid spoilers), but preserve conversational text."""
    s = raw.strip()
    start = re.search(r"[A-Za-z0-9]", s)
    if start:
        s = s[start.start() :]
        
    # Prefer truncating at a math-style final question when there are several "?".
    math_q = None
    for m in re.finditer(
        r"(?is).*\b(how many|how much|how long|how many more|what is|how many are|can you calculate)\b[^?]*\?",
        s,
    ):
        math_q = m
    if math_q:
        s = s[: math_q.end()]
    else:
        q = s.rfind("?")
        if q != -1:
            s = s[: q + 1]
    return s.strip()

# =====================================================
# FIX 1: PYTHON HYBRID MATH CORRECTOR
# =====================================================

OPERATION_FUNCS = {
    "divide": lambda a, b: a // b if b != 0 else 0,
    "multiply": lambda a, b: a * b,
    "subtract": lambda a, b: abs(a - b),
    "add": lambda a, b: a + b,
}


def detect_operation_from_prompt(prompt: str) -> str:
    p = prompt.lower()
    if any(w in p for w in ["share", "equally", "groups of", "divide", "split"]):
        return "divide"
    if any(w in p for w in ["rows", "each", "multiply", "times", "plants"]):
        return "multiply"
    if any(w in p for w in ["loses", "lost", "remain", "minus", "subtract"]):
        return "subtract"
    if any(w in p for w in ["more", "total", "finds", "add", "together"]):
        return "add"
    return "unknown"


def inject_operands(response: str, prompt: str) -> str:
    """
    If the LLM dropped the original numbers from the story,
    inject them back so the problem stays solvable.
    """
    numbers_in_prompt = [int(n) for n in re.findall(r"\b\d+\b", prompt)]
    numbers_in_response = {int(n) for n in re.findall(r"\b\d+\b", response)}

    missing = [n for n in numbers_in_prompt if n not in numbers_in_response]
    if not missing:
        return response  # nothing to fix

    # Build a tiny prefix that restores missing numbers naturally
    prefix = (
        f"(The numbers in this problem are {' and '.join(str(n) for n in missing)}.) "
    )
    return prefix + response


def apply_math_corrector(prompt: str, response: str, mode: str) -> tuple:
    """
    1. Ensures operands are present in the story (inject if missing).
    2. Computes the correct answer with Python.
    3. Returns (corrected_response, correct_answer_int_or_None).

    The answer is NOT injected into the story (anti-spoiler rule stays).
    It is returned as metadata so the /api/chat response can carry it.
    """
    if mode != "story":
        return response, None

    numbers = [int(n) for n in re.findall(r"\b\d+\b", prompt)]
    if len(numbers) < 2:
        return response, None

    operation = detect_operation_from_prompt(prompt)
    if operation == "unknown":
        return inject_operands(response, prompt), None

    try:
        a, b = numbers[0], numbers[1]
        correct_answer = OPERATION_FUNCS[operation](a, b)
        corrected = inject_operands(response, prompt)
        return corrected, int(correct_answer)
    except Exception:
        return inject_operands(response, prompt), None


# =========================
# GENERATE ANSWER WITH HARD OUTPUT CONTROL
# =========================

def generate_answer(message, history, session_id="default", use_rag=True) -> Tuple[str, List[str], str]:
    msg_clean = message.lower().strip()

    # Catch basic greetings instantly without wasting LLM compute
    if re.fullmatch(r"(hello|hi|hey|greetings|howdy|yo)\s*[!\.?]*", msg_clean):
        return (
            "Hello! I am the Great Sage of MathTales. Are you ready for a math story? What topic would you like to explore today? 🌟",
            [],
            "story",
        )

    # STATE MACHINE: Determine if user is answering a problem or requesting a new story
    mode = "story"
    if history:
        last_msg = history[-1]
        if last_msg.get("role") == "assistant":
            last_text = last_msg.get("content", "").lower()
            # If the bot asked for a topic / concept (including UI welcome copy), next message is story mode.
            topic_request_markers = (
                "what topic",
                "what math concept",
                "what concept",
                "what would you like",
                "what do you like",
                "learn today",
                "explore today",
                "explore through",
                "new story",
                "another story",
                "ready for a math story",
            )
            if any(m in last_text for m in topic_request_markers):
                mode = "story"
            # Otherwise, if the bot ended with a question (typical math word problem), user is answering it.
            elif "?" in last_text:
                mode = "evaluate"

    # Only use RAG for creating a new story based on a topic.
    # Searching RAG for user answers like "17" or "I don't know" will introduce garbage context!
    if use_rag and mode == "story":
        docs = retrieve_docs(message)

        # Optional reranking
        docs = rerank_docs(message, docs)

        # CLEAN CONTEXT: remove instruction-like lines
        def clean_context(text):
            pats = [
                r"Use one of.*",
                r"Problem \d+.*",
                r"Exercise.*",
                r"Answer:.*",
                r"Solution:.*",
                r"Teacher:.*",
                r"Response:.*",
                r"^#{1,6}\s+.+$",
                r"^\s*[-*]{3,}\s*$",
            ]
            for p in pats:
                text = re.sub(p, "", text, flags=re.IGNORECASE | re.MULTILINE)
            return text.strip()

        context = "\n\n".join([clean_context(doc.page_content) for doc in docs])
        sources = [doc.page_content[:80] for doc in docs]
    else:
        context = "Basic math knowledge"
        sources = []

    history_text = build_history(history)
    state = active_sessions.get(session_id, SessionState())
    prompt = build_prompt(context, message, history_text, mode=mode, state=state)

    # DEBUG
    print("\n===== DEBUG =====")
    print("USER:", message)
    print("CONTEXT:", context[:500])
    print("PROMPT:", prompt[:500])

    # Invoke LLM
    response = llm.invoke(prompt)

    # Clean the output from Phi-3 formatting artifacts
    response = response.replace("<|end|>", "").replace("<|assistant|>", "").strip()

    if mode == "story":
        labels_to_remove = [
            "Story:",
            "Question:",
            "Teacher:",
            "Response:",
            "Problem:",
            "Answer:",
            "Here is",
        ]
        for bad_word in labels_to_remove:
            if bad_word.lower() in response.lower():
                response = response.replace(bad_word, "")
        response = refine_story_response(response)

    response = response.strip()

    if mode == "story" and response and "?" not in response:
        response = response.rstrip(" .!") + "?"

    return response, sources, mode


# =========================
# API
# =========================

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        if req.session_id not in active_sessions:
            active_sessions[req.session_id] = SessionState()

        response, sources, mode = generate_answer(
            req.message,
            req.history,
            req.session_id,
            req.use_rag,
        )
        # Apply hybrid corrector (Fix 1)
        response, correct_answer = apply_math_corrector(req.message, response, mode)

        user_turns = sum(1 for m in req.history if m.get("role") == "user") + 1
        turn_number = user_turns

        if len(response) < 10:
            if mode == "story":
                response = (
                    "Tell me a math topic (for example: fractions, animals, or shopping) "
                    "and I'll make a short story problem!"
                )
            else:
                response = (
                    "Thanks for sharing! When you're ready, tell me what topic you'd like for the next problem."
                )

        if mode == "evaluate" and "?" not in response:
            response = response.rstrip() + " What topic would you like for your next problem?"

        story_payload: Optional[StoryElements] = None
        if mode == "story" and len(response) >= 10:
            se = extract_story_elements(response)
            if se.characters or se.setting:
                story_payload = se
                active_sessions[req.session_id].characters = se.characters
                if se.setting:
                    active_sessions[req.session_id].setting = se.setting
            active_sessions[req.session_id].math_used += f"{req.message}, "

        return ChatResponse(
            response=response,
            context_used=sources,
            turn_number=turn_number,
            story_elements=story_payload,
            correct_answer=correct_answer,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# RUN
# =========================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
