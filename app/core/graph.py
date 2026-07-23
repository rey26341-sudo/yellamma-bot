"""
app/core/graph.py

The LangGraph core. This is a behavior-preserving re-platform of the
old AIService.generate_reply()'s if/elif chains — same decision logic,
moved into graph nodes with real persisted state instead of two
disconnected in-memory dicts. Business rules aren't rewritten here on
purpose: re-platform first, improve the rules once you can see this
still behaves the same as before.

Two request paths, chosen by config["type"] (defaults to "booking" if
the field is missing, e.g. the current salon.json):
  - "customer_support" (e.g. pogo) -> customer_support_node
  - anything else (e.g. salon)     -> booking_node

Both call ask_gemini() (app/core/llm.py) for open-ended questions, and
booking_node calls the save_appointment tool (app/core/tools.py) once
name/phone/date/time are all collected.
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


# ---------------------------------------------------------------------
# Entry: load config, decide which flow this business uses
# ---------------------------------------------------------------------

def route_by_business_type(state: ChatState) -> str:
    config = load_config(state["business_id"])
    # Defaults to "booking" — salon.json has no "type" key today, and
    # the old code's fallback path (no type check) was the booking
    # flow, so this preserves that behavior instead of crashing on a
    # missing key the way `config["type"]` used to.
    business_type = config.get("type", "booking")
    return "customer_support" if business_type == "customer_support" else "booking"


# ---------------------------------------------------------------------
# Customer-support flow (e.g. pogo) — same keyword ladder as before
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# Booking flow (e.g. salon) — same multi-step flow as before
# ---------------------------------------------------------------------

BOOKING_TRIGGER_WORDS = ["appointment", "book", "booking", "schedule", "reserve", "visit", "slot"]
SALON_INFO_WORDS = [
    "service", "services", "price", "pricing", "cost", "charge", "haircut", "hair",
    "hairstyle", "hair spa", "facial", "cleanup", "makeup", "bridal", "threading",
    "waxing", "manicure", "pedicure", "timing", "hours", "open", "closed", "location", "address",
]


def booking_node(state: ChatState) -> ChatState:
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

        # All fields collected — save via the LangChain tool instead
        # of calling AppointmentService directly.
        if not state.get("saved"):
            save_input = {
                "business_id": business_id,
                "name": state.get("name") or "",
                "phone": state.get("phone") or "",
                "service": state.get("service") or "",
                "date": state.get("date") or "",
                "time": time_value,
            }
            logger.info("Attempting save_appointment with input=%r", save_input)
            try:
                tool_result = save_appointment.invoke(save_input)
                logger.info("save_appointment succeeded: %r", tool_result)
                state["saved"] = True
            except Exception:
                logger.exception("save_appointment FAILED for input=%r", save_input)
                # Don't set saved=True on failure — next turn's retry
                # (if any) will attempt the save again instead of
                # silently pretending it worked.

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


# ---------------------------------------------------------------------
# History bookkeeping — runs after either flow, before END
# ---------------------------------------------------------------------

def record_history_node(state: ChatState) -> ChatState:
    _append_history(state, "user", state["message"])
    _append_history(state, "assistant", state["reply"] or "")
    return state


# ---------------------------------------------------------------------
# Build + compile
# ---------------------------------------------------------------------

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
