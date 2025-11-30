/* eslint-disable */
/* eslint-disable @next/next/no-server-import-in-page */
export const runtime = "nodejs";
// @ts-nocheck

import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import * as zlib from "zlib";

// ===== ENV =====
const SUPABASE_URL = process.env.SUPABASE_URL!;
const SUPABASE_KEY =
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY!;
const OPENAI_KEY = process.env.OPENAI_API_KEY!;
const OPENAI_MODEL = process.env.OPENAI_MODEL || "gpt-4o-mini";

if (!SUPABASE_URL || !SUPABASE_KEY || !OPENAI_KEY) {
  console.error("Missing SUPABASE_URL / SUPABASE_KEY / OPENAI_API_KEY");
}

// ===== HELPERS =====

async function downloadAndDecompressBatch(
  batchId: string
): Promise<Buffer> {
  const url = `${SUPABASE_URL}/storage/v1/object/chunks/${batchId}.gz`;

  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${SUPABASE_KEY}` },
  });

  if (!res.ok) {
    throw new Error(
      `Failed to download ${batchId}.gz: ${res.status} ${await res.text()}`
    );
  }

  const gz = Buffer.from(await res.arrayBuffer());
  const raw = zlib.gunzipSync(gz);
  return raw;
}

async function ensureBatchBuffers(
  mappings: { batch_id: string; start: number; end: number }[]
) {
  const cache = new Map<string, Buffer>();

  for (const m of mappings) {
    if (!cache.has(m.batch_id)) {
      const buf = await downloadAndDecompressBatch(m.batch_id);
      cache.set(m.batch_id, buf);
    }
  }
  return cache;
}

function sliceTextFromBuffer(
  buf: Buffer,
  start: number,
  end: number
): string {
  const slice = buf.slice(start, end + 1);
  return slice.toString("utf-8");
}

// ===== MAIN ROUTE =====

export async function POST(req: Request) {
  try {
    const { question, top_k = 5 } = await req.json();

    if (!question) {
      return NextResponse.json(
        { error: "Missing 'question' field" },
        { status: 400 }
      );
    }

    // === 1. Embed query ===
    const embRes = await fetch(
      "https://api.openai.com/v1/embeddings",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${OPENAI_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model:
            process.env.OPENAI_EMBEDDING_MODEL ||
            "text-embedding-3-small",
          input: question,
        }),
      }
    );

    if (!embRes.ok) {
      throw new Error(`Embedding error: ${await embRes.text()}`);
    }

    const embJson = await embRes.json();
    const queryEmbedding = embJson.data?.[0]?.embedding;

    if (!queryEmbedding) {
      throw new Error("No embedding returned");
    }

    // === 2. Vector search using match_documents RPC ===
    const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

    const rpcRes = await supabase
      .rpc("match_documents", {
        query_embedding: queryEmbedding,
        match_count: top_k,
      })
      .select()
      .limit(top_k);

    let matches: any[] = [];

    if ("error" in rpcRes && rpcRes.error) {
      throw new Error(
        "RPC error: " + JSON.stringify(rpcRes.error)
      );
    } else if (Array.isArray(rpcRes.data)) {
      matches = rpcRes.data;
    } else if (Array.isArray(rpcRes)) {
      matches = rpcRes;
    } else if (rpcRes.data) {
      matches = rpcRes.data;
    }

    if (!matches.length) {
      throw new Error(
        "No vector matches returned — check match_documents RPC."
      );
    }

    const mappings = matches.map((m: any) => ({
      batch_id: m.batch_id,
      start: Number(m.start),
      end: Number(m.end),
      chunk_id: m.chunk_id,
    }));

    // === 3. Download required batches once ===
    const batchBuffers = await ensureBatchBuffers(mappings);

    // === 4. Extract and merge chunks ===
    const snippets = mappings.map((m) => {
      const buf = batchBuffers.get(m.batch_id);
      const txt = sliceTextFromBuffer(buf, m.start, m.end);
      return { chunk_id: m.chunk_id, text: txt };
    });

    const contextText = snippets
      .map((s) => `--- ${s.chunk_id} ---\n${s.text}`)
      .join("\n\n");

    // === 5. Final answer from GPT ===
    const systemPrompt =
      "You are Jurio, a Mongolian legal AI. Use the legal context to answer precisely. Cite chunk_ids.";

    const chatRes = await fetch(
      "https://api.openai.com/v1/chat/completions",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${OPENAI_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: OPENAI_MODEL,
          temperature: 0.1,
          max_tokens: 800,
          messages: [
            { role: "system", content: systemPrompt },
            {
              role: "user",
              content: `Question: ${question}\n\nContext:\n${contextText}`,
            },
          ],
        }),
      }
    );

    if (!chatRes.ok) {
      throw new Error(`Chat error: ${await chatRes.text()}`);
    }

    const chatJson = await chatRes.json();
    const answer =
      chatJson.choices?.[0]?.message?.content || "";

    return NextResponse.json({
      answer,
      sources: snippets.map((s) => s.chunk_id),
    });
  } catch (err: any) {
    console.error("Agent error:", err);
    return NextResponse.json(
      { error: String(err) },
      { status: 500 }
    );
  }
}
