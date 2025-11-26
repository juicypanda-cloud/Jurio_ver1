import { NextResponse } from "next/server";
import { embedText } from "@/lib/embedding";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const text = (body?.text || "").trim();
    if (!text) return NextResponse.json({ error: "Missing text" }, { status: 400 });

    const emb = await embedText(text);
    return NextResponse.json({ ok: true, embedding: emb });
  } catch (err: any) {
    console.error("EMBED ERROR:", err);
    return NextResponse.json({ error: err?.message || "Embedding failed" }, { status: 500 });
  }
}
