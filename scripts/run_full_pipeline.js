import { execSync } from "child_process";

function run(cmd) {
  console.log(`\n🚀 Running: ${cmd}\n`);
  execSync(cmd, { stdio: "inherit" });
}

console.log("====================================");
console.log("🚀 JURIO FULL PIPELINE STARTED");
console.log("====================================");

run("node scripts/fix_urls_and_scrape.js");
run("node scripts/chunk_texts.js");
run("node scripts/generate_embeddings.js");
run("node scripts/upload_embeddings.js");

console.log("====================================");
console.log("🎉 PIPELINE COMPLETE!");
console.log("====================================");
