import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from agent import memory_manager
from agent.date_parser_helper import format_time  # if used elsewhere

# ✅ Import broadcast helper from main
from agent.broadcasting import broadcast_notification  

KOLKATA = ZoneInfo("Asia/Kolkata")
reminder_tasks = {}

async def send_reminders(app):
    """Background task: checks reminders every minute (uses aware datetimes)."""
    while True:
        try:
            memory = memory_manager.load_memory()
            now = datetime.now(KOLKATA)

            for section in ["tasks", "events"]:
                for item in memory.get(section, []):
                    if "reminder_time" in item and item.get("status") != "completed":
                        # reminder_time is stored as "YYYY-MM-DD HH:MM" (string)
                        try:
                            target = datetime.strptime(item["reminder_time"], "%Y-%m-%d %H:%M")
                            target = target.replace(tzinfo=KOLKATA)
                        except Exception:
                            # If stored value was ISO or different, try fromisoformat
                            try:
                                target = datetime.fromisoformat(item["reminder_time"])
                                if target.tzinfo is None:
                                    target = target.replace(tzinfo=KOLKATA)
                                else:
                                    target = target.astimezone(KOLKATA)
                            except Exception:
                                # skip invalid format
                                continue

                        # 🔔 Trigger notification when due
                        if now >= target and item.get("status") != "notified":
                            text = item.get("text", "No description")
                            print(f"🔔 Reminder: {text}")
                            item["status"] = "notified"
                            memory_manager.save_memory(memory)

                            # ✅ Broadcast instant notification to all connected clients
                            try:
                                await broadcast_notification(
                                    f"Reminder: {section[:-1].capitalize()}",
                                    text
                                )
                            except Exception as e:
                                print(f"⚠ WebSocket broadcast error: {e}")

            await asyncio.sleep(60)

        except Exception as e:
            print("⚠ Reminder loop error:", e)
            await asyncio.sleep(60)


async def schedule_reminder(message, reminder_time_str):
    """
    reminder_time_str expected in 'YYYY-MM-DD HH:MM' (Asia/Kolkata) or ISO.
    Schedules an asyncio task with correct delay using Asia/Kolkata as reference.
    """
    now = datetime.now(KOLKATA)

    # Parse incoming string robustly
    try:
        target = datetime.strptime(reminder_time_str, "%Y-%m-%d %H:%M")
        target = target.replace(tzinfo=KOLKATA)
    except Exception:
        try:
            target = datetime.fromisoformat(reminder_time_str)
            if target.tzinfo is None:
                target = target.replace(tzinfo=KOLKATA)
            else:
                target = target.astimezone(KOLKATA)
        except Exception:
            print(f"⚠ Invalid reminder_time format: {reminder_time_str}")
            return

    delay = (target - now).total_seconds()

    if delay <= 0:
        print(f"⏰ Skipping past reminder: {message} (target {target.isoformat()})")
        return

    async def reminder_task():
        await asyncio.sleep(delay)
        print(f"🔔 Reminder: {message}")

        # ✅ Broadcast real-time reminder notification
        try:
            await broadcast_notification("Reminder", message)
        except Exception as e:
            print(f"⚠ WebSocket broadcast error (schedule): {e}")

    task = asyncio.create_task(reminder_task())
    reminder_tasks[message] = task
    print(f"⏳ Reminder scheduled for: {target.isoformat()} → {message}")