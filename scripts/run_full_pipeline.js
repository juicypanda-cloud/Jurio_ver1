// SMART PIPELINE (NO FULL RESCRAPE UNLESS EXPLICITLY RUN)

import { execSync } from "child_process";
import fs from "fs";

// helper
function exists(path) {
  return fs.existsSync(path);
}

console.log("\n====================================");
console.log("🚀 JURIO SMART PIPELINE STARTED");
console.log("====================================\n");

// 1. Check if full scrape folders exist
const hasLegalFull = exists("data_store/legalinfo_full");
const hasShuukhFull = exists("data_store/shuukh_full");

if (!hasLegalFull || !hasShuukhFull) {
  console.log("⚠️ Full scrape directories missing.");
  console.log("➡️ Skipping scraping step (will NOT rescrape).");
} else {
  console.log("📌 Running scrape step because full folders exist.");
  execSync("node scripts/fix_urls_and_scrape.js", { stdio: "inherit" });
}

// 2. Always clean & chunk new files
console.log("\n📌 Running: chunk_texts.js");
execSync("node scripts/chunk_texts.js", { stdio: "inherit" });

// 3. Generate NEW embeddings only
console.log("\n📌 Running: generate_embeddings.js");
execSync("node scripts/generate_embeddings.js", { stdio: "inherit" });

// 4. Upload ONLY new embeddings
console.log("\n📌 Running: upload_embeddings.js");
execSync("node scripts/upload_embeddings.js", { stdio: "inherit" });

console.log("\n====================================");
console.log("🎉 SMART PIPELINE COMPLETED SUCCESSFULLY");
console.log("====================================\n");