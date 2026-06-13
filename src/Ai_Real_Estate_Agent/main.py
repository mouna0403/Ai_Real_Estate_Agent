import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from Ai_Real_Estate_Agent.utils.agent import ask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def chat_response(text: str) -> dict:
    """Build the correct Google Chat Add-on response format."""
    return {
        "hostAppDataAction": {
            "chatDataAction": {
                "createMessageAction": {
                    "message": {"text": text}
                }
            }
        }
    }

@app.post("/ask")
async def ask_endpoint(request: Request):
    data = await request.json()
    question = data.get("question")
    if not question:
        return {"error": "Missing question"}
    return {"answer": ask(question)}

@app.post("/chat")
async def google_chat(request: Request):
    try:
        data = await request.json()
        logger.info(f"[CHAT] Full payload: {data}")

        chat = data.get("chat", {})
        event_type = chat.get("type", "")
        logger.info(f"[CHAT] Event type: {event_type}")

        if event_type == "ADDED_TO_SPACE":
            return chat_response("Hello! I am your Ile-de-France real estate assistant. Ask me anything about IDF.")

        if event_type == "REMOVED_FROM_SPACE":
            return {}

        # Correct path for Google Chat Add-on message
        text = chat.get("messagePayload", {}).get("message", {}).get("text", "").strip()
        logger.info(f"[CHAT] Message text: '{text}'")

        if not text:
            return chat_response("I did not understand your message.")

        logger.info("[CHAT] Calling agent...")
        answer = ask(text)
        logger.info(f"[CHAT] Answer: {answer[:100]}")
        return chat_response(answer)

    except Exception as e:
        logger.error(f"[CHAT] Exception: {str(e)}", exc_info=True)
        return chat_response("An error occurred. Please try again.")

@app.get("/")
def health():
    return {"status": "ok"}