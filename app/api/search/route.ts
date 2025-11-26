import { NextResponse } from "next/server";
import { embedText } from "@/lib/embedding";
import { searchDocuments } from "@/lib/vectorSearch";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const query = (body?.query || "").trim();
    if (!query) return NextResponse.json({ error: "Missing query" }, { status: 400 });

    const emb = await embedText(query);
    const results = await searchDocuments(emb, 5);

    return NextResponse.json({ ok: true, results });
  } catch (err: any) {
    console.error("SEARCH ERROR:", err);
    return NextResponse.json({ error: err?.message || "Search failed" }, { status: 500 });
  }
}
