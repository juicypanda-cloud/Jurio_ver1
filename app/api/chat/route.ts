import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export const runtime = "nodejs";

// Fetch dynamic agent settings from Supabase
async function loadAgentSettings() {
  const { data, error } = await supabase
    .from("agent_settings")
    .select("*")
    .single();

  if (error) throw new Error("Failed to load agent settings: " + error.message);
  return data;
}

async function embedOpenAI(text: string) {
  const res = await fetch("https://api.openai.com/v1/embeddings", {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}` 
    },
    body: JSON.stringify({ 
      model: process.env.EMBEDDING_MODEL || "text-embedding-3-small",
      input: text 
    }),
  });

  if (!res.ok) throw new Error(await res.text());
  const j = await res.json();
  return j.data[0].embedding;
}

async function loadJsonText(bucket: string, path: string) {
  const { data, error } = await supabase.storage.from(bucket).download(path);
  if (error) throw new Error(`Could not load ${path}: ${error.message}`);

  const raw = Buffer.from(await data.arrayBuffer()).toString("utf-8");

  try {
    return JSON.parse(raw).text || "";
  } catch {
    return raw;
  }
}

export async function POST(req: Request) {
  try {
    const { question } = await req.json();
    if (!question)
      return NextResponse.json({ error: "No question" }, { status: 400 });

    // 1) Load agent settings
    const settings = await loadAgentSettings();
    const SYSTEM_PROMPT = settings.system_prompt || "You are Jurio, a Mongolian legal assistant.";
    const TOP_K = settings.top_k || 6;
    const TEMP = settings.temperature || 0.0;

    // 2) Embed question
    const queryEmb = await embedOpenAI(question);

    // 3) Search for matching chunks
    const { data: rows, error } = await supabase.rpc("match_documents", {
      query_embedding: queryEmb,
      match_count: TOP_K,
    });

    if (error) throw error;

    const bucket = process.env.SUPABASE_BUCKET_TEXTS || "texts";
    const chunks: any[] = [];

    for (const r of rows) {
      const batch = r.batch_id || "";
      const m = batch.match(/\d+/);
      const n = m ? Number(m[0]) : null;
      if (n === null) continue;

      let fileText = "";
      let sourcePath = "";

      const docPath = `legalinfo/doc_${n}.json`;
      const casePath = `shuukh/case_${n}.json`;

      try {
        fileText = await loadJsonText(bucket, docPath);
        sourcePath = docPath;
      } catch {
        try {
          fileText = await loadJsonText(bucket, casePath);
          sourcePath = casePath;
        } catch {
          continue;
        }
      }

      const fragment = fileText.slice(r.start, r.end);

      chunks.push({
        text: fragment,
        source: sourcePath,
        start: r.start,
        end: r.end,
      });
    }

    // Build RAG context
    let context = "";
    chunks.forEach((c) => {
      context += `SOURCE: ${c.source} [${c.start}-${c.end}]\n${c.text}\n\n`;
    });

    // 5) Generate answer
    const aiRes = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: process.env.CHAT_MODEL || "gpt-4o-mini",
        temperature: TEMP,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: `Question: ${question}\n\nContext:\n${context}` }
        ],
      }),
    });

    const result = await aiRes.json();
    const answer = result.choices?.[0]?.message?.content || "";

    return NextResponse.json({
      answer,
      sources: chunks,
      used_settings: {
        system_prompt: SYSTEM_PROMPT,
        temperature: TEMP,
        top_k: TOP_K,
      },
    });

  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || String(err) },
      { status: 500 }
    );
  }
}