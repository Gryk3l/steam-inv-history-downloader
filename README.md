# steam-inv-history-downloader
A clumsy script to download all your inventory history (any transaction) into a csv file

No parameters, it will ask for session info once ran

Downloads everything that would appear in your steam inventory history (https://steamcommunity.com/profiles/<profile_id>/inventoryhistory/). That includes things such as:
  - Items traded
  - Items being moved into/out of storage units
  - Items crafted
  - Items earned (e.g. Medals in CS2, Weekly Drops in CS2, Booster Packs, Trading Card Drops, Drops for PUBG, etc)
  - Gifts sent
  - Gifts received
  - Armory redeems in CS2
  - Store purchases (includes keys that are bought and instantly used to open keys)
  - Items obtained from opening cases
  - Items listed on the community market
  - Items bought from the community market

Usage:
```python3 steam_inv_hist_downloader.py```
