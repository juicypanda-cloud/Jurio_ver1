import fs from "fs";
import path from "path";
import OpenAI from "openai";

// load env
import "dotenv/config";

const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// folders
const INPUT_DIR = "processed/chunks";
const OUTPUT_DIR = "processed/embed_batches";

// ensure dir exists
if (!fs.existsSync(OUTPUT_DIR)) fs.mkdirSync(OUTPUT_DIR, { recursive: true });

// recursive file reader
function walk(dir) {
  let results = [];
  const list = fs.readdirSync(dir);

  list.forEach((file) => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);

    if (stat && stat.isDirectory()) {
      results = results.concat(walk(filePath));
    } else if (file.endsWith("_chunks.json")) {
      results.push(filePath);
    }
  });

  return results;
}

async function embedChunk(text) {
  const response = await client.embeddings.create({
    model: "text-embedding-3-small",    // ✔️ 1536-dim
    input: text,
  });

  return response.data[0].embedding;
}

async function run() {
  const files = walk(INPUT_DIR);

  console.log(`Embedding ${files.length} chunk-files...`);

  let batch = [];
  let batchIndex = 0;

  for (const f of files) {
    const doc = JSON.parse(fs.readFileSync(f, "utf8"));
    const url = doc.url;
    const chunks = doc.chunks;

    for (let i = 0; i < chunks.length; i++) {
      const text = chunks[i];

      const embedding = await embedChunk(text);

      batch.push({
        url,
        chunk: text,
        embedding,
      });

      console.log(`Embedded: ${path.basename(f)} → chunk ${i}`);
    }

    // Save batch every 100 entries
    if (batch.length >= 100) {
      fs.writeFileSync(
        `${OUTPUT_DIR}/batch_${batchIndex}.json`,
        JSON.stringify(batch, null, 2)
      );
      console.log(`Saved batch_${batchIndex}.json`);
      batchIndex++;
      batch = [];
    }
  }

  // save remainder
  if (batch.length > 0) {
    fs.writeFileSync(
      `${OUTPUT_DIR}/batch_${batchIndex}.json`,
      JSON.stringify(batch, null, 2)
    );
    console.log(`Saved final batch_${batchIndex}.json`);
  }

  console.log("DONE: All embeddings generated.");
}

run();
