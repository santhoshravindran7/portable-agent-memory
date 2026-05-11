// sse.js — SSE helpers for GitHub Copilot Extension chat responses.

/**
 * Write an SSE content event.
 */
function sendContent(res, body) {
  res.write(`data: ${JSON.stringify({ type: "content", body })}\n\n`);
}

/**
 * Signal the end of the SSE stream.
 */
function sendDone(res) {
  res.write("data: [DONE]\n\n");
}

/**
 * Set up SSE headers on an Express response.
 */
function initSSE(res) {
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
    "X-Accel-Buffering": "no",
  });
}

module.exports = { sendContent, sendDone, initSSE };
