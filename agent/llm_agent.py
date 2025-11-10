import json
import re
from groq import Groq
from textblob import TextBlob
from agent.memory_manager import add_item, complete_item
import os
# ✅ Groq API Setup
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "llama-3.1-8b-instant"

client = Groq(api_key=GROQ_API_KEY)


# ✅ Keyword Extraction — uses Regex + TextBlob + LLM fallback
def extract_keywords(text):
    import re
    from textblob import TextBlob
    from groq import Groq

    text = text.strip()
    if not text:
        return ""

    # --- 1️⃣ Regex-based smart keyword extraction ---
    regex_patterns = [
        r"\b(?:need to|want to|have to|must|should|plan to|try to|buy|make|do|submit|attend|call|meet|prepare|finish)\b\s+(.*)",
        r"\b(?:schedule|join|attend|arrange|set up|organize)\b\s+(.*)"
    ]
    for pattern in regex_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            phrase = match.group(1).strip()
            if len(phrase.split()) > 1:
                return phrase

    # --- 2️⃣ TextBlob noun phrase extraction ---
    blob = TextBlob(text)
    noun_phrases = blob.noun_phrases
    if noun_phrases:
        phrase = " ".join(noun_phrases[:3])
        if phrase:
            return phrase

    # --- 3️⃣ LLM Fallback (Groq llama-3.1-8b-instant) ---
    try:
        client = Groq(api_key=GROQ_API_KEY)
        chat = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Extract only the short actionable or event phrase (2–6 words) from this text."},
                {"role": "user", "content": text}
            ]
        )
        phrase = chat.choices[0].message.content.strip()
        phrase = re.sub(r"[^a-zA-Z0-9\s]", "", phrase)
        if phrase and len(phrase.split()) <= 6:
            return phrase
    except Exception:
        pass

    # --- 4️⃣ Simple fallback ---
    words = [w for w in text.split() if len(w) > 3 and w.lower() not in [
        "the", "that", "this", "and", "with", "from", "have", "will",
        "need", "want", "make", "buy", "do", "to", "for", "a", "an", "it"
    ]]
    return " ".join(words[:4])


# ✅ Smart Matching Patterns
# ✅ Smart Matching Patterns

TASK_PATTERNS = [
    # 🔹 Only normal to-do or work-related actions
    r"\b(add|create|make|want)\b.*\b(task|todo|note)\b",
    r"\b(submit|report|assignment)\b",
    r"\b(buy|item|milk|groceries|curd)\b",
    r"\b(work|study|clean|send)\b"
]

EVENT_PATTERNS = [
    # 🔹 Put reminder-related words here
    r"\b(remind|reminder|remind me|notify|alert)\b",
    r"\b(meeting|event|appointment|class|birthday|conference)\b",
    r"\bschedule\b.*\b(meeting|call|zoom)\b",
    r"\b(join|attend)\b.*\b(event|meeting|session)\b",
    r"\b(on|at)\b.*\b(\d{1,2}(:\d{2})?\s?(am|pm)?)\b"
]

COMPLETE_PATTERNS = [
    r"\b(done|finished|completed|over|complete)\b"
]



# ✅ LLM Smart Classification — Used as fallback
def ai_response(prompt: str):
    """LLM call for fallback classification (task / event / chat)."""
    try:
        chat = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a Smart Task Assistant. Identify if the message is a task, event, or chat."},
                {"role": "user", "content": prompt}
            ]
        )
        return chat.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠ LLM Error: {e}")
        return ""


# ✅ Core Processing Function
# ✅ Core Processing Function
def process_message(message: str):
    import difflib
    import re
    msg_lower = message.lower().strip()

    # 🧠 Helper to find best fuzzy match among existing tasks/events
    from agent.memory_manager import get_all_items
    def find_best_match(text, tasks):
        text = text.lower().strip()
        best_match = None
        highest_ratio = 0.0
        for t in tasks:
            ratio = difflib.SequenceMatcher(None, text, t["text"].lower()).ratio()
            if ratio > highest_ratio:
                highest_ratio = ratio
                best_match = t
        return best_match if highest_ratio > 0.7 else None

    # 🟢 Completion Detection (Regex + Smart Match)
    if any(re.search(p, msg_lower) for p in COMPLETE_PATTERNS):
        # Extract main phrase before "done/completed"
        parts = re.split(r"\b(done|finished|completed|over|complete)\b", msg_lower)
        key_text = parts[0].strip() if parts else message.strip()
        if not key_text:
            key_text = extract_keywords(message)

        # 🧩 Get all current tasks/events
        try:
            all_items = get_all_items()
        except Exception:
            all_items = []

        # 🧠 Find best fuzzy match among all (task + event)
        match_item = None
        if all_items:
            best_match = None
            highest_ratio = 0.0
            for t in all_items:
                ratio = difflib.SequenceMatcher(None, key_text.lower(), t["text"].lower()).ratio()
                if ratio > highest_ratio:
                    highest_ratio = ratio
                    best_match = t
            if highest_ratio > 0.65:
                match_item = best_match

        # ✅ Use actual stored type instead of guessing
        if match_item:
            complete_item({"text": match_item["text"], "type": match_item["type"]})
            return {
                "result": {"type": "complete", "source": "regex"},
                "reply": f"✅ {match_item['type'].capitalize()} '{match_item['text']}' completed and removed. ({match_item['source'].upper()})"
            }
        else:
            return {
                "result": {"type": "none", "source": "regex"},
                "reply": "⚠️ No matching task or event found to complete."
            }

    # 🟡 Regex-based Smart Matching
    if any(re.search(p, msg_lower) for p in TASK_PATTERNS):
        key_text = extract_keywords(message)
        add_item({"text": key_text, "type": "task", "source": "regex"})
        return {"result": {"type": "task", "source": "regex"}, "reply": f"📝 Task added: {key_text}"}

    elif any(re.search(p, msg_lower) for p in EVENT_PATTERNS):
        key_text = extract_keywords(message)
        add_item({"text": key_text, "type": "event", "source": "regex"})
        return {"result": {"type": "event", "source": "regex"}, "reply": f"📅 Event added: {key_text}"}

    # 🔵 LLM Fallback Detection
    raw = ai_response(message)
    try:
        if not raw:
            raise ValueError("Empty LLM response")

        lower = raw.lower()
        if any(word in lower for word in ["task", "todo", "reminder"]):
            key_text = extract_keywords(message)
            add_item({"text": key_text, "type": "task", "source": "llm"})
            return {"result": {"type": "task", "source": "llm"}, "reply": f"📝 Task added: {key_text}"}

        elif any(word in lower for word in ["event", "meeting", "appointment"]):
            key_text = extract_keywords(message)
            add_item({"text": key_text, "type": "event", "source": "llm"})
            return {"result": {"type": "event", "source": "llm"}, "reply": f"📅 Event added: {key_text}"}

        elif any(word in lower for word in ["done", "completed", "finished", "over"]):
            key_text = extract_keywords(message)
            all_items = get_all_items()
            match_item = find_best_match(key_text, all_items)
            if match_item:
                complete_item({"text": match_item["text"], "type": match_item["type"]})
                return {"result": {"type": "complete", "source": "llm"},
                        "reply": f"✅ Marked completed: {match_item['text']}"}
    except Exception as e:
        print(f"⚠ Error in LLM handling: {e}")

    # ⚪ Default Fallback
    return {"result": {"type": "chat", "source": "llm"}, "reply": "💬 Got it! No task or event detected."}
