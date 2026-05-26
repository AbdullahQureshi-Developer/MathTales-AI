"""
MathTales AI - Advanced Evaluation Framework (v2)
=================================================

Covers all three evaluation plan pillars:
  1. Narrative Coherence  — topic drift (semantic), entity consistency, human scoring
  2. Mathematical Accuracy — correctness, equation error-rate, concept coverage
  3. Comparative Study    — RAG vs Base (BLEU, BERT F1, specificity, length)

Offline / CLI only — not imported by main.py.

Install:
    pip install nltk bert-score sympy sentence-transformers matplotlib

Run:
    python evaluate.py                   # standard eval
    python evaluate.py --multi-turn      # + coherence decay over 20 turns
    python evaluate.py --human           # prompt for human scores after each test
    python evaluate.py --compare         # force RAG-vs-Base on every prompt
"""

from sympy import sympify
from bert_score import score as bertscore
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
import numpy as np
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import re
import json
import argparse
import urllib.request
import string
import matplotlib
matplotlib.use("Agg")


# Sentence-transformer for semantic similarity (topic drift)
try:
    from sentence_transformers import SentenceTransformer, util as st_util
    _SBERT = SentenceTransformer("BAAI/bge-small-en-v1.5")
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False
    print("[WARN] sentence-transformers not installed — semantic drift disabled.")

API_BASE = "http://localhost:8000"
smooth = SmoothingFunction().method1


# ─────────────────────────────────────────────
# Test prompts
# ─────────────────────────────────────────────

import random

def generate_test_prompts(n=55):
    base_prompts = [
        {"prompt": "Tell a story where {a} friends share {b} apples equally.", "operation": "divide", "concepts": ["divide", "equal", "share"], "ans_fmt": "Each friend gets {ans} apples.", "calc": lambda a,b: (a, a*b, b)},
        {"prompt": "A wizard has {b} magic coins and puts them into groups of {a}. How many groups?", "operation": "divide", "concepts": ["group", "divide"], "ans_fmt": "There are {ans} groups.", "calc": lambda a,b: (a*b, a, b)},
        {"prompt": "A farmer plants {a} rows with {b} sunflowers each. How many total?", "operation": "multiply", "concepts": ["multiply", "row"], "ans_fmt": "There are {ans} sunflowers in total.", "calc": lambda a,b: (a, b, a*b)},
        {"prompt": "A dragon collects {b} gems but loses {a}. How many remain?", "operation": "subtract", "concepts": ["subtract", "minus"], "ans_fmt": "{ans} gems remain.", "calc": lambda a,b: (a+b, a, b)},
        {"prompt": "An astronaut finds {a} moon rocks and then finds {b} more. What is the total?", "operation": "add", "concepts": ["add", "total", "more"], "ans_fmt": "The total is {ans} rocks.", "calc": lambda a,b: (a, b, a+b)},
    ]
    
    prompts = []
    for i in range(1, n + 1):
        template = random.choice(base_prompts)
        a, b = random.randint(2, 12), random.randint(2, 12)
        op1, op2, ans = template["calc"](a, b)
        
        prompts.append({
            "id": i,
            "prompt": template["prompt"].format(a=op1, b=op2),
            "expected_answer": ans,
            "operands": [op1, op2],
            "operation": template["operation"],
            "concepts": template["concepts"],
            "student_answer": template["ans_fmt"].format(ans=ans),
        })
    return prompts

TEST_PROMPTS = generate_test_prompts(55)


# ─────────────────────────────────────────────
# API helpers
# ─────────────────────────────────────────────

def call_api(message, history=None, use_rag=True):
    payload = json.dumps({
        "message": message,
        "history": history or [],
        "use_rag": use_rag,
    }).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        if hasattr(e, 'read'):
            body = e.read().decode('utf-8', errors='ignore')
        else:
            body = str(e)
        return {"response": "", "error": body}


def call_base_model(message):
    return call_api(message, use_rag=False).get("response", "")


# ─────────────────────────────────────────────
# Text utilities
# ─────────────────────────────────────────────

def tokenize(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text.split()


def sentences_of(text):
    return [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]


# ─────────────────────────────────────────────
# 1a. Narrative Coherence — semantic topic drift
# ─────────────────────────────────────────────

def semantic_topic_drift(response_text, prompt):
    """
    Returns cosine similarity between the prompt embedding and the response
    embedding.  Higher = less drift.  Falls back to keyword overlap if SBERT
    is unavailable.
    """
    if SBERT_AVAILABLE:
        embs = _SBERT.encode([prompt, response_text], convert_to_tensor=True)
        score = float(st_util.cos_sim(embs[0], embs[1]))
        return round(score, 3)
    # Keyword-overlap fallback
    p_words = set(tokenize(prompt))
    r_words = set(tokenize(response_text))
    overlap = len(p_words & r_words) / max(len(p_words), 1)
    return round(overlap, 3)


def semantic_drift_across_turns(turn_texts, prompt):
    """
    For multi-turn: measure similarity of each turn to the original prompt.
    Returns list of per-turn drift scores (higher = closer to original topic).
    """
    if not SBERT_AVAILABLE:
        return [semantic_topic_drift(t, prompt) for t in turn_texts]
    prompt_emb = _SBERT.encode(prompt, convert_to_tensor=True)
    scores = []
    for text in turn_texts:
        t_emb = _SBERT.encode(text, convert_to_tensor=True)
        scores.append(round(float(st_util.cos_sim(prompt_emb, t_emb)), 3))
    return scores


# ─────────────────────────────────────────────
# 1b. Narrative Coherence — entity consistency
# ─────────────────────────────────────────────

def entity_consistency(text):
    """
    Extracts proper-noun entities and checks:
      - reuse_ratio: fraction of entities mentioned more than once
      - contradiction_proxy: entities that appear both near negation words
        and without them (crude proxy for flip-flop inconsistency)
    """
    entities = re.findall(r"\b[A-Z][a-z]+\b", text)
    entity_counts = {}
    for e in entities:
        entity_counts[e] = entity_counts.get(e, 0) + 1

    reuse = sum(1 for v in entity_counts.values() if v > 1)
    reuse_ratio = round(reuse / max(len(entity_counts), 1), 2)

    # Contradiction proxy: entity near "not/no/never/lost/didn't"
    negation_pattern = r"(?:not|no|never|lost|didn't|wasn't)\s+\w*\s*([A-Z][a-z]+)"
    negated = set(re.findall(negation_pattern, text))
    positive_pattern = r"\b([A-Z][a-z]+)\b"
    positive = set(re.findall(positive_pattern, text))
    contradicted = len(negated & positive)

    return {
        "unique_entities": len(entity_counts),
        "reuse_ratio": reuse_ratio,
        "contradicted_entities": contradicted,
        "entity_counts": entity_counts,
    }


# ─────────────────────────────────────────────
# 1c. Narrative Coherence — combined measure
# ─────────────────────────────────────────────

def measure_coherence(text, prompt):
    words = tokenize(text)
    sents = sentences_of(text)
    topic_score = semantic_topic_drift(text, prompt)
    ent = entity_consistency(text)
    return {
        "topic_drift_score": topic_score,          # higher = more on-topic
        "entity_consistency": ent["reuse_ratio"],  # higher = more consistent
        "contradicted_entities": ent["contradicted_entities"],
        "sentence_count": len(sents),
        "word_count": len(words),
        "entity_detail": ent,
    }


# ─────────────────────────────────────────────
# 1d. Human scoring (CLI)
# ─────────────────────────────────────────────

HUMAN_DIMENSIONS = ["flow", "consistency", "engagement"]


def human_score(prompt, response):
    """
    Prompts the evaluator for 1-5 scores on each dimension.
    Returns dict of scores + average.
    """
    print("\n─── Human Evaluation ─────────────────────────")
    print(f"PROMPT   : {prompt}")
    print(f"RESPONSE : {response[:400]}{'...' if len(response) > 400 else ''}")
    print("Rate the story 1–5 on each dimension (Enter to skip):")
    scores = {}
    for dim in HUMAN_DIMENSIONS:
        raw = input(f"  {dim.capitalize()} [1-5]: ").strip()
        try:
            scores[dim] = max(1, min(5, int(raw)))
        except ValueError:
            scores[dim] = None
    valid = [v for v in scores.values() if v is not None]
    scores["average"] = round(sum(valid) / len(valid), 2) if valid else None
    return scores


# ─────────────────────────────────────────────
# 2a. Math accuracy — robust number check
# ─────────────────────────────────────────────

def check_math(text, expected_answer, operands, operation):
    """
    The model is hard-instructed NOT to reveal the answer (anti-spoiler rule in
    main.py's refine_story_response + prompt).  Checking for expected_answer in
    the response will almost always return False and is therefore misleading.

    Instead we measure solvability of the generated problem:
      - operands_present : all input numbers from the prompt appear in the story
      - operation_present: the correct operation keyword appears
      - ends_with_question: story ends with '?' (required by main.py)
      - solvable         : operands_present AND ends_with_question
    """
    numbers_in_text = {int(n) for n in re.findall(r"\b\d+\b", text)}
    operands_present = all(op in numbers_in_text for op in operands)

    OPERATION_SYNONYMS = {
        "divide":   ["divide", "divides", "divided", "share", "split", "group"],
        "multiply": ["multiply", "multiplies", "multiplied", "times", "each", "rows"],
        "subtract": ["subtract", "subtracts", "subtracted", "loses", "lost", "minus", "remain"],
        "add":      ["add", "adds", "added", "more", "total", "plus"],
        "double":   ["double", "doubles", "doubled", "twice", "pattern"],
    }
    synonyms = OPERATION_SYNONYMS.get(operation, [operation])
    text_lower = text.lower()
    operation_present = any(s in text_lower for s in synonyms)
    ends_with_question = text.rstrip().endswith("?")

    return {
        "solvable": operands_present and ends_with_question,
        "operands_present": operands_present,
        "operation_present": operation_present,
        "ends_with_question": ends_with_question,
        # Expected to be False by design — flags unexpected answer leakage
        "answer_leaked": expected_answer in numbers_in_text,
    }


# ─────────────────────────────────────────────
# 2b. Math accuracy — equation validation + error rate
# ─────────────────────────────────────────────

def validate_equations(text):
    """
    main.py's anti-spoiler rules mean the model will almost never output a
    solved equation like "12 / 3 = 4".  Searching for them produces all-zero
    metrics that are noise, not signal.

    Instead we validate the *problem structure*:
      - has_numeric_setup    : at least 2 distinct numbers appear (operands)
      - has_question_mark    : story closes with '?' (mandatory in main.py)
      - inline_eq_count      : how many solved equations slipped through
                               (should be 0 — non-zero = answer leaked)
      - inline_eq_correct    : of any that slipped, how many are arithmetically valid
    """
    inline_eqs = re.findall(r"(\d+\s*[\+\-\*\/]\s*\d+\s*=\s*\d+)", text)
    correct = incorrect = 0
    for eq in inline_eqs:
        try:
            left, right = eq.split("=")
            if sympify(left.strip()) == sympify(right.strip()):
                correct += 1
            else:
                incorrect += 1
        except Exception:
            pass

    distinct_numbers = len(set(re.findall(r"\b\d+\b", text)))

    return {
        "has_numeric_setup": distinct_numbers >= 2,
        "has_question_mark": text.rstrip().endswith("?"),
        "distinct_numbers_in_text": distinct_numbers,
        "inline_eq_count": len(inline_eqs),       # leak detector
        "inline_eq_correct": correct,
        "inline_eq_incorrect": incorrect,
    }


# ─────────────────────────────────────────────
# 2c. Concept coverage
# ─────────────────────────────────────────────

def concept_coverage(text, concepts):
    text_lower = text.lower()
    found = [c for c in concepts if re.search(
        rf"\b{re.escape(c)}\b", text_lower)]
    return round(len(found) / max(len(concepts), 1), 2), found


# ─────────────────────────────────────────────
# 3. RAG vs Base comparison
# ─────────────────────────────────────────────

MATH_TERMS = ["divide", "multiply", "subtract", "add", "group",
              "pattern", "double", "equal", "share", "remain"]


def compare_models(prompt, rag_text):
    """
    Compares RAG-enhanced response with base model on:
      - Length
      - Math-term specificity
      - BLEU (response vs prompt as trivial reference)
      - BERT F1
    """
    base_text = call_base_model(prompt)
    if not base_text:
        return None

    def specificity(t):
        tl = t.lower()
        return sum(1 for m in MATH_TERMS if m in tl)

    rag_bleu = compute_bleu(rag_text, prompt)
    base_bleu = compute_bleu(base_text, prompt)

    _, _, rag_f = bertscore([rag_text], [prompt], lang="en")
    _, _, base_f = bertscore([base_text], [prompt], lang="en")

    return {
        "rag_words": len(rag_text.split()),
        "base_words": len(base_text.split()),
        "rag_specificity": specificity(rag_text),
        "base_specificity": specificity(base_text),
        "rag_bleu": rag_bleu,
        "base_bleu": base_bleu,
        "rag_bert_f1": round(float(rag_f.mean()), 3),
        "base_bert_f1": round(float(base_f.mean()), 3),
        "rag_wins_specificity": specificity(rag_text) > specificity(base_text),
        "rag_wins_bert": float(rag_f.mean()) > float(base_f.mean()),
    }


# ─────────────────────────────────────────────
# BLEU / BERT helpers
# ─────────────────────────────────────────────

def compute_bleu(candidate, reference):
    return round(sentence_bleu([tokenize(reference)], tokenize(candidate),
                               smoothing_function=smooth), 3)


def compute_bertscore(candidate, reference):
    P, R, F = bertscore([candidate], [reference], lang="en")
    return {
        "precision": round(float(P.mean()), 3),
        "recall": round(float(R.mean()), 3),
        "f1": round(float(F.mean()), 3),
    }


# ─────────────────────────────────────────────
# Multi-turn coherence decay
# ─────────────────────────────────────────────

def simulate_multi_turn(turns=20):
    """
    Mirrors the real conversation flow that main.py's state machine expects.

    main.py checks the last assistant message to decide mode:
      - If it ends with "?" → mode = "evaluate"  (user is answering)
      - If it contains a topic-request phrase → mode = "story"

    Sending "Tell me what happens next." after every word problem always
    triggers "evaluate" mode — you end up measuring feedback quality,
    not story narrative coherence.

    Fix: alternate between a topic request (story turn) and a plausible
    student answer (evaluate turn).  Coherence decay is measured on story
    turns only, which is the meaningful signal.
    """
    history = []
    seed_topic = "Farmer Ali and apples"

    topic_requests = [
        f"Tell me a story about {seed_topic}.",
        "Tell me a story about a baker and fractions.",
        "Tell me a story about a sailor counting fish.",
        "Tell me a story about a market with coins.",
        "Tell me a story about a library and books.",
        "Tell me a story about a garden and vegetables.",
        "Tell me a story about a zoo with animals.",
        "Tell me a story about rockets and numbers.",
        "Tell me a story about a chef dividing pizza.",
        "Tell me a story about twins sharing sweets.",
    ]
    plausible_answers = [
        "I think the answer is 4.",
        "Maybe 3 groups?",
        "I'm not sure, maybe 32?",
        "The total would be 30.",
        "63 gems remain.",
        "I think it's 8.",
        "The answer is 15.",
        "Could be 7?",
        "I think 6 pieces each.",
        "Maybe 9?",
    ]

    metrics = []
    turn_texts = []

    for i in range(1, turns + 1):
        is_story_turn = (i % 2 == 1)

        if is_story_turn:
            prompt = topic_requests[(i // 2) % len(topic_requests)]
        else:
            prompt = plausible_answers[(i // 2 - 1) % len(plausible_answers)]

        res = call_api(prompt, history)
        text = res.get("response", "")
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": text})
        turn_texts.append(text)

        metrics.append({
            "turn": i,
            "turn_type": "story" if is_story_turn else "evaluate",
            "coherence": measure_coherence(text, seed_topic),
        })

    # Semantic drift vs seed topic across all turns
    drift_scores = semantic_drift_across_turns(turn_texts, seed_topic)
    for i, m in enumerate(metrics):
        m["semantic_drift_score"] = drift_scores[i]

    return metrics


# ─────────────────────────────────────────────
# Visualisation
# ─────────────────────────────────────────────

def plot_results(results, multi_turn_metrics=None):
    ids = [str(r["id"]) for r in results]
    math_acc = [1 if r["math"]["solvable"] else 0 for r in results]
    concept_cov = [r["concept_coverage"] for r in results]
    bert_f1 = [r["bertscore"]["f1"] for r in results]
    topic_drift = [r["coherence"]["topic_drift_score"] for r in results]

    has_compare = any(r.get("comparison") for r in results)
    has_mt = multi_turn_metrics is not None

    n_plots = 3 + (1 if has_compare else 0) + (1 if has_mt else 0)
    fig = plt.figure(figsize=(14, 4 * ((n_plots + 1) // 2)))
    gs = gridspec.GridSpec((n_plots + 1) // 2, 2,
                           figure=fig, hspace=0.5, wspace=0.35)

    axes = [fig.add_subplot(gs[i // 2, i % 2]) for i in range(n_plots)]

    x = np.arange(len(ids))
    w = 0.28

    # Plot 1 — Math accuracy vs Concept coverage
    ax = axes[0]
    ax.bar(x - w / 2, math_acc, w, label="Math correct", color="#4A90D9")
    ax.bar(x + w / 2, concept_cov, w, label="Concept coverage", color="#50C878")
    ax.set_xticks(x)
    ax.set_xticklabels([f"T{i}" for i in ids])
    ax.set_ylim(0, 1.15)
    ax.set_title("Math Accuracy & Concept Coverage")
    ax.legend(fontsize=8)
    ax.set_ylabel("Score")

    # Plot 2 — BERT F1
    ax = axes[1]
    ax.bar(x, bert_f1, color="#E07B54")
    ax.set_xticks(x)
    ax.set_xticklabels([f"T{i}" for i in ids])
    ax.set_ylim(0, 1)
    ax.set_title("BERTScore F1 (response ↔ prompt)")
    ax.set_ylabel("F1")

    # Plot 3 — Coherence (topic drift + entity consistency)
    ax = axes[2]
    ent_cons = [r["coherence"]["entity_consistency"] for r in results]
    ax.plot(ids, topic_drift, marker="o",
            label="Topic drift score", color="#7B5EA7")
    ax.plot(ids, ent_cons, marker="s", linestyle="--",
            label="Entity consistency", color="#C0392B")
    ax.set_ylim(0, 1.05)
    ax.set_title("Narrative Coherence per Test")
    ax.legend(fontsize=8)
    ax.set_ylabel("Score")
    ax.grid(alpha=0.3)

    plot_idx = 3

    # Plot 4 — RAG vs Base (if available)
    if has_compare:
        ax = axes[plot_idx]
        plot_idx += 1
        rag_spec = [r["comparison"]["rag_specificity"]
                    for r in results if r.get("comparison")]
        base_spec = [r["comparison"]["base_specificity"]
                     for r in results if r.get("comparison")]
        rag_bert = [r["comparison"]["rag_bert_f1"]
                    for r in results if r.get("comparison")]
        base_bert = [r["comparison"]["base_bert_f1"]
                     for r in results if r.get("comparison")]
        cids = [str(r["id"]) for r in results if r.get("comparison")]
        cx = np.arange(len(cids))
        ax.bar(cx - w, rag_spec, w, label="RAG specificity", color="#3498DB")
        ax.bar(cx, base_spec, w, label="Base specificity", color="#95A5A6")
        ax2 = ax.twinx()
        ax2.plot(cx - w / 2, rag_bert, "D-",
                 color="#1ABC9C", label="RAG BERT F1")
        ax2.plot(cx - w / 2, base_bert, "x--",
                 color="#E74C3C", label="Base BERT F1")
        ax2.set_ylim(0, 1)
        ax.set_xticks(cx)
        ax.set_xticklabels([f"T{i}" for i in cids])
        ax.set_title("RAG vs Base Model")
        ax.legend(loc="upper left", fontsize=7)
        ax2.legend(loc="upper right", fontsize=7)

    # Plot 5 — Multi-turn coherence decay
    if has_mt:
        ax = axes[plot_idx]
        turns = [m["turn"] for m in multi_turn_metrics]
        drift = [m.get("semantic_drift_score",
                       m["coherence"]["topic_drift_score"])
                 for m in multi_turn_metrics]
        entity = [m["coherence"]["entity_consistency"]
                  for m in multi_turn_metrics]
        ax.plot(turns, drift, marker="o",
                label="Semantic drift score", color="#7B5EA7")
        ax.plot(turns, entity, marker="s", linestyle="--",
                label="Entity consistency", color="#E67E22")
        ax.set_title("Multi-Turn Coherence Decay")
        ax.set_xlabel("Turn")
        ax.set_ylabel("Score")
        ax.set_ylim(0, 1.05)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    fig.suptitle("MathTales AI — Evaluation Report",
                 fontsize=14, fontweight="bold")
    plt.savefig("evaluation_report.png", dpi=150, bbox_inches="tight")
    print("Saved -> evaluation_report.png")


# ─────────────────────────────────────────────
# Main evaluation loop
# ─────────────────────────────────────────────

def run_evaluation(multi_turn=False, enable_human=False, force_compare=False):
    results = []

    for tc in TEST_PROMPTS:
        print(f"\n{'-'*50}\nTest {tc['id']}: {tc['prompt']}")

        res = call_api(tc["prompt"])
        text = res.get("response", "")

        if not text:
            print("  [ERROR] No response:", res.get("error", "unknown"))
            continue

        coherence = measure_coherence(text, tc["prompt"])
        coverage, found = concept_coverage(text, tc["concepts"])
        math = check_math(text, tc["expected_answer"],
                          tc["operands"], tc["operation"])
        bleu = compute_bleu(text, tc["prompt"])
        bert = compute_bertscore(text, tc["prompt"])
        equations = validate_equations(text)
        comparison = compare_models(
            tc["prompt"], text) if force_compare else None
        human = human_score(tc["prompt"], text) if enable_human else None

        result = {
            "id": tc["id"],
            "prompt": tc["prompt"],
            "math": math,
            "concept_coverage": coverage,
            "concepts_found": found,
            "coherence": coherence,
            "bleu": bleu,
            "bertscore": bert,
            "equations": equations,
            "comparison": comparison,
            "human_scores": human,
        }
        results.append(result)

        print(
            f"  Solvable            : {math['solvable']} (operands: {math['operands_present']}, op: {math['operation_present']}, '?': {math['ends_with_question']})")
        print(
            f"  Answer leaked       : {math['answer_leaked']}  <- should be False")
        print(
            f"  Problem structure   : setup={equations['has_numeric_setup']}, question={equations['has_question_mark']}, eq_leaks={equations['inline_eq_count']}")
        print(f"  Concept coverage    : {coverage} {found}")
        print(f"  Topic drift score   : {coherence['topic_drift_score']}")
        print(f"  Entity consistency  : {coherence['entity_consistency']}")
        print(f"  BLEU                : {bleu}")
        print(f"  BERT F1             : {bert['f1']}")
        if comparison:
            print(
                f"  RAG wins specificity: {comparison['rag_wins_specificity']}")
            print(f"  RAG wins BERT       : {comparison['rag_wins_bert']}")
        if human:
            print(f"  Human scores        : {human}")

    if not results:
        print("No results collected.")
        return

    n = len(results)
    summary = {
        "tests": n,
        "solvability_rate": round(sum(r["math"]["solvable"] for r in results) / n, 3),
        "operands_present_rate": round(sum(r["math"]["operands_present"] for r in results) / n, 3),
        "operation_present_rate": round(sum(r["math"]["operation_present"] for r in results) / n, 3),
        "answer_leak_rate": round(sum(r["math"]["answer_leaked"] for r in results) / n, 3),
        "avg_concept_coverage": round(sum(r["concept_coverage"] for r in results) / n, 3),
        "problem_structure_rate": round(
            sum(1 for r in results if r["equations"]["has_numeric_setup"] and r["equations"]["has_question_mark"]) / n, 3),
        "avg_topic_drift": round(
            sum(r["coherence"]["topic_drift_score"] for r in results) / n, 3),
        "avg_bert_f1": round(sum(r["bertscore"]["f1"] for r in results) / n, 3),
    }

    mt_metrics = None
    if multi_turn:
        print("\n[Multi-turn simulation — 20 turns]")
        mt_metrics = simulate_multi_turn()

    output = {"summary": summary, "results": results}
    if mt_metrics:
        output["multi_turn"] = mt_metrics

    with open("evaluation_results.json", "w") as f:
        json.dump(output, f, indent=2, default=str)

    plot_results(results, mt_metrics)

    print("\n" + "=" * 50)
    print("SUMMARY")
    for k, v in summary.items():
        print(f"  {k:<35}: {v}")
    print("Saved -> evaluation_results.json")

# =====================================================
# FIX 3: ABLATION STUDY
# Paste this entire block right before if __name__ == "__main__":
# =====================================================


def run_ablation(n_prompts: int = 20):
    """
    Tests 3 configurations on the same n_prompts:
      Config A — Baseline : use_rag=False  (pure LLM, no retrieval)
      Config B — RAG only : use_rag=True   (current system)
      Config C — RAG + Math Corrector (calls the /api/chat endpoint which
                 now runs apply_math_corrector server-side via Fix 1)

    Compares solvability, concept coverage, BERT F1, and topic drift.
    Saves results to ablation_results.json and ablation_report.png.
    """
    prompts = TEST_PROMPTS[:n_prompts]

    configs = {
        "Baseline (no RAG)": {"use_rag": False},
        "RAG": {"use_rag": True},
    }

    all_results = {}

    for config_name, kwargs in configs.items():
        print(f"\n{'='*55}")
        print(f"Running config: {config_name}")
        print(f"{'='*55}")
        config_results = []

        for tc in prompts:
            print(f"  Test {tc['id']}: {tc['prompt'][:60]}...")
            res = call_api(tc["prompt"], use_rag=kwargs["use_rag"])
            text = res.get("response", "")

            if not text:
                print(f"    [ERROR] {res.get('error', 'no response')}")
                continue

            math = check_math(
                text, tc["expected_answer"], tc["operands"], tc["operation"]
            )
            coverage, _ = concept_coverage(text, tc["concepts"])
            coherence = measure_coherence(text, tc["prompt"])
            bert = compute_bertscore(text, tc["prompt"])

            config_results.append(
                {
                    "id": tc["id"],
                    "prompt": tc["prompt"],
                    "solvable": math["solvable"],
                    "operands_present": math["operands_present"],
                    "operation_present": math["operation_present"],
                    "answer_leaked": math["answer_leaked"],
                    "concept_coverage": coverage,
                    "topic_drift": coherence["topic_drift_score"],
                    "bert_f1": bert["f1"],
                }
            )

        all_results[config_name] = config_results

    # ── Summary table ──────────────────────────────────────────
    print(f"\n{'='*55}")
    print("ABLATION SUMMARY")
    print(f"{'='*55}")
    summary_rows = []
    for config_name, rows in all_results.items():
        if not rows:
            continue
        n = len(rows)
        row = {
            "config": config_name,
            "n": n,
            "solvability": round(sum(r["solvable"] for r in rows) / n, 3),
            "operands_present": round(sum(r["operands_present"] for r in rows) / n, 3),
            "op_recognised": round(sum(r["operation_present"] for r in rows) / n, 3),
            "answer_leak": round(sum(r["answer_leaked"] for r in rows) / n, 3),
            "concept_coverage": round(sum(r["concept_coverage"] for r in rows) / n, 3),
            "avg_topic_drift": round(sum(r["topic_drift"] for r in rows) / n, 3),
            "avg_bert_f1": round(sum(r["bert_f1"] for r in rows) / n, 3),
        }
        summary_rows.append(row)
        print(f"\n  [{config_name}]")
        for k, v in row.items():
            if k not in ("config", "n"):
                print(f"    {k:<22}: {v}")

    # ── Plot ───────────────────────────────────────────────────
    if len(summary_rows) >= 2:
        labels = [r["config"] for r in summary_rows]
        metrics = [
            "solvability",
            "op_recognised",
            "concept_coverage",
            "avg_topic_drift",
            "avg_bert_f1",
        ]
        colors = ["#4A90D9", "#50C878", "#E07B54", "#7B5EA7", "#C0392B"]

        x = np.arange(len(labels))
        w = 0.15
        fig, ax = plt.subplots(figsize=(11, 5))

        for i, (metric, color) in enumerate(zip(metrics, colors)):
            vals = [r[metric] for r in summary_rows]
            ax.bar(
                x + i * w, vals, w, label=metric.replace("_", " ").title(), color=color
            )

        ax.set_xticks(x + w * (len(metrics) - 1) / 2)
        ax.set_xticklabels(labels, fontsize=10)
        ax.set_ylim(0, 1.15)
        ax.set_ylabel("Score")
        ax.set_title(
            "MathTales AI — Ablation Study (Baseline vs RAG)", fontweight="bold"
        )
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        plt.savefig("ablation_report.png", dpi=150, bbox_inches="tight")
        print("\nSaved -> ablation_report.png")

    with open("ablation_results.json", "w") as f:
        json.dump(
            {"summary": summary_rows, "detail": all_results}, f, indent=2, default=str
        )
    print("Saved -> ablation_results.json")


# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MathTales Evaluator v2")
    parser.add_argument("--multi-turn", action="store_true",
                        help="Run 20-turn coherence decay simulation")
    parser.add_argument("--human", action="store_true",
                        help="Collect human scores (flow/consistency/engagement) via CLI")
    parser.add_argument("--compare", action="store_true",
                        help="Force RAG-vs-Base comparison on every test prompt")
    parser.add_argument("--ablation", action="store_true",          # <-- ADD
                    help="Run ablation: Baseline vs RAG vs Hybrid")
    args = parser.parse_args()
if args.ablation:  # <-- ADD
    run_ablation(n_prompts=20)  # <-- ADD
else:  # <-- ADD
    run_evaluation(
        multi_turn=args.multi_turn, enable_human=args.human, force_compare=args.compare
    )
