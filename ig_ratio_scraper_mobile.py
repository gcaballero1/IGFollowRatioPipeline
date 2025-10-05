#!/usr/bin/env python3
"""
IG Ratio Scraper v2.1 (mobile UA + m.instagram.com + cooldowns + periodic restart)

Purpose:
- Reduce "followers=None" streaks caused by Instagram's anti-bot/rate limits.
- Use the lighter mobile site (m.instagram.com) and a mobile User-Agent.
- Restart the browser every N profiles to reset state a bit.
- Detect "Please wait a few minutes" pages and auto-cooldown.

Install:
    pip install pandas openpyxl selenium webdriver-manager beautifulsoup4

Example:
    python ig_ratio_scraper_mobile.py \
      --input following_to_check.xlsx \
      --sheet "Following to Check" \
      --out C:\ig_out\ig_counts_following_mobile.csv \
      --out_negative C:\ig_out\ig_negative_ratio_following_mobile.csv \
      --headless --sleep 4.0 --start 0 --max 200 --restart_every 100 --cooldown 120
"""

import os
import re
import time
import argparse
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

def human_int(s):
    s = s.strip().lower().replace(',', '')
    m = re.match(r'^([\d\.]+)\s*([kKmM])?$', s)
    if not m:
        try:
            return int(re.sub(r'[^0-9]', '', s))
        except Exception:
            return None
    num = float(m.group(1))
    suf = m.group(2)
    if not suf:
        return int(num)
    if suf.lower() == 'k':
        return int(num * 1_000)
    if suf.lower() == 'm':
        return int(num * 1_000_000)
    return int(num)

def extract_counts_from_html(html):
    soup = BeautifulSoup(html, "html.parser")

    # Detect rate-limit/login walls
    full_text = soup.get_text(" ", strip=True).lower()
    if "please wait a few minutes" in full_text or "try again later" in full_text:
        return "RATE_LIMIT", "RATE_LIMIT"

    # 1) og:description is present on m.instagram usually too
    og = soup.find("meta", {"property": "og:description"})
    if og and og.get("content"):
        text = og["content"]
        m = re.search(r'([\d,\.kKmM]+)\s+Followers,\s+([\d,\.kKmM]+)\s+Following', text, flags=re.IGNORECASE)
        if m:
            return human_int(m.group(1)), human_int(m.group(2))

    # 2) Fallback: scan text
    mf = re.search(r'([\d,\.kKmM]+)\s*followers', full_text, flags=re.IGNORECASE)
    mg = re.search(r'([\d,\.kKmM]+)\s*following', full_text, flags=re.IGNORECASE)
    followers = human_int(mf.group(1)) if mf else None
    following = human_int(mg.group(1)) if mg else None
    if followers or following:
        return followers, following

    return None, None

def setup_driver(headless=False, mobile=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    # Stability and quieter logs
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument("--use-gl=swiftshader")
    opts.add_argument("--disable-3d-apis")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=430,900")
    opts.add_argument("--lang=en-US")
    opts.add_argument("--log-level=3")
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    if mobile:
        opts.add_argument(f"--user-agent={MOBILE_UA}")

    service = Service(ChromeDriverManager().install(), log_path=os.devnull)
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(60)
    return driver

def append_row_csv(path, row, header=False):
    import pandas as pd
    df = pd.DataFrame([row])
    df.to_csv(path, mode="a", index=False, header=header)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--sheet", default="Following to Check")
    ap.add_argument("--out", default="ig_counts.csv")
    ap.add_argument("--out_negative", default="ig_negative_ratio.csv")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--sleep", type=float, default=3.5)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--max", type=int, default=None)
    ap.add_argument("--restart_every", type=int, default=120, help="Restart browser after N profiles")
    ap.add_argument("--cooldown", type=int, default=90, help="Seconds to sleep if rate-limit is detected")
    args = ap.parse_args()

    df = pd.read_excel(args.input, sheet_name=args.sheet)
    if "username" not in df.columns:
        raise SystemExit("The input sheet must contain a 'username' column.")

    usernames = (
        df["username"].dropna().astype(str).str.strip().str.replace("@","", regex=False).unique().tolist()
    )
    usernames = usernames[args.start: (args.start + args.max) if args.max else None]

    # Prepare CSV headers if file doesn't exist yet
    header_all = not os.path.exists(args.out)
    header_neg = not os.path.exists(args.out_negative)

    domain = "m.instagram.com"
    driver = setup_driver(headless=args.headless, mobile=True)
    processed_since_restart = 0

    try:
        for idx, u in enumerate(usernames, 1 + args.start):
            url = f"https://{domain}/{u}/"

            # Periodic restart to reduce long-run None streaks
            if processed_since_restart >= args.restart_every:
                driver.quit()
                time.sleep(2.0)
                driver = setup_driver(headless=args.headless, mobile=True)
                processed_since_restart = 0

            try:
                driver.get(url)
                time.sleep(args.sleep)

                html = driver.page_source
                followers, following = extract_counts_from_html(html)

                if followers == "RATE_LIMIT" or following == "RATE_LIMIT":
                    print(f"[{idx}] {u}: RATE_LIMIT detected → sleeping {args.cooldown}s")
                    time.sleep(args.cooldown)
                    # Retry once after cooldown
                    driver.get(url)
                    time.sleep(args.sleep)
                    html = driver.page_source
                    followers, following = extract_counts_from_html(html)

                ratio = (followers / following) if (isinstance(followers, int) and isinstance(following, int) and following > 0) else None

                row = {
                    "index": idx,
                    "username": u,
                    "profile_link": url,
                    "followers": followers if isinstance(followers, int) else None,
                    "following": following if isinstance(following, int) else None,
                    "ratio_followers_over_following": ratio,
                }

                append_row_csv(args.out, row, header=header_all)
                header_all = False

                if (isinstance(followers, int)) and (isinstance(following, int)) and (following > 0) and (followers < following):
                    append_row_csv(args.out_negative, row, header=header_neg)
                    header_neg = False

                processed_since_restart += 1
                print(f"[{idx}] {u}: followers={row['followers']}, following={row['following']}")

            except Exception as e:
                row = {
                    "index": idx,
                    "username": u,
                    "profile_link": url,
                    "followers": None,
                    "following": None,
                    "ratio_followers_over_following": None,
                    "error": str(e)[:240],
                }
                append_row_csv(args.out, row, header=header_all)
                header_all = False
                print(f"[{idx}] {u}: ERROR {str(e)[:140]}")

                time.sleep(args.sleep)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
