// server.js — Express server for the PAM GitHub Copilot Extension.

const express = require("express");
const { handleChat } = require("./handler");

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// Health check
app.get("/", (_req, res) => {
  res.json({
    name: "portable-agent-memory",
    description: "PAM GitHub Copilot Extension",
    version: "0.1.0",
    status: "ok",
  });
});

// GitHub Copilot Extension chat endpoint
app.post("/api/chat", handleChat);

app.listen(PORT, () => {
  console.log(`🧠 PAM Copilot Extension running on port ${PORT}`);
});

module.exports = app;
