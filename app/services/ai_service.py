from app.services.config_loader import load_config
from app.services.gemini_service import GeminiService
from app.utils.parser import extract_name
from app.utils.parser import extract_phone
from app.utils.parser import extract_time


class AIService:

    def __init__(self):
        self.gemini = GeminiService()

    def generate_reply(
        self,
        business_id: str,
        message: str,
        session: dict
    ) -> str:

        config = load_config(business_id)
        message = message.lower().strip()

        # ==================================================
        # CUSTOMER SUPPORT MODE (POGO)
        # ==================================================

        if config["type"] == "customer_support":

            # Greeting
            if message in [
                "hi",
                "hello",
                "hey",
                "good morning",
                "good afternoon",
                "good evening"
            ]:

                return (
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

            # Help
            if any(word in message for word in [
                "help",
                "support",
                "assist"
            ]):

                return (
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

            # Demo
            if any(word in message for word in [
                "demo",
                "book demo",
                "schedule demo",
                "talk to sales",
                "sales"
            ]):

                return (
                    "Certainly.\n\n"
                    "To arrange a personalized product demonstration, please share:\n\n"
                    "• Full Name\n"
                    "• Company Name\n"
                    "• Work Email\n"
                    "• Your research goals\n\n"
                    "A Pogo specialist will contact you shortly."
                )

            # Pricing
            if any(word in message for word in [
                "pricing",
                "price",
                "cost",
                "quote"
            ]):

                return (
                    "Pogo offers customized enterprise pricing based on your research requirements.\n\n"
                    "I'd recommend scheduling a product demo so the sales team can prepare a tailored quotation."
                )

            # Enterprise
            if any(word in message for word in [
                "enterprise",
                "business",
                "organization",
                "company",
                "corporate"
            ]):

                return (
                    "Pogo helps enterprise organizations conduct AI-powered consumer research using verified participant panels, automated interviews, quantitative surveys and research analytics.\n\n"
                    "What would you like to know?"
                )

            # Platform
            if any(word in message for word in [
                "platform",
                "products",
                "product",
                "features",
                "capabilities",
                "what is pogo"
            ]):

                return self.gemini.ask(
                    "Explain Pogo platform, products and capabilities.",
                    business_id
                )

            # AI Interviewer
            if "ai interviewer" in message:

                return self.gemini.ask(
                    "Explain AI Interviewer.",
                    business_id
                )

            # Consumer Panel
            if any(word in message for word in [
                "consumer panel",
                "panel",
                "participants"
            ]):

                return self.gemini.ask(
                    "Explain the verified consumer panel.",
                    business_id
                )

            # Surveys
            if any(word in message for word in [
                "survey",
                "surveys",
                "quant"
            ]):

                return self.gemini.ask(
                    "Explain quantitative surveys.",
                    business_id
                )

            # Case Studies
            if any(word in message for word in [
                "case study",
                "case studies",
                "success story"
            ]):

                return self.gemini.ask(
                    "Show available case studies.",
                    business_id
                )

            # Thanks
            if any(word in message for word in [
                "thanks",
                "thank you"
            ]):

                return (
                    "You're welcome!\n\n"
                    "If you'd like, I can also explain Pogo's platform, research capabilities, or help you request a product demo."
                )

            # Goodbye
            if any(word in message for word in [
                "bye",
                "goodbye",
                "see you"
            ]):

                return (
                    "Thank you for visiting Pogo.\n\n"
                    "Have a wonderful day!"
                )

            # Everything else goes to Gemini
            return self.gemini.ask(message, business_id)

        
        # ==================================================
        # BOOKING MODE (SALON)
        # ==================================================

        # Continue collecting booking details
        if session["step"] == "awaiting_name":

            name = extract_name(message)

            if name:
                session["name"] = name
            else:
                return "Sorry, I couldn't understand your name. Could you please tell me your name again?"

            session["step"] = "awaiting_phone"

            return (
                f"Nice to meet you, {session['name']}.\n\n"
                "May I have your 10-digit mobile number?"
            )


        if session["step"] == "awaiting_phone":

            phone = extract_phone(message)

            if phone:
                session["phone"] = phone
            else:
                return "Please enter a valid 10-digit mobile number."

            session["step"] = "awaiting_date"

            return (
                "Thank you.\n\n"
                "Which date would you like to book your appointment?"
            )


        if session["step"] == "awaiting_date":

            session["date"] = message
            session["step"] = "awaiting_time"

            return (
                "Great.\n\n"
                "time please?"
            )


        if session["step"] == "awaiting_time":

            time = extract_time(message)

            if time:
                session["time"] = time
            else:
                return "Please enter a valid time (example: 10 AM, 2 PM, 6:30 PM)."

            session["step"] = None

            return (
                "✅ Appointment request received.\n\n"
                f"Name: {session['name']}\n"
                f"Phone: {session['phone']}\n"
                f"Date: {session['date']}\n"
                f"Time: {session['time']}\n\n"
                "Our salon team will contact you shortly for confirmation.\n\n"
                "Have a nice day!"
            )


        # Appointment booking trigger words
        booking_words = [
            "appointment",
            "book",
            "booking",
            "schedule",
            "reserve",
            "visit",
            "slot"
        ]

        if any(word in message for word in booking_words):

            session["step"] = "awaiting_name"

            return (
                "Certainly! I can help you book an appointment.\n\n"
                "May I know your full name?"
            )


        # Normal salon information questions
        salon_info_words = [
            "service",
            "services",
            "price",
            "pricing",
            "cost",
            "charge",
            "haircut",
            "hair",
            "hairstyle",
            "hair spa",
            "facial",
            "cleanup",
            "makeup",
            "bridal",
            "threading",
            "waxing",
            "manicure",
            "pedicure",
            "timing",
            "hours",
            "open",
            "closed",
            "location",
            "address"
        ]

        if any(word in message for word in salon_info_words):

            return self.gemini.ask(
                message,
                business_id
            )


        # Greeting
        if message in [
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening"
        ]:

            return (
                "Hello! Welcome to NAXBOT AI.\n\n"
                "I can help you with salon services, pricing information, "
                "and appointment bookings."
            )


        # Final fallback
        return config["fallback_reply"]      
