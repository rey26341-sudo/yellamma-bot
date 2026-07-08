import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

knowledge = """
Pogo is an AI-powered consumer research company.

It combines verified behavioral data with AI-powered research.

Funding: $32M.

Panel size: 3M+ verified U.S. consumers.

Products:

- Audience Builder
- AI Interviewer
- Quant Surveys
- AI Research Agent

Answer ONLY from this information.
"""

question = "What is Pogo?"

prompt = f"""
You are an AI customer support assistant.

Knowledge:

{knowledge}

User Question:
{question}
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt
)

print(response.text)
