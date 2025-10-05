# IG Follow Ratio Pipeline

This tool increases your Instagram followers-to-following ratio by looking up accounts in your following list, flagging accounts with a negative followers-to-following ratio, and then exporting a list of those accounts into an excel sheet (csv) with links to each flagged account for easy unfollowing on your computer. 

⚠️ **Use responsibly and at your accounts own risk! Automated browsing of Instagram may violate their Terms of Use. Run in small batches with delays, and avoid aggressive scraping.**

![image alt](https://github.com/gcaballero1/IGFollowRatioPipeline/blob/main/Screenshot%20Process.jpg?raw=true)

## Quick Start

1. Create an Excel file `following_to_check.xlsx` with a sheet `Following to Check` and a column `username` listing handles.

   You can request a list of accounts in your following in instagram:
     - Go to settings -> Account center -> Your information and permissions -> Export your information -> Create Export -> (Choose your instagram account) -> Export to device -> (Make sure to choose Date Range as `All Time` and Format as `Json` and for Customize information check off everything except followers and following) -> then save all your customizations -> start export
     - Will notify you through email when ready and then you downlaod from the same account center you went to and will be in a zipped file
     - Next you can upload the 'following' file and ask ChatGpt to generate a downloadable Excel file (`following_to_check.xlsx`) listing all usernames with profile links

2. Install deps:
   ```bash
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   python ig_ratio_scraper_mobile.py  --input "examples/following_to_check.sample.xlsx"  --sheet "Following to Check"  --out "ig_counts_following_mobile.csv"  --out_negative "ig_negative_ratio_following_mobile.csv"  --sleep 5.0 --max 150 --restart_every 100 --cooldown 120
   ```
   
Outputs:
- `ig_counts_following_mobile.csv` — counts for all scanned users
- `ig_negative_ratio_following_mobile.csv` — only negative-ratio accounts

## FYI
If you notice the code producing `None` results for profiles (username_234: followers=None, following=None), means your IP is throttled. Don't freak out, just means you need to wait for 30-60 mins but sometimes can be up to a few hours. You can re-run to check if still happening but don't spam too much to prevent account getting resticted, hasn't happen to me yet... *knocks on wood*

## Tips to reduce `None` results
- Use batches (`--max 150`) and longer delays (`--sleep 5–6s`).
- Breaks between batches; increase `--cooldown` if you see "Please wait a few minutes".

## License
[PolyForm Noncommercial License 1.0.0](https://github.com/gcaballero1/IGFollowRatioPipeline/blob/605ae76ba0122fdedb13e36d5ac46dd6fefafce0/LICENSE.md)
