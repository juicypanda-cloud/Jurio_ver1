// scripts/upload_texts_to_supabase.js
// Upload all doc_*.json and case_*.json to Supabase Storage bucket `texts`

const fs = require("fs");
const path = require("path");
const { createClient } = require("@supabase/supabase-js");
require("dotenv").config();

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const BUCKET = process.env.SUPABASE_BUCKET_TEXTS || "texts";

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error("⚠️ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY");
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY, {
  auth: { persistSession: false },
});

async function uploadFile(localPath, destPath) {
  const buffer = fs.readFileSync(localPath);
  console.log("Uploading →", destPath);

  const { error } = await supabase.storage
    .from(BUCKET)
    .upload(destPath, buffer, {
      contentType: "application/json",
      upsert: true,
    });

  if (error) {
    console.error("❌ Upload error:", error.message);
  } else {
    console.log("✅ Uploaded:", destPath);
  }
}

async function uploadAll() {
  const legalDir = "data_store/legalinfo_full";
  const shuukhDir = "data_store/shuukh_full";

  const legalFiles = fs.readdirSync(legalDir).filter(f => f.endsWith(".json"));
  const shuukhFiles = fs.readdirSync(shuukhDir).filter(f => f.endsWith(".json"));

  console.log(`Found ${legalFiles.length} legal documents`);
  console.log(`Found ${shuukhFiles.length} court cases`);

  for (const file of legalFiles) {
    await uploadFile(
      path.join(legalDir, file),
      `legalinfo/${file}`
    );
  }

  for (const file of shuukhFiles) {
    await uploadFile(
      path.join(shuukhDir, file),
      `shuukh/${file}`
    );
  }

  console.log("\n🎉 All JSON files uploaded successfully!");
}

uploadAll();