import axios from "axios";
import * as cheerio from "cheerio";
import fs from "fs";
import path from "path";

// -------------------------
// URL DETECTION REGEX
// -------------------------
const LEGALINFO_REGEX = /https:\/\/legalinfo\.mn\/[^\s"']+/g;
const SHUUKH_REGEX = /https:\/\/shuukh\.mn\/[^\s"']+/g;

// -------------------------
// SMART PRIORITY LOGIC
// -------------------------
function pickLegalinfoUrl(urls) {
  if (!urls || urls.length === 0) return null;

  // Prefer main laws
  const lawUrl = urls.find(u => u.includes("/law/"));
  if (lawUrl) return lawUrl;

  // Otherwise use longest URL
  return urls.sort((a,b) => b.length - a.length)[0];
}

function pickShuukhUrl(urls) {
  if (!urls || urls.length === 0) return null;

  // Prefer lavlagaa
  const lav = urls.find(u => u.includes("/lavlagaa/"));
  if (lav) return lav;

  // Prefer case/decision links
  const caseUrl = urls.find(u =>
      u.includes("/decision/") ||
      u.includes("/case/") ||
      u.includes("/court_")
  );
  if (caseUrl) return caseUrl;

  // Otherwise use longest
  return urls.sort((a,b) => b.length - a.length)[0];
}

// -------------------------
// SCRAPERS (improved selectors)
// -------------------------
async function scrapeLegalinfo(url) {
  const res = await axios.get(url, { timeout: 30000 });
  const $ = cheerio.load(res.data);

  const selectors = [
    ".law-detail",
    ".lawtext",
    ".content",
    ".post-content",
    ".article-content",
    ".body-content"
  ];

  for (const sel of selectors) {
    if ($(sel).length) return $(sel).text().trim();
  }

  return $("body").text().trim();
}

async function scrapeShuukh(url) {
  const res = await axios.get(url, { timeout: 30000 });
  const $ = cheerio.load(res.data);

  const selectors = [
    ".decision-container",
    ".content-body",
    ".case-detail",
    ".post-content",
    ".wrap-content"
  ];

  for (const sel of selectors) {
    if ($(sel).length) return $(sel).text().trim();
  }

  return $("body").text().trim();
}

// -------------------------
// PROCESSOR
// -------------------------
async function run() {
  console.log("🔍 Fixing URLs + scraping clean text...\n");

  // LEGALINFO
  const legalDir = "data_store/legalinfo_full";
  for (const f of fs.readdirSync(legalDir)) {
    if (!f.endsWith(".json")) continue;

    const full = JSON.parse(fs.readFileSync(`${legalDir}/${f}`, "utf8"));
    const rawText = full.text || "";

    const urls = [...rawText.matchAll(LEGALINFO_REGEX)].map(m => m[0]);
    const chosen = pickLegalinfoUrl(urls);

    if (!chosen) {
      console.log(`⚠ No valid URL inside ${f} — skipping`);
      continue;
    }

    console.log(`📘 LEGALINFO: ${f} → ${chosen}`);

    const clean = await scrapeLegalinfo(chosen);

    fs.writeFileSync(
      `data_store/legalinfo_clean/${f}`,
      JSON.stringify({ url: chosen, text: clean }, null, 2)
    );
  }

  console.log("\n✅ LEGALINFO DONE.\n");

  // SHUUKH
  const shuukhDir = "data_store/shuukh_full";
  for (const f of fs.readdirSync(shuukhDir)) {
    if (!f.endsWith(".json")) continue;

    const full = JSON.parse(fs.readFileSync(`${shuukhDir}/${f}`, "utf8"));
    const rawText = full.text || "";

    const urls = [...rawText.matchAll(SHUUKH_REGEX)].map(m => m[0]);
    const chosen = pickShuukhUrl(urls);

    if (!chosen) {
      console.log(`⚠ No valid URL in case file ${f} — skipping`);
      continue;
    }

    console.log(`📕 SHUUKH: ${f} → ${chosen}`);

    const clean = await scrapeShuukh(chosen);

    fs.writeFileSync(
      `data_store/shuukh_clean/${f}`,
      JSON.stringify({ url: chosen, text: clean }, null, 2)
    );
  }

  console.log("\n🎉 ALL DONE!");
}

run();