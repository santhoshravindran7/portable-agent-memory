// api/chat.js — Vercel serverless function for the PAM GitHub Copilot Extension.
// This is the alternative deployment path for Vercel (one-click deploy).

const { handleChat } = require("../handler");

module.exports = async function (req, res) {
  if (req.method === "GET") {
    return res.status(200).json({
      name: "portable-agent-memory",
      description: "PAM GitHub Copilot Extension",
      version: "0.1.0",
      status: "ok",
    });
  }

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  return handleChat(req, res);
};
