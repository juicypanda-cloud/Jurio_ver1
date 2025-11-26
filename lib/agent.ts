import OpenAI from "openai";
import { embedText } from "./embedding";
import { searchDocuments } from "./vectorSearch";

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY!,
});

export async function runLegalAgent(question: string) {
  // 1) Embed question
  const embedding = await embedText(question);

  // 2) Vector search
  const results = await searchDocuments(embedding, 7);

  // 3) Build context
  const context = results
    .map((d: any, i: number) => {
      return `SOURCE #${i + 1}
Title: ${d.title || "Untitled"}
URL: ${d.origin_url || "N/A"}
---
${d.content}`;
    })
    .join("\n\n");

  const prompt = `
You are a Mongolian legal assistant.
You MUST answer based only on the provided documents.
Always include citations.

USER QUESTION:
${question}

CONTEXT:
${context}
`;

  // 4) GPT-4o answer
  const response = await openai.chat.completions.create({
    model: "gpt-4o",
    messages: [
      { role: "system", content: "You are a legal assistant." },
      { role: "user", content: prompt }
    ],
  });

  return {
    answer: response.choices[0].message,
    sources: results,
  };
}
