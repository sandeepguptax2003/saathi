export interface SSEMessage {
  event: string;
  data: string;
  id?: string;
}

function parseBlock(block: string): SSEMessage | null {
  let event = "message";
  let id: string | undefined;
  const data: string[] = [];
  let sawField = false;
  for (const line of block.split("\n")) {
    if (line === "" || line.startsWith(":")) continue;
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    sawField = true;
    if (field === "event") event = value;
    else if (field === "data") data.push(value);
    else if (field === "id") id = value;
  }
  if (!sawField) return null;
  return { event, data: data.join("\n"), id };
}

/**
 * Reads a text/event-stream body (works for POST, unlike EventSource).
 * Handles events split across chunks, CRLF line endings, comments and multi-line data.
 */
export async function* readSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<SSEMessage> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = buffer.replace(/\r\n|\r(?!$)/g, "\n");
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const message = parseBlock(buffer.slice(0, boundary));
        buffer = buffer.slice(boundary + 2);
        if (message) yield message;
        boundary = buffer.indexOf("\n\n");
      }
    }
    buffer += decoder.decode();
    const tail = parseBlock(buffer.replace(/\r\n?/g, "\n"));
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}
