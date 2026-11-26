"""
Groq LLaMA Chatbot Engine for Traffic Event Co-Pilot.
Falls back to rule-based answers for the 5 known police question types (fast, grounded).
Calls Groq LLaMA 3.1 only for open-ended questions outside the rule-based categories.
Supports bilingual output: English and Telugu (తెలుగు).
API key read from GROQ_API_KEY environment variable (stored in .env, never in code).
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# 1.  Load .env if python-dotenv is available (graceful fallback)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
except ImportError:
    pass  # dotenv not installed — user must set GROQ_API_KEY in environment

# Import police_chatbot for the rule-based layer
try:
    import police_chatbot as _PC  # rule-based engine already built
    _PC_AVAILABLE = True
except ImportError:
    _PC_AVAILABLE = False

# ---------------------------------------------------------------------------
# 2.  Groq client (lazy init — only created on first open-ended call)
# ---------------------------------------------------------------------------
_groq_client = None
_GROQ_MODEL = "llama-3.1-8b-instant"   # fastest; switch to llama-3.3-70b-versatile for smarter


def _get_groq_client():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from groq import Groq  # pip install groq
        _groq_client = Groq(api_key=api_key)
        return _groq_client
    except ImportError:
        return None


def groq_available() -> bool:
    """Return True if the Groq client can be initialised."""
    return _get_groq_client() is not None


# ---------------------------------------------------------------------------
# 3.  Build a compact res summary for the Groq system prompt
#     (keeps token usage low — only factual numbers, no prose)
# ---------------------------------------------------------------------------
def _build_res_summary(res: dict[str, Any]) -> str:
    if not res:
        return "No scenario computed yet."
    P = res.get("params", {})
    dem = res.get("demand", {})
    so = res.get("sum_opt", {})
    corridor = res.get("corridor")
    hotspots = res.get("hotspots", pd.DataFrame())
    diversions = res.get("diversions", [])

    lines = [
        f"EVENT: {P.get('event_name', 'Unknown')} | PHASE: {P.get('phase', 'ingress')} "
        f"| START: {P.get('start_time', '?')} | CROWD: {P.get('attendance', 0):,}",
        f"DEMAND: {dem.get('total_vehicles', 0):,} vehicles | "
        f"Peak PCU/h: {dem.get('peak_hourly_pcu', 0):,.0f} | "
        f"Metro riders: {dem.get('metro_riders', 0):,.0f} | "
        f"Pedestrians: {dem.get('pedestrians', 0):,.0f}",
        f"NETWORK: Max V/C (optimised): {so.get('max_vc', 0):.2f} | "
        f"Roads over capacity: {so.get('congested', 0)} | Near capacity: {so.get('near', 0)}",
    ]

    if not hotspots.empty:
        top = hotspots.head(4)
        hs_lines = []
        for idx, (_, r) in enumerate(top.iterrows()):
            hs_lines.append(
                f"  [H-{idx+1}] {r.get('street','?')} V/C={r.get('vc',0):.2f} "
                f"load={r.get('load_pcu_hr',0):,.0f} cap={r.get('capacity_pcu_hr',0):,.0f}"
            )
        lines.append("HOTSPOTS:\n" + "\n".join(hs_lines))

    if diversions:
        div_lines = []
        for d in diversions[:4]:
            feasible = "feasible +{extra_m}m".format(**d) if d.get("feasible") else "NO safe detour"
            div_lines.append(f"  {d.get('tag','[D]')} {d.get('name','?')} V/C={d.get('vc',0):.2f} → {feasible}")
        lines.append("DIVERSIONS:\n" + "\n".join(div_lines))

    if corridor:
        lines.append(
            f"EMERGENCY CORRIDOR [E-1]: {corridor.get('length_m',0):,}m | "
            f"Free ETA: {corridor.get('free_min',0)} min | "
            f"Congested ETA: {corridor.get('unprotected_min',0)} min"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4.  Main entry point — hybrid rule-based + Groq
# ---------------------------------------------------------------------------
def generate_response(
    query: str,
    res: dict[str, Any] | None,
    lang: str = "English",
    chat_history: list[dict] | None = None,
) -> tuple[str, str]:
    """
    Returns (answer_text, source) where source is 'rule' or 'groq' or 'fallback'.

    chat_history: list of {"role": "user"/"assistant", "content": "..."} for Groq context.
    """
    is_te = str(lang).strip() == "తెలుగు"

    # --- 4a. Rule-based layer first (fast, zero API calls) ---
    if _PC_AVAILABLE:
        try:
            rule_ans = _PC.generate_police_response(query, res, lang=lang)
            # If rule-based engine returned a meaningful answer (has a heading)
            if rule_ans and ("###" in rule_ans or len(rule_ans) > 80):
                return rule_ans, "rule"
        except Exception:
            pass

    # --- 4b. Groq LLM fallback ---
    client = _get_groq_client()
    if client is None or not res:
        # No API key / no scenario — return polite fallback
        if is_te:
            return (
                "క్షమించండి, ఈ ప్రశ్నకు నేను ఇప్పుడు సమాధానం ఇవ్వలేకపోతున్నాను. "
                "దయచేసి రద్దీ, మళ్లింపు, గ్రీన్ కారిడార్ లేదా పోలీసు మోహరింపు "
                "గురించి అడగండి.",
                "fallback"
            )
        return (
            "I can answer questions about hotspots, diversions, the emergency corridor, "
            "police deployment, or parking. Please run the Co-Pilot first if you haven't.",
            "fallback"
        )

    res_summary = _build_res_summary(res)
    lang_instruction = "Respond in Telugu (తెలుగు) script." if is_te else "Respond in English."

    system_prompt = f"""You are a professional AI Traffic Event Co-Pilot for Hyderabad Police.
You help police officers understand and implement the traffic management plan.

STRICT RULES:
1. Only use numbers and facts from the SCENARIO DATA below — never invent figures.
2. If a fact is not in the data, say "Data not available for this scenario."
3. All planning heuristics are ASSUMED — label them clearly.
4. Keep responses concise and tactical — suitable for a police officer on duty.
5. {lang_instruction}

SCENARIO DATA:
{res_summary}
"""

    messages = [{"role": "system", "content": system_prompt}]

    # Include recent conversation context (last 6 turns max)
    if chat_history:
        for msg in chat_history[-6:]:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": query})

    try:
        response = client.chat.completions.create(
            model=_GROQ_MODEL,
            messages=messages,
            max_tokens=512,
            temperature=0.3,   # low temp = factual, grounded
        )
        answer = response.choices[0].message.content.strip()
        return answer, "groq"
    except Exception as exc:
        err = str(exc)
        if is_te:
            return f"గ్రోక్ AI కనెక్షన్ విఫలమైంది: {err[:80]}", "error"
        return f"Groq AI connection failed: {err[:80]}", "error"


# ---------------------------------------------------------------------------
# 5.  Greeting message (called when plan first loads)
# ---------------------------------------------------------------------------
def greeting(event_name: str, lang: str = "English") -> str:
    is_te = str(lang).strip() == "తెలుగు"
    groq_badge = "🤖 AI" if groq_available() else "📋 Rule-Based"
    if is_te:
        return (
            f"నమస్కారం, ఆఫీసర్. **{event_name}** ఈవెంట్ కోసం ట్రాఫిక్ కార్యాచరణ "
            f"ప్రణాళిక సిద్ధంగా ఉంది. {groq_badge} మోడ్‌లో పనిచేస్తున్నాను. "
            f"రద్దీ ప్రాంతాలు, ట్రాఫిక్ మళ్లింపులు, అత్యవసర కారిడార్ లేదా "
            f"పోలీసు సిబ్బంది మోహరింపు గురించి నన్ను అడగండి."
        )
    return (
        f"Hello, Officer. The traffic operation plan for **{event_name}** is ready. "
        f"Running in {groq_badge} mode. "
        f"Ask me about hotspots, diversions, the emergency corridor, "
        f"deployment, or any operational question about this plan."
    )


# ---------------------------------------------------------------------------
# 6.  Source badge helper (shown in chat UI next to AI responses)
# ---------------------------------------------------------------------------
def source_badge(source: str, lang: str = "English") -> str:
    is_te = str(lang).strip() == "తెలుగు"
    if source == "groq":
        return "🤖 AI-assisted (Groq)" if not is_te else "🤖 AI-సహాయం (Groq)"
    if source == "rule":
        return "📋 Plan data" if not is_te else "📋 ప్లాన్ డేటా"
    return "⚠️ Fallback" if not is_te else "⚠️ ఫాల్‌బ్యాక్"
