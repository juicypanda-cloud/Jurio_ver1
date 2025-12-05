const axios = require("axios");
const cheerio = require("cheerio");
const fs = require("fs");
const path = require("path");

// FULL scrape fallback function
function extractFullText(html) {
  const $ = cheerio.load(html);
  return $("body").text().replace(/\s+/g, " ").trim();
}

// LEGALINFO SCRAPER
async function scrapeLegalinfo(url) {
  try {
    const res = await axios.get(url, { timeout: 30000 });
    const $ = cheerio.load(res.data);

    const selectors = [
      ".law-detail",
      ".post-content",
      ".lawtext",
      ".article-content",
      ".body-content",
    ];

    let text = "";
    for (const sel of selectors) {
      if ($(sel).length) {
        text = $(sel).text().trim();
        break;
      }
    }

    if (!text) text = extractFullText(res.data);
    return text;
  } catch (err) {
    console.log("LEGALINFO SCRAPE ERROR:", url, err.message);
    return "";
  }
}

// SHUUKH SCRAPER — FULL MODE
async function scrapeShuukh(url) {
  try {
    const res = await axios.get(url, { timeout: 30000 });
    return extractFullText(res.data);
  } catch (err) {
    console.log("SHUUKH SCRAPE ERROR:", url, err.message);
    return "";
  }
}

async function run() {
  //
  // LEGALINFO
  //
  const legalPath = "data_store/legalinfo_full";
  const legalFiles = fs.readdirSync(legalPath);

  for (const f of legalFiles) {
    if (!f.endsWith(".json")) continue;

    const obj = JSON.parse(fs.readFileSync(path.join(legalPath, f), "utf8"));
    const url = obj.url;

    console.log(`Scraping LEGALINFO → ${f} → ${url}`);

    const text = await scrapeLegalinfo(url);

    fs.writeFileSync(
      `data_store/legalinfo_clean/${f}`,
      JSON.stringify({ url, text }, null, 2)
    );
  }

  console.log("LEGALINFO DONE!");

  //
  // SHUUKH
  //
  const shuukhPath = "data_store/shuukh_full";
  const shuukhFiles = fs.readdirSync(shuukhPath);

  for (const f of shuukhFiles) {
    if (!f.endsWith(".json")) continue;

    const obj = JSON.parse(fs.readFileSync(path.join(shuukhPath, f), "utf8"));
    const url = obj.url;

    console.log(`Scraping SHUUKH → ${f} → ${url}`);

    const text = await scrapeShuukh(url);

    fs.writeFileSync(
      `data_store/shuukh_clean/${f}`,
      JSON.stringify({ url, text }, null, 2)
    );
  }

  console.log("SHUUKH DONE!");
}

run();