const express = require("express");

const app = express();
app.use(express.json());

const VERIFY_TOKEN = "yellamma_verify_123";

app.get("/webhook", (req, res) => {
  const mode = req.query["hub.mode"];
  const token = req.query["hub.verify_token"];
  const challenge = req.query["hub.challenge"];

  if (mode === "subscribe" && token === VERIFY_TOKEN) {
    return res.status(200).send(challenge);
  }

  return res.sendStatus(403);
});

app.post("/webhook", (req, res) => {
  console.log("MESSAGE:", req.body);
  res.sendStatus(200);
});

app.listen(3000, () => {
  console.log("Yellamma bot running on port 3000");
});
