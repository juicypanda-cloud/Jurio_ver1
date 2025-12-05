import fs from "fs";
import path from "path";

// CONFIG
const INPUT_DIRS = [
  "data_store/legalinfo_clean",
  "data_store/shuukh_clean",
];

const OUTPUT_DIR = "processed/chunks";
const CHUNK_SIZE = 1500; // characters per chunk
const CHUNK_OVERLAP = 200;

// Ensure output folders exist
function ensureDir(p) {
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}

function chunkText(text, size = CHUNK_SIZE, overlap = CHUNK_OVERLAP) {
  const chunks = [];
  let start = 0;

  while (start < text.length) {
    const end = start + size;
    const chunk = text.slice(start, end);
    chunks.push(chunk);
    start += size - overlap;
  }

  return chunks;
}

async function run() {
  ensureDir(OUTPUT_DIR);

  for (const inputDir of INPUT_DIRS) {
    const files = fs.readdirSync(inputDir).filter(f => f.endsWith(".json"));

    const targetFolderName = path.basename(inputDir); // legalinfo_clean → legalinfo_clean
    const outFolder = path.join(OUTPUT_DIR, targetFolderName);
    ensureDir(outFolder);

    for (const f of files) {
      const filePath = path.join(inputDir, f);
      const raw = JSON.parse(fs.readFileSync(filePath, "utf8"));

      const text = raw.text || "";

      const chunks = chunkText(text);

      const outPath = path.join(outFolder, f.replace(".json", "_chunks.json"));
      fs.writeFileSync(outPath, JSON.stringify({ url: raw.url, chunks }, null, 2));

      console.log(`CHUNKED → ${f} → ${chunks.length} chunks`);
    }
  }

  console.log("DONE: All texts chunked successfully.");
}

run();
