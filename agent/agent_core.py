import re
from agent import memory_manager

TASK_KEYWORDS = r"(add|create|buy|get|call|email|send|pay|remember|task|todo)"
EVENT_KEYWORDS = r"(meet|appointment|event|schedule|birthday|remind|plan|attend|conference)"

def detect_intent(user_input):
    """Detect intent based on regex keywords."""
    if re.search(TASK_KEYWORDS, user_input, re.IGNORECASE):
        return "task"
    elif re.search(EVENT_KEYWORDS, user_input, re.IGNORECASE):
        return "event"
    return "chat"

def add_item(text, category, source="regex"):
    """Add task/event to memory (connected with memory_manager)."""
    memory_manager.add_item({
        "text": " ".join(text.split(" ")[0:8]),
        "type": category,
        "source": source
    })
    print(f"✅ Added {category} via {source}: {text}")