from fastapi import WebSocket
import asyncio

connected_clients = []


async def add_client(ws: WebSocket):
    """Register a new connected WebSocket client."""
    connected_clients.append(ws)


async def remove_client(ws: WebSocket):
    """Remove disconnected WebSocket client."""
    if ws in connected_clients:
        connected_clients.remove(ws)


async def broadcast_notification(title: str, message: str):
    """Send a JSON notification to all connected WebSocket clients."""
    for ws in connected_clients:
        try:
            await ws.send_json({"title": title, "message": message})
        except Exception:
            await remove_client(ws)