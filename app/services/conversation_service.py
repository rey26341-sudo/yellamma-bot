class ConversationService:

    def __init__(self):
        self.sessions = {}

    def get_session(self, user_id: str):

        if user_id not in self.sessions:

            self.sessions[user_id] = {
                "business_id": None,
                "step": None,
                "name": None,
                "phone": None,
                "service": None,
                "date": None,
                "time": None,
                "saved": False
            }

        return self.sessions[user_id]
