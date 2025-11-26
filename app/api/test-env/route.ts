import { NextResponse } from "next/server";

export async function GET() {
  const key = process.env.OPENAI_API_KEY;

  return NextResponse.json({
    openai_key_loaded: !!key,
    preview: key?.slice(0, 3) || "none"
  });
}
