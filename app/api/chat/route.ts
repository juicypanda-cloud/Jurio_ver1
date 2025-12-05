import { NextResponse } from "next/server";
import { supabase } from "@/lib/supabase";

export const runtime = "nodejs";

async function embedOpenAI(text: string) {
  const res = await fetch("https://api.openai.com/v1/embeddings", {
    method: "POST",
    headers: { 
      "Content-Type": "application/json",
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}` 
    },
    body: JSON.stringify({ model: "text-embedding-3-small", input: text }),
  });

  if (!res.ok) throw new Error(await res.text());

  const j = await res.json();
  return j.data[0].embedding;
}

async function loadJsonText(bucket: string, path: string) {
  const { data, error } = await supabase.storage.from(bucket).download(path);

  if (error) throw new Error(`Could not load ${path}: ${error.message}`);

  const buffer = await data.arrayBuffer();
  const raw = Buffer.from(buffer).toString("utf-8");

  try {
    return JSON.parse(raw).text || "";
  } catch {
    return raw;
  }
}

export async function POST(req: Request) {
  try {
    const { question, top_k = 6 } = await req.json();
    if (!question) return NextResponse.json({ error: "No question" }, { status: 400 });

    // 1) Embed question
    const queryEmb = await embedOpenAI(question);

    // 2) Get nearest chunks via RPC
    const { data: rows, error } = await supabase.rpc("match_documents", {
      query_embedding: queryEmb,
      match_count: top_k,
    });
    if (error) throw error;

    const bucket = process.env.SUPABASE_BUCKET_TEXTS || "texts";
    const chunks: any[] = [];

    // 3) Load JSON + slice text for each retrieved chunk
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

    // 4) Build context for OpenAI
    let context = "";
    chunks.forEach((c) => {
      context += `SOURCE: ${c.source} [${c.start}-${c.end}]\n${c.text}\n\n`;
    });

    // 5) Call OpenAI Chat
    const aiRes = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [
          { role: "system", content: "You are a legal assistant. Only answer using provided context. Keep answers accurate and concise, cite the sources." },
          { role: "user", content: `Question: ${question}\n\nContext:\n${context}` },
        ],
        temperature: 0.0,
      }),
    });

    const result = await aiRes.json();
    const answer = result.choices?.[0]?.message?.content || "";

    return NextResponse.json({
      answer,
      sources: chunks,
    });

  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || String(err) },
      { status: 500 }
    );
  }
}