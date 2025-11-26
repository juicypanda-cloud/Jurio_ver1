import { supabase } from "./supabase";

export async function searchDocuments(embedding: number[], matchCount: number = 5) {
  const { data, error } = await supabase.rpc("match_documents", {
    query_embedding: embedding,
    match_count: matchCount,
  });

  if (error) {
    console.error("Supabase match_documents error:", error);
    throw new Error("Database search failed");
  }

  return data;
}
