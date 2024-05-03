
import asyncio
import websockets
import websockets_routes

router = websockets_routes.Router()

@router.route("/ws/tasks/{task_id}")
async def getTaskStatus(ws, path):
    await ws.send("get task status route!")

@router.route("/ws/results/{task_id}")
async def getResult(ws, path):
    await ws.send("get result route!")

async def WebSocketServer():
    start_server = websockets.serve(router, "localhost", 8765)
    await start_server
    print("WebSocket server running on ws://localhost:8765")
    await asyncio.Future()  # Keep the event loop running