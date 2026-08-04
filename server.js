const express = require("express");
const path = require("path");

const app = express();
const API_BASE_URL = process.env.API_BASE_URL || "http://127.0.0.1:8001";

app.use(express.json());

// Serve files from the frontend folder
app.use(express.static(path.join(__dirname, "frontend")));

app.post("/chat", async (req, res) => {
  try {
    const upstreamResponse = await fetch(`${API_BASE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(req.body || {})
    });

    const responseText = await upstreamResponse.text();
    res.status(upstreamResponse.status);
    res.set("Content-Type", upstreamResponse.headers.get("content-type") || "application/json");
    res.send(responseText);
  } catch (error) {
    res.status(502).json({
      detail: "Unable to reach the backend chat API. Start the FastAPI service on port 8001 and try again."
    });
  }
});

const VERIFY_TOKEN = "yellamma_verify_123";

// Yellamma AI homepage
app.get("/", (req, res) => {
res.sendFile(path.join(__dirname, "frontend", "index.html"));
});

// Salon AI demo page
app.get("/salon", (req, res) => {
res.sendFile(path.join(__dirname, "frontend", "salon.html"));
});

// WhatsApp webhook verification
app.get("/webhook", (req, res) => {
const mode = req.query["hub.mode"];
const token = req.query["hub.verify_token"];
const challenge = req.query["hub.challenge"];

if (mode === "subscribe" && token === VERIFY_TOKEN) {
return res.status(200).send(challenge);
}

return res.sendStatus(403);
});

// WhatsApp incoming messages
app.post("/webhook", (req, res) => {
console.log("MESSAGE:", req.body);
res.sendStatus(200);
});

app.listen(3000, () => {
console.log("Yellamma website running at http://127.0.0.1:3000");
});

