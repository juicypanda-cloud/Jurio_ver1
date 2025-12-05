import fs from "fs";
import path from "path";

// Extract numeric ID from filename like doc_27.json → 27
function extractId(filename) {
  const match = filename.match(/\d+/);
  return match ? match[0] : null;
}

function fixLegalinfoUrls() {
  const inputDir = "data_store/legalinfo_full";
  const outputDir = "data_store/legalinfo_fixed";

  const files = fs.readdirSync(inputDir);

  for (const f of files) {
    if (!f.endsWith(".json")) continue;

    const id = extractId(f);
    if (!id) continue;

    const fixedUrl = `https://legalinfo.mn/mn/law/${id}`;

    const original = JSON.parse(
      fs.readFileSync(path.join(inputDir, f), "utf8")
    );

    const cleaned = {
      url: fixedUrl,
      text: original.text || "",
      title: original.title || ""
    };

    fs.writeFileSync(
      path.join(outputDir, f),
      JSON.stringify(cleaned, null, 2)
    );

    console.log(`LEGALINFO FIXED → ${f} → ${fixedUrl}`);
  }
}

function fixShuukhUrls() {
  const inputDir = "data_store/shuukh_full";
  const outputDir = "data_store/shuukh_fixed";

  const files = fs.readdirSync(inputDir);

  for (const f of files) {
    if (!f.endsWith(".json")) continue;

    const id = extractId(f);
    if (!id) continue;

    const fixedUrl = `https://shuukh.mn/lavlagaa/${id}`;

    const original = JSON.parse(
      fs.readFileSync(path.join(inputDir, f), "utf8")
    );

    const cleaned = {
      url: fixedUrl,
      text: original.text || "",
      title: original.title || ""
    };

    fs.writeFileSync(
      path.join(outputDir, f),
      JSON.stringify(cleaned, null, 2)
    );

    console.log(`SHUUKH FIXED → ${f} → ${fixedUrl}`);
  }
}

console.log("Fixing URLs...");
fixLegalinfoUrls();
fixShuukhUrls();
console.log("DONE! URLs safely repaired.");
