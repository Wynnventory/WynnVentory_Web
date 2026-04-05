"""
Downloads item type icons from the Wynncraft CDN.
Icons are saved to scripts/item_icons/
"""

import os
import urllib.request
import urllib.error

BASE_URL = "https://cdn.wynncraft.com/nextgen/itemguide/3.3"
TYPES = ["wand", "bow", "dagger", "spear", "relik", "ring", "necklace", "bracelet", "helmet", "leggings", "boots", "chestplate"]
ELEMENTS = ["earth", "fire", "thunder", "water", "multi", "air", "basicWood", "basicIron", "basicGold", "basicDiamond"]
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../modules/routes/web/static/icons/item_icons")


def download_icons():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    total = len(TYPES) * len(ELEMENTS) * 3
    downloaded = 0
    skipped = 0
    failed = 0

    for item_type in TYPES:
        for element in ELEMENTS:
            for i in range(1, 4):
                filename = f"{item_type}.{element}{i}.webp"
                url = f"{BASE_URL}/{filename}"
                dest = os.path.join(OUTPUT_DIR, filename)

                if os.path.exists(dest):
                    print(f"  skip  {filename}")
                    skipped += 1
                    continue

                try:
                    urllib.request.urlretrieve(url, dest)
                    print(f"  ok    {filename}")
                    downloaded += 1
                except urllib.error.HTTPError as e:
                    print(f"  {e.code}   {filename}")
                    failed += 1
                except Exception as e:
                    print(f"  err   {filename}: {e}")
                    failed += 1

    print(f"\nDone. {downloaded} downloaded, {skipped} skipped, {failed} failed.")
    print(f"Icons saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    download_icons()
