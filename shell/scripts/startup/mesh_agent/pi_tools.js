// SPDX-FileCopyrightText: 2026 Cadex Authors
//
// SPDX-License-Identifier: GPL-2.0-or-later

// Pi extension that exposes Mesh's Blender tools to the pi coding agent.
//
// This is the non-MCP transport (ADR-175): pi does not speak MCP by design,
// but its extension API registers tools natively. The seam is the same TCP
// bridge `mcp_shim.py` uses — this file is the shim's sibling, one protocol
// hop shorter. Loaded by `backend.PiBackend` via `pi -e pi_tools.js`; the
// bridge's address arrives in MESH_BRIDGE_PORT / MESH_BRIDGE_TOKEN because
// pi has no per-extension argv.
//
// Only node built-ins are used, so nothing has to be installed next to it.
// The tool `parameters` are the bridge's JSON Schemas passed through raw —
// pi accepts plain JSON Schema (verified against pi 0.84.4).

import net from "node:net";

function bridgeRequest(payload) {
  const port = Number(process.env.MESH_BRIDGE_PORT);
  const token = process.env.MESH_BRIDGE_TOKEN || "";
  return new Promise((resolve, reject) => {
    const sock = net.createConnection({ host: "127.0.0.1", port }, () => {
      sock.write(JSON.stringify({ ...payload, token }) + "\n");
    });
    let buf = "";
    sock.on("data", (chunk) => {
      buf += chunk.toString("utf-8");
      if (buf.endsWith("\n")) {
        sock.end();
        try {
          resolve(JSON.parse(buf));
        } catch (err) {
          reject(err);
        }
      }
    });
    sock.on("error", reject);
    // The bridge answers when Blender's main thread has run the tool; a
    // rebuild can be minutes. Same ceiling as the bridge's own socket.
    sock.setTimeout(600000, () => {
      sock.destroy();
      reject(new Error("Mesh bridge timeout"));
    });
  });
}

// The bridge speaks MCP content shapes; pi wants Anthropic-style ones.
function toPiContent(blocks) {
  return (blocks || []).map((block) => {
    if (block && block.type === "image" && block.data) {
      return {
        type: "image",
        source: {
          type: "base64",
          mediaType: block.mimeType || "image/png",
          data: block.data,
        },
      };
    }
    return block;
  });
}

export default async function (pi) {
  const reply = await bridgeRequest({ op: "list_tools" });
  for (const tool of reply.tools) {
    pi.registerTool({
      name: tool.name,
      label: tool.name,
      description: tool.description,
      parameters: tool.input_schema,
      async execute(_toolCallId, params) {
        const result = await bridgeRequest({
          op: "call",
          tool: tool.name,
          input: params || {},
        });
        if (result.is_error) {
          const text = (result.content || [])
            .filter((block) => block.type === "text")
            .map((block) => block.text)
            .join("\n");
          throw new Error(text || "The Mesh tool reported an error.");
        }
        return { content: toPiContent(result.content), details: {} };
      },
    });
  }
}
