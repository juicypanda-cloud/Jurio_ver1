import fs from "fs";
import path from "path";
import { createClient } from "@supabase/supabase-js";
import "dotenv/config";

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

async function uploadBatch(batchPath, batchName) {
  const content = JSON.parse(fs.readFileSync(batchPath, "utf8"));

  const rows = content.map((item) => ({
    chunk_id: item.chunk_id,
    embedding: item.embedding,
    source: item.source,
    start: item.start,
    end: item.end,
    batch_id: batchName
  }));

  const { error } = await supabase.from("documents").insert(rows);

  if (error) {
    console.error("❌ ERROR uploading", batchName, error);
  } else {
    console.log("✅ Uploaded", batchName);
  }
}

async function run() {
  const folder = "processed/embed_batches";
  const files = fs.readdirSync(folder).filter((f) => f.endsWith(".json"));

  console.log(`🚀 Uploading ${files.length} batches...`);

  for (const file of files) {
    const fullPath = path.join(folder, file);
    await uploadBatch(fullPath, file.replace(".json", ""));
  }

  console.log("🎉 DONE — All embeddings uploaded to Supabase!");
}

run();