# 🤖 Yellamma AI Receptionist

**Your AI Receptionist For Every Business**

Yellamma is an AI-powered virtual receptionist platform that helps businesses answer customer enquiries, share service/pricing information, and book appointments — automatically, 24/7. It's built as a multi-tenant chatbot backend (one deployment, many businesses via a `business_id`) with a lightweight web chat widget and a demo landing page.

> Help customers, answer enquiries, and automate conversations 24/7.

I identified a problem faced by small businesses — repetitive customer enquiries and appointment requests — and designed a configurable AI assistant where the same backend supports different industries by swapping business workflows. I own the backend, frontend, deployment, configuration, and automation workflows end-to-end.

## Why LangGraph?

Traditional chatbots send every message independently to the LLM.

Yellamma uses LangGraph to model conversations as a state machine. Customer details collected during the booking flow are preserved across multiple turns, allowing the assistant to complete bookings reliably before writing them to PostgreSQL.

This architecture provides a foundation for future RAG, tool calling, and multi-agent workflows.

---

## 🚦 Current Status

**The LangGraph-powered appointment flow is working and verified.**

The chatbot has been upgraded from the earlier, simpler rule-based flow to a **LangChain + LangGraph** conversation engine. It now collects appointment details step by step, preserves that information across the whole conversation (using graph state instead of stateless prompting), and writes the finished booking to the real production database.

### ✅ Verified working

- Conversational, multi-turn appointment booking
- Step-by-step collection of customer name, phone number, appointment date, and time
- Conversation memory persisted across the entire booking flow (via LangGraph state)
- LangGraph manages conversation state while LangChain provides LLM integration.
- Saving completed appointments to the production application database
- Required database fields for `business_id` and `service` are captured and stored

<img width="1917" height="402" alt="image" src="https://github.com/user-attachments/assets/a5e13f2c-9660-4c59-8750-8488c2130f10" />


### 🧪 Latest verification

An end-to-end test completed successfully, with the following appointment saved to the database:

| ID | Customer | Phone | Date | Time |
|----|-----------|-------------|-------------|------|
| 8 | Renganayaki | 9876543210 | next monday | 2 PM |

This confirms the full path is working: **conversation → remembered details → database booking**, with the run completing without errors.

### 🔧 What was fixed during the LangGraph migration

1. Resolved setup issues such as missing folders and an incorrect active Python environment.
2. Corrected the database path so bookings are written to the intended application database (not a stray/local one).
3. Updated the existing database schema with the missing `business_id` and `service` columns.
4. Confirmed a real appointment can now be created successfully end-to-end through the new chatbot flow.

---

## ✨ Features

- **Conversational AI receptionist** powered by Google Gemini, with natural, context-aware replies.
- **Stateful AI workflow powered by LangGraph** — LangChain + LangGraph manage multi-turn dialogue state, so details collected earlier in the chat (name, phone, date) are never lost as the conversation continues.
- **Multi-business support** — a single API instance serves multiple businesses, distinguished by a `business_id` (e.g. `salon`, `pogo`).
- **Appointment booking flow** — collects the customer's name, phone number, preferred date, time, and service, then confirms the request and persists it to the database:
  ```
  ✅ Appointment request received.
  Name: Kirishanth
  Phone: 45678935
  Date: next week
  Time: evening
  Our staff will contact you shortly.
  ```
- **Service & FAQ answering** — responds to natural-language questions like *"salon services?"* or *"facial and threading"* with relevant, formatted answers.
- **Persistent bookings** — completed bookings are written to PostgreSQL, including the `business_id` and `service` fields required for multi-tenant reporting.
- **Simple REST API** (`POST /chat`) that's easy to integrate into any website, WhatsApp bot, or messaging platform.
- **Interactive API docs** via Swagger UI (auto-generated from FastAPI).
- **Web chat demo widget** for trying the receptionist directly in the browser.
- **Landing/demo page** showcasing AI solutions across industries: **Salon**, **Healthcare**, and **Export**.
- **Dockerized** for one-command local setup, with public demo sharing via Cloudflare Tunnel.

---

## 🏗️ Architecture Diagram

The diagram below shows how a message flows from a customer through the multi-tenant API into the LangGraph-orchestrated conversation AI Agent layer, and how a completed booking is persisted.

```mermaid
flowchart TD
    subgraph Client["Client Surfaces"]
        A1[Web Chat Widget]
        A2[Landing / Demo Page]
        A3[Future: WhatsApp / Telegram]
    end

    subgraph API["FastAPI Backend (yellamma-api)"]
        B1["/chat endpoint\n(chat.py)"]
        B2["/appointments endpoints\n(appointments.py)"]
        B3["Config Loader\n(config_loader.py)\nresolves business_id → JSON profile"]
    end

    subgraph Brain["Conversation Engine"]
        C1["Conversation Service\n(conversation_service.py)"]
        C2["LangGraph State Machine\n- collect name\n- collect phone\n- collect date\n- collect time\n- collect service\n- confirm booking"]
        C3["LangChain Orchestration Layer"]
        C4["Gemini Service\n(gemini_service.py)\ncalls Google Gemini API"]
    end

    subgraph Data["Persistence"]
        D1["Booking Service\n(booking_service.py /\nappointment_service.py)"]
        D2[("PostgreSQL\nyellamma-db")]
        D3["Per-business configs\n(configs/*.json)"]
        D4["Per-client knowledge & prompts\n(clients/*/knowledge.md, prompts.md)"]
    end

    subgraph Planned["Planned (Roadmap)"]
        E1["Qdrant\nDocument / FAQ retrieval"]
        E2["Multi-agent layer\n(specialized agents)"]
    end

    A1 --> B1
    A2 --> B1
    A3 -.future.-> B1

    B1 --> B3
    B3 --> D3
    B1 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 -->|Gemini response| C1
    C1 --> D4

    C2 -->|all fields collected| D1
    D1 --> D2
    B2 --> D2

    C2 -.future retrieval.-> E1
    C1 -.future.-> E2

    style Planned stroke-dasharray: 5 5
```

**How a request flows, step by step:**

1. A customer sends a message from the **web chat widget**, the **landing page demo**, or (in future) **WhatsApp/Telegram**.
2. The message hits `POST /chat` along with a `business_id`.
3. The **Config Loader** resolves which business profile to use — pulling branding, FAQs, flows, and prompts specific to that tenant (e.g. `salon.json` vs `pogo.json`).
4. The **Conversation Service** hands the message and current state to the **LangGraph state machine**, which tracks exactly where the customer is in the booking flow (name → phone → date → time → service → confirm) and remembers everything collected so far.
5. **LangChain** orchestrates the prompt construction and tool calls; the **Gemini Service** calls the Google Gemini API to generate the natural-language reply.
6. Once every required field has been collected, the **Booking Service** writes the finished appointment — including the mandatory `business_id` and `service` columns — to **PostgreSQL**.
7. Planned components (dashed box): **Qdrant** for document/FAQ retrieval so the bot can answer from real business documents, and a **multi-agent layer** to split responsibilities (e.g. a booking agent vs. an FAQ agent vs. a follow-up agent).

---

## 📁 Project Structure

```
yellamma-bot/
├── app/                          # FastAPI backend
│   ├── main.py                   # App entrypoint
│   ├── api/
│   │   └── routes/
│   │       ├── chat.py           # POST /chat — main conversation endpoint
│   │       └── appointments.py   # Appointment-related endpoints
│   ├── configs/                  # Per-business config profiles
│   │   ├── salon.json
│   │   ├── pogo.json
│   │   ├── fashion_shop.json
│   │   ├── import_export.json
│   │   └── real_estate.json
│   ├── core/                     # Core app settings/utilities
│   ├── database/
│   │   └── database.py           # DB connection/session setup
│   ├── models/
│   │   └── appointment.py        # SQLAlchemy models (now incl. business_id, service)
│   ├── schemas/
│   │   ├── app.py
│   │   └── chat.py                # Pydantic request/response schemas
│   ├── services/
│   │   ├── ai_service.py          # AI orchestration layer
│   │   ├── gemini_service.py      # Google Gemini integration
│   │   ├── conversation_service.py# Talks to the LangGraph state machine
│   │   ├── graph_service.py        # ⭐ NEW: LangGraph flow definition & state
│   │   ├── appointment_service.py
│   │   ├── booking_service.py     # Persists completed bookings to Postgres
│   │   └── config_loader.py       # Loads per-business JSON configs
│   └── utils/
│       └── parser.py              # Message/date/time parsing helpers
│
├── clients/                      # Business-specific knowledge & prompts
│   ├── salon/
│   │   └── knowledge.md
│   └── pogo/
│       ├── branding.json
│       ├── company.json
│       ├── faqs.json
│       ├── flows.json
│       ├── knowledge.md
│       └── prompts.md
│
├── frontend/                     # Demo web chat UI
│   ├── css/
│   ├── js/
│   ├── images/
│   ├── index.html
│   └── salon.html
│
├── static/
│   └── index.html                # Served static demo page
│
├── docs/                         # Additional documentation
├── tests/                        # Test suite
├── test_gemini.py                # Standalone Gemini API test script
│
├── server.js                     # Node/Express server (auxiliary service)
├── package.json
├── package-lock.json
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt              # Python dependencies (now incl. langchain, langgraph)
├── PROJECT_ROADMAP.md
└── README.md
```

> **Note:** `graph_service.py` is new since the LangGraph migration and is where the conversation state machine (name → phone → date → time → service → confirm) is defined. Adjust the exact filename/location to match your actual repo if it differs — this reflects the described upgrade layered onto the previously documented structure.
>
> The repo contains both a Python/FastAPI backend (`app/`) and a small Node/Express server (`server.js`). `node_modules/` and `venv/` are local dependency folders and aren't tracked in version control (add them to `.gitignore` if not already).

---

## 🏗️ Tech Stack

| Layer                | Technology                                        |
|-----------------------|----------------------------------------------------|
| Backend API           | Python 3.12, FastAPI, Uvicorn                      |
| Conversation Engine   | LangChain + LangGraph (stateful multi-turn flows)  |
| AI / LLM              | Google Gemini API (`google-genai`)                 |
| Database               | PostgreSQL (via Docker container `yellamma-db`)    |
| Containerization       | Docker & Docker Compose                            |
| Frontend (demo)        | HTML / JavaScript chat widget                       |
| Tunneling               | Cloudflare Tunnel (`trycloudflare.com`)            |
| Planned: Retrieval     | Qdrant (document / FAQ search)                     |
| Planned: Messaging     | WhatsApp / Telegram integration                    |

---

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) & Docker Compose
- A [Google AI Studio](https://aistudio.google.com/) API key (for Gemini)

### 1. Clone the repository

```bash
git clone https://github.com/rey26341-sudo/yellamma-bot.git
cd yellamma-bot
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
DATABASE_URL=postgresql://user:password@yellamma-db:5432/yellamma
```

### 3. Run with Docker Compose

```bash
docker compose up --build
```

This will build and start two containers:

| Container        | Purpose                     |
|-------------------|------------------------------|
| `yellamma-api`    | FastAPI backend (port `8001`) |
| `yellamma-db`     | PostgreSQL database          |

Once running, the API will be available at:

```
http://127.0.0.1:8001
```

> **Note:** If you see `ModuleNotFoundError: No module named 'google'`, make sure `google-genai` is listed in `requirements.txt` and rebuild the image with `docker compose up --build`. Similarly, ensure `langchain` and `langgraph` are listed for the new conversation engine.

### 4. Explore the API docs

FastAPI auto-generates interactive Swagger docs:

```
http://localhost:8001/docs
```

---

## 💬 Using the Chat API

**Endpoint:** `POST /chat`

**Request body:**

```json
{
  "business_id": "salon",
  "message": "What services do you offer?"
}
```

**Response:**

```json
{
  "reply": "Welcome to Naturals Demo Salon! Our services include:\n* Hair cuts and styling\n* Hair spa\n* Facials and cleanups\n* Threading and waxing\n* Manicure and pedicure\n* Bridal and party makeup\n\nWhich of these services are you interested in learning more about?"
}
```

### Example: cURL

```bash
curl -X POST http://127.0.0.1:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"business_id":"salon","message":"book appointment"}'
```

### Example conversation flow (appointment booking, LangGraph-driven)

| Step | User message | Bot reply | Graph State Update |
|------|----------------|-----------|----------------------|
| 1 | `book appointment` | "May I know your full name?" | enters `collect_name` node |
| 2 | `Renganayaki` | "May I have your 10-digit mobile number?" | `name` stored, moves to `collect_phone` |
| 3 | `9876543210` | "Which date would you like to book your appointment?" | `phone` stored, moves to `collect_date` |
| 4 | `next monday` | "What time works best for you?" | `date` stored, moves to `collect_time` |
| 5 | `2 PM` | ✅ Appointment request received & confirmed | `time` stored → all fields present → booking written to Postgres |

---

## 🖥️ Web Chat Widget (Demo)

A minimal HTML/JS chat widget is included for testing the receptionist in-browser:

```
http://127.0.0.1:5500
```

Simply type a message in the input box and press **Send** — the widget calls the `/chat` API and displays the AI's response in real time, with the LangGraph engine keeping track of the conversation behind the scenes.

---

## 🌐 Landing Page

A demo landing page (`localhost:3000`) introduces the product and lets visitors try a live demo:

- **Salon** — Appointments, services, pricing enquiries
- **Healthcare** — Patient assistance and information
- **Export** — Product and customer enquiries

Click **"Try Salon Demo"** to interact with the salon receptionist directly.

---

## 🌍 Sharing a Public Demo

For quick demos without deploying to a server, expose your local API using a Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://localhost:8001
```

This generates a public URL (e.g. `https://your-tunnel-name.trycloudflare.com`) that proxies requests to your local instance — useful for sharing a live demo link with clients or teammates.

---

**Added production security features** 

Async SQLAlchemy
PostgreSQL-first design
No silent SQLite fallback in production
TLS requirement for external PostgreSQL
Connection pooling
Statement timeout
No DB URL logging
Async session management










## 🛣️ Roadmap

- [x] LangGraph/LangChain-based conversation engine with persistent multi-turn state
- [x] End-to-end appointment booking saved to the production database - postgreSQL
- [ ] WhatsApp / Telegram integration
- [ ] Document search / knowledge retrieval using Qdrant
- [ ] Admin dashboard for managing businesses and appointments
- [ ] Multi-language support
- [ ] Voice input/output support
- [ ] Multi-agent architecture with specialized agents (booking agent, FAQ agent, follow-up agent)
      

## 🎯 Project Direction

The core booking brain — built on LangGraph and verified end-to-end — is complete. The next phase builds on this foundation: connect it to WhatsApp, give it access to business documents and FAQs through Qdrant, and gradually introduce specialized agents where they provide clear value.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/rey26341-sudo/yellamma-bot/issues).

---

## 📄 License

This project is currently unlicensed. Add a `LICENSE` file to specify usage terms.

  




proof of works:
<img width="1920" height="1020" alt="Screenshot 2026-06-24 175735" src="https://github.com/user-attachments/assets/ed93e016-b938-40f3-a36f-6e8b95382954" />
<img width="1920" height="1020" alt="Screenshot 2026-06-27 232756" src="https://github.com/user-attachments/assets/be87319a-a4da-4e8d-8b18-f12c1c7eb73e" />
<img width="1920" height="1020" alt="Screenshot 2026-06-27 233754" src="https://github.com/user-attachments/assets/6938bffa-1b67-415e-85dd-7569129ee62a" />
<img width="1920" height="1020" alt="Screenshot 2026-06-28 090036" src="https://github.com/user-attachments/assets/95678375-8d22-4fe3-b275-7d4394ac19fb" />
<img width="1920" height="1020" alt="Screenshot 2026-06-28 193016" src="https://github.com/user-attachments/assets/fd77f642-12a2-4a83-9c5c-5d6387dd47f7" />
<img width="1899" height="970" alt="Screenshot 2026-06-28 194414" src="https://github.com/user-attachments/assets/03f59670-d254-4b01-8a8a-cb9ff2ccdee9" />
<img width="1920" height="1080" alt="Screenshot 2026-06-29 124337" src="https://github.com/user-attachments/assets/f8caa3a2-8c0c-4ccb-9051-e265dc6f83ae" />
<img width="1920" height="1080" alt="Screenshot 2026-06-29 132953" src="https://github.com/user-attachments/assets/ac49a9e8-2ee0-49a6-a3e3-6044b1de1956" />
<img width="1920" height="1080" alt="Screenshot 2026-06-29 154853" src="https://github.com/user-attachments/assets/8ed0ced0-49ce-49bd-bf36-8305685beaf5" />
<img width="1920" height="1020" alt="Screenshot 2026-06-29 162223" src="https://github.com/user-attachments/assets/cde5e420-f2e8-4c96-841d-cb029772cd45" />
<img width="1920" height="1020" alt="Screenshot 2026-06-29 164002" src="https://github.com/user-attachments/assets/2739ab7f-0659-45f4-821b-33bb35a54f43" />
<img width="1920" height="1020" alt="Screenshot 2026-07-08 173332" src="https://github.com/user-attachments/assets/b979a1ae-ab20-4372-a556-feb0631a8ae3" />
<img width="1920" height="1020" alt="Screenshot 2026-07-03 141847" src="https://github.com/user-attachments/assets/de2a74e8-8f1e-4806-b60d-edfe0b705e83" />
<img width="1920" height="1020" alt="Screenshot 2026-07-03 141818" src="https://github.com/user-attachments/assets/2494c350-f6f0-4015-bf55-cb3db094b411" />
<img width="1920" height="1020" alt="Screenshot 2026-07-08 120921" src="https://github.com/user-attachments/assets/42176d16-1ab6-4535-8957-c17647e8ac31" />
<img width="1920" height="1020" alt="Screenshot 2026-07-08 183358" src="https://github.com/user-attachments/assets/4ca7f59e-f916-4baa-bcf4-ce1f853e400c" />
<img width="1920" height="1020" alt="Screenshot 2026-07-07 223820" src="https://github.com/user-attachments/assets/cb980b2e-c3b2-44f8-bcd3-caa84c254993" />
<img width="1920" height="1020" alt="Screenshot 2026-07-08 082229" src="https://github.com/user-attachments/assets/6a5976be-0b31-40c1-a12d-c7deb5cddcce" />

