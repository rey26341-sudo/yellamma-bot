"""
app/core/graph.py

DIFF NOTES (apply against your real file — I haven't seen
app/core/tools.py yet, so the save_appointment.invoke(...) ->
await save_appointment.ainvoke(...) line below assumes the tool
becomes async too; if tools.py stays sync, tell me and I'll adjust
this instead of guessing).

Changes from your version:
  1. booking_node is now `async def` (was `def`) so it can await the
     appointment save instead of running a blocking sync DB call
     inside an async graph invocation.
  2. save_input now sends "tenant_id": state["tenant_id"] instead of
     "business_id" — the real FK, resolved server-side by chat.py
     before this graph ever runs, not the display slug.
  3. save_appointment.invoke(...) -> await save_appointment.ainvoke(...)

Everything else (routing logic, keyword ladders, reply text) is
unchanged from what you pasted.
"""

import logging

from langgraph.graph import END, START, StateGraph

from app.core.llm import ask_gemini
from app.core.state import ChatState
from app.core.tools import save_appointment
from app.services.config_loader import load_config
from app.utils.parser import extract_name, extract_phone, extract_time

logger = logging.getLogger("core.graph")

GREETING_WORDS = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]


def _append_history(state: ChatState, role: str, text: str) -> None:
    state.setdefault("history", [])
    state["history"].append({"role": role, "text": text})
    state["history"] = state["history"][-12:]


def route_by_business_type(state: ChatState) -> str:
    config = load_config(state["business_id"])
    business_type = config.get("type", "booking")
    return "customer_support" if business_type == "customer_support" else "booking"


def customer_support_node(state: ChatState) -> ChatState:
    message = state["message"].lower().strip()
    business_id = state["business_id"]

    if message in GREETING_WORDS:
        reply = (
            "👋 Welcome to Pogo!\n\n"
            "I'm Pogo's AI Assistant.\n\n"
            "I can help you with:\n"
            "• AI-powered consumer research\n"
            "• Verified consumer panel\n"
            "• AI Interviewer\n"
            "• Quantitative surveys\n"
            "• Enterprise research solutions\n"
            "• Product capabilities\n"
            "• Pricing information\n"
            "• Booking a product demo\n\n"
            "How may I assist you today?"
        )
    elif any(w in message for w in ["help", "support", "assist"]):
        reply = (
            "I'd be happy to help.\n\n"
            "You can ask me about:\n\n"
            "• Consumer research\n"
            "• AI Interviewer\n"
            "• Verified consumer panel\n"
            "• Surveys\n"
            "• Enterprise capabilities\n"
            "• Case studies\n"
            "• Pricing\n"
            "• Booking a demo"
        )
    elif any(w in message for w in ["demo", "book demo", "schedule demo", "talk to sales", "sales"]):
        reply = (
            "Certainly.\n\n"
            "To arrange a personalized product demonstration, please share:\n\n"
            "• Full Name\n"
            "• Company Name\n"
            "• Work Email\n"
            "• Your research goals\n\n"
            "A Pogo specialist will contact you shortly."
        )
    elif any(w in message for w in ["pricing", "price", "cost", "quote"]):
        reply = (
            "Pogo offers customized enterprise pricing based on your research requirements.\n\n"
            "I'd recommend scheduling a product demo so the sales team can prepare a tailored quotation."
        )
    elif any(w in message for w in ["enterprise", "business", "organization", "company", "corporate"]):
        reply = (
            "Pogo helps enterprise organizations conduct AI-powered consumer research using verified "
            "participant panels, automated interviews, quantitative surveys and research analytics.\n\n"
            "What would you like to know?"
        )
    elif any(w in message for w in ["platform", "products", "product", "features", "capabilities", "what is pogo"]):
        reply = ask_gemini("Explain Pogo platform, products and capabilities.", business_id, state)
    elif "ai interviewer" in message:
        reply = ask_gemini("Explain AI Interviewer.", business_id, state)
    elif any(w in message for w in ["consumer panel", "panel", "participants"]):
        reply = ask_gemini("Explain the verified consumer panel.", business_id, state)
    elif any(w in message for w in ["survey", "surveys", "quant"]):
        reply = ask_gemini("Explain quantitative surveys.", business_id, state)
    elif any(w in message for w in ["case study", "case studies", "success story"]):
        reply = ask_gemini("Show available case studies.", business_id, state)
    elif any(w in message for w in ["thanks", "thank you"]):
        reply = (
            "You're welcome!\n\n"
            "If you'd like, I can also explain Pogo's platform, research capabilities, "
            "or help you request a product demo."
        )
    elif any(w in message for w in ["bye", "goodbye", "see you"]):
        reply = "Thank you for visiting Pogo.\n\nHave a wonderful day!"
    else:
        reply = ask_gemini(message, business_id, state)

    state["reply"] = reply
    return state


BOOKING_TRIGGER_WORDS = ["appointment", "book", "booking", "schedule", "reserve", "visit", "slot"]
SALON_INFO_WORDS = [
    "service", "services", "price", "pricing", "cost", "charge", "haircut", "hair",
    "hairstyle", "hair spa", "facial", "cleanup", "makeup", "bridal", "threading",
    "waxing", "manicure", "pedicure", "timing", "hours", "open", "closed", "location", "address",
]


async def booking_node(state: ChatState) -> ChatState:
    message = state["message"].lower().strip()
    business_id = state["business_id"]
    config = load_config(business_id)

    if state.get("step") == "awaiting_name":
        name = extract_name(message)
        if not name:
            state["reply"] = "Sorry, I couldn't understand your name. Could you please tell me your name again?"
            return state
        state["name"] = name
        state["step"] = "awaiting_phone"
        state["reply"] = f"Nice to meet you, {name}.\n\nMay I have your 10-digit mobile number?"
        return state

    if state.get("step") == "awaiting_phone":
        phone = extract_phone(message)
        if not phone:
            state["reply"] = "Please enter a valid 10-digit mobile number."
            return state
        state["phone"] = phone
        state["step"] = "awaiting_date"
        state["reply"] = "Thank you.\n\nWhich date would you like to book your appointment?"
        return state

    if state.get("step") == "awaiting_date":
        state["date"] = message
        state["step"] = "awaiting_time"
        state["reply"] = "Great.\n\ntime please?"
        return state

    if state.get("step") == "awaiting_time":
        time_value = extract_time(message)
        if not time_value:
            state["reply"] = "Please enter a valid time (example: 10 AM, 2 PM, 6:30 PM)."
            return state
        state["time"] = time_value
        state["step"] = None

        if not state.get("saved"):
            save_input = {
                # tenant_id, not business_id — the real FK, resolved
                # server-side before this graph ever ran (see
                # app/api/routes/chat.py). business_id stays available
                # in `state` for config/display purposes only.
                "tenant_id": state["tenant_id"],
                "name": state.get("name") or "",
                "phone": state.get("phone") or "",
                "service": state.get("service") or "",
                "date": state.get("date") or "",
                "time": time_value,
            }
            logger.info("Attempting save_appointment with input=%r", save_input)
            try:
                tool_result = await save_appointment.ainvoke(save_input)
                logger.info("save_appointment succeeded: %r", tool_result)
                state["saved"] = True
            except Exception:
                logger.exception("save_appointment FAILED for input=%r", save_input)

        state["reply"] = (
            "✅ Appointment request received.\n\n"
            f"Name: {state['name']}\n"
            f"Phone: {state['phone']}\n"
            f"Date: {state['date']}\n"
            f"Time: {time_value}\n\n"
            "Our salon team will contact you shortly for confirmation.\n\n"
            "Have a nice day!"
        )
        return state

    if any(w in message for w in BOOKING_TRIGGER_WORDS):
        state["step"] = "awaiting_name"
        state["reply"] = "Certainly! I can help you book an appointment.\n\nMay I know your full name?"
        return state

    if any(w in message for w in SALON_INFO_WORDS):
        state["reply"] = ask_gemini(message, business_id, state)
        return state

    if message in GREETING_WORDS:
        state["reply"] = (
            "Hello! Welcome to NAXBOT AI.\n\n"
            "I can help you with salon services, pricing information, and appointment bookings."
        )
        return state

    state["reply"] = config.get("fallback_reply") or config.get("fallback") or (
        "I can help you with our services, pricing, and appointments. "
        "Could you please tell me what you need?"
    )
    return state


def record_history_node(state: ChatState) -> ChatState:
    _append_history(state, "user", state["message"])
    _append_history(state, "assistant", state["reply"] or "")
    return state


def build_graph(checkpointer):
    graph = StateGraph(ChatState)

    graph.add_node("customer_support", customer_support_node)
    graph.add_node("booking", booking_node)
    graph.add_node("record_history", record_history_node)

    graph.add_conditional_edges(
        START,
        route_by_business_type,
        {"customer_support": "customer_support", "booking": "booking"},
    )
    graph.add_edge("customer_support", "record_history")
    graph.add_edge("booking", "record_history")
    graph.add_edge("record_history", END)

    return graph.compile(checkpointer=checkpointer)
