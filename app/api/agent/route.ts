import { NextResponse } from "next/server";
import { embedText } from "@/lib/embedding";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const question = body.question || "";

    const emb = await embedText(question);

    return NextResponse.json({
      ok: true,
      question,
      embedding: emb,
    });
  } catch (err: any) {
    console.error("AGENT ERROR:", err);
    return NextResponse.json({
      error: err?.message || "Agent failed",
    });
  }
}
