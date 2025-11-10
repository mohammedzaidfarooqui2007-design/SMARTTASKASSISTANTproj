from pymongo import MongoClient
from datetime import datetime
import os
import certifi
import json

# ======================================================
# 🧩 MONGO CONNECTION
# ======================================================

from pymongo import MongoClient
import certifi

# ======================================================
# 🧩 DIRECT MONGO CONNECTION (no environment variable)
# ======================================================
MONGO_URL = "mongodb+srv://mdaqdushussain019_db_user:aqdus019@cluster0.pcew0uy.mongodb.net/?retryWrites=true&w=majority"

try:
    client = MongoClient(
        MONGO_URL,
        tls=True,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=5000,
        retryWrites=True,
        w="majority"
    )
    db = client["smart_assistant"]
    db.list_collection_names()  # quick connection test
    print("✅ MongoDB connection successful on Render!")
except Exception as e:
    print("⚠️ MongoDB connection failed:", e)
    print("⚠️ Running in offline mode (local memory only)")
    client = None
    db = None

if db:
    tasks_collection = db["tasks"]
    events_collection = db["events"]
else:
    tasks_collection = []
    events_collection = []

import json
import os
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
def load_memory():
    tasks = list(tasks_collection.find({}, {"_id": 0}))
    events = list(events_collection.find({}, {"_id": 0}))
    return {"tasks": tasks, "events": events}



def save_memory(memory):
    tasks_collection.delete_many({})
    events_collection.delete_many({})
    if "tasks" in memory:
        tasks_collection.insert_many(memory["tasks"])
    if "events" in memory:
        events_collection.insert_many(memory["events"])



def ensure_memory():
    try:
        db.list_collection_names()  # Test connection
        print("✅ MongoDB connection OK")
    except Exception as e:
        print("⚠ MongoDB connection failed:", e)
        print("⚠ Running in offline mode (local memory only)")



def add_item(data):
    text = (data.get("text") or "").strip()
    type_ = (data.get("type") or "").strip().lower()
    source = (data.get("source") or "regex").strip().lower()

    if not text:
        print("⚠ No text provided to add")
        return load_memory()

    item = {
        "text": text,
        "status": "pending",
        "source": source,
        "created_at": datetime.now().isoformat()
    }

    if type_ == "task":
        tasks_collection.insert_one(item)
        print(f"✅ Task added: {text} ({source})")
    elif type_ == "event":
        events_collection.insert_one(item)
        print(f"✅ Event added: {text} ({source})")
    else:
        print("⚠ Invalid type. Must be 'task' or 'event'")

    return load_memory()



    # 🔹 Try specific type first

def complete_item(message: str):
    message_lower = message.lower().strip()
    message_words = set(message_lower.split())

    best_key, best_doc, best_score = None, None, 0

    for key, collection in [("tasks", tasks_collection), ("events", events_collection)]:
        for doc in collection.find():
            item_words = set(doc["text"].lower().split())
            common = message_words.intersection(item_words)
            score = len(common) / max(len(item_words), 1)
            if score > best_score:
                best_score, best_key, best_doc = score, key, doc

    if best_score >= 0.3 and best_doc:
        if best_key == "tasks":
            tasks_collection.delete_one({"text": best_doc["text"]})
        else:
            events_collection.delete_one({"text": best_doc["text"]})
        return f"✅ Marked '{best_doc['text']}' as completed (keyword match {round(best_score*100)}%)."

    return "⚠ No matching task or event found to complete."








def get_all_items():
    tasks = list(tasks_collection.find({}, {"_id": 0}))
    events = list(events_collection.find({}, {"_id": 0}))
    return tasks + events






