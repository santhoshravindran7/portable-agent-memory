// server.js — Express server for the PAM GitHub Copilot Extension.

const express = require("express");
const crypto = require("crypto");
const { handleChat } = require("./handler");

const app = express();
const PORT = process.env.PORT || 3000;
const APP_SECRET = process.env.GITHUB_APP_SECRET;

app.use(express.json());

// --- Rate limiting ---
const rateLimit = new Map();
const RATE_LIMIT = 60; // requests per minute

function rateLimiter(req, res, next) {
  const key = req.headers["x-github-user"] || req.ip;
  const now = Date.now();
  const window = rateLimit.get(key) || { count: 0, reset: now + 60000 };
  if (now > window.reset) {
    window.count = 0;
    window.reset = now + 60000;
  }
  window.count++;
  rateLimit.set(key, window);
  if (window.count > RATE_LIMIT) {
    return res.status(429).json({ error: "Rate limit exceeded" });
  }
  next();
}

// --- Signature verification ---
function verifySignature(req, res, next) {
  if (!APP_SECRET) {
    console.warn("WARNING: GITHUB_APP_SECRET not set — skipping request signature verification");
    return next();
  }
  const signature = req.headers["x-hub-signature-256"];
  if (!signature) {
    return res.status(401).json({ error: "Missing signature" });
  }
  const body = JSON.stringify(req.body);
  const expected = "sha256=" + crypto.createHmac("sha256", APP_SECRET).update(body).digest("hex");
  if (!crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) {
    return res.status(401).json({ error: "Invalid signature" });
  }
  next();
}

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
app.post("/api/chat", rateLimiter, verifySignature, handleChat);

app.listen(PORT, () => {
  console.log(`🧠 PAM Copilot Extension running on port ${PORT}`);
});

module.exports = app;
