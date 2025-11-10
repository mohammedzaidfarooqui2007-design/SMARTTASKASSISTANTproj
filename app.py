from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from datetime import datetime
import os
import asyncio
from contextlib import asynccontextmanager

# ======================================================
# 🔗 MONGODB CONNECTION (with fallback)
# ======================================================
MONGO_URL = "mongodb+srv://mdaqdushussain019_db_user:aqdus019@cluster0.pcew0uy.mongodb.net/?appName=Cluster0"
try:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    client.server_info()  # Trigger connection
    db = client["smart_assistant"]
    tasks_collection = db["tasks"]
    events_collection = db["events"]
    print("✅ Connected to MongoDB successfully!")
except Exception as e:
    print("⚠️ MongoDB connection failed:", e)
    client = None
    db = None
    tasks_collection = None
    events_collection = None

# ======================================================
# 📦 LOCAL IMPORTS
# ======================================================
from agent.date_parser_helper import extract_time, format_time
from agent import memory_manager, notify
from agent.llm_agent import process_message
from agent.notify import schedule_reminder
from agent.broadcasting import add_client, remove_client, broadcast_notification

# ======================================================
# 🌱 FASTAPI APP SETUP (with modern lifespan)
# ======================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 App starting up...")
    memory_manager.ensure_memory()
    asyncio.create_task(notify.send_reminders(app))
    yield
    try:
        memory = memory_manager.load_memory()
        memory_manager.save_memory(memory)
        print("✅ Memory saved successfully on shutdown.")
    except Exception as e:
        print("⚠ Error saving memory on shutdown:", e)
    print("🛑 App shutdown complete.")

app = FastAPI(title="Smart Task Assistant", lifespan=lifespan)

# ======================================================
# 🧩 STATIC FILES & TEMPLATES
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# ======================================================
# 🌍 MAIN INTERFACE
# ======================================================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    memory = memory_manager.load_memory()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "tasks": memory["tasks"],
        "events": memory["events"]
    })

# ======================================================
# 🧠 MEMORY ROUTES
# ======================================================
@app.get("/memory")
async def get_memory():
    return JSONResponse(memory_manager.load_memory())

@app.post("/send")
async def send_message(req: dict):
    user_input = req.get("message", "")
    result = process_message(user_input)
    msg_type = result["result"].get("type", "chat")
    reply = result["reply"]

    detected_time = extract_time(user_input)
    if detected_time and msg_type in ["task", "event"]:
        formatted_time = format_time(detected_time)
        asyncio.create_task(schedule_reminder(user_input, formatted_time))
        reply += f"\n🕒 Reminder set for {formatted_time}"

    return JSONResponse({
        "reply": reply,
        "type": msg_type,
        "source": result["result"]["source"]
    })

@app.post("/remove")
async def remove_item(request: Request):
    data = await request.json()
    updated_memory = memory_manager.complete_item(data)
    return JSONResponse({
        "status": "completed",
        "memory": updated_memory
    })

@app.post("/remove-auto")
async def remove_auto(request: Request):
    data = await request.json()
    message = data.get("message", "")
    reply = memory_manager.complete_item(message)
    return JSONResponse({"reply": reply})

# ======================================================
# 🔔 CHECK REMINDERS
# ======================================================
@app.get("/check_reminders")
async def check_reminders():
    memory = memory_manager.load_memory()
    now = datetime.now()
    notifications = []

    for section in ["tasks", "events"]:
        for item in memory.get(section, []):
            if not item.get("completed") and item.get("reminder_time"):
                reminder_time = datetime.fromisoformat(item["reminder_time"])
                if reminder_time <= now:
                    notifications.append({
                        "title": f"Reminder: {section[:-1].capitalize()}",
                        "message": item["description"]
                    })
                    item["completed"] = True
                    memory_manager.save_memory(memory)

    return {"notifications": notifications}

# ======================================================
# ⚡ WEBSOCKETS
# ======================================================
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    await add_client(ws)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        await remove_client(ws)

@app.get("/test-popup")
async def test_popup():
    await broadcast_notification("Test Notification", "Your popup system is working 🎉")
    return {"status": "sent"}

# ======================================================
# ▶ RUN DIRECTLY
# ======================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)




