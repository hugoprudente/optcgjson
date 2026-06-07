import argparse
import datetime
import json
import os
import re
import html
import sys
from typing import List

import requests
from bs4 import BeautifulSoup

# Toggle to enable or disable image downloading
download_images = False

# Base URLs
# Discovery uses the root CARDLIST page, individual scrapes use ?series=<id>
DISCOVERY_URL = "https://asia-en.onepiece-cardgame.com/cardlist/"
base_url = "https://asia-en.onepiece-cardgame.com/cardlist/?series="
image_base_url = "https://asia-en.onepiece-cardgame.com/images/cardlist/card/"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERIES_MAP_FILE = os.path.join(BASE_DIR, "series_map.yaml")

# Some series represent special crossover products (e.g. Premium Boosters) whose
# logical "set code" is not the prefix of individual card numbers. Map those
# series IDs to explicit codes so we can write a product-level JSON.
SPECIAL_SERIES_CODES: dict[int, str] = {
    # Recording ALL PREMIUM BOOSTER -ONE PIECE CARD THE BEST vol.2- [PRB-02]
    556302: "PRB02",
}


def load_series_map() -> dict[str, dict]:
    """
    Load a simple YAML mapping of logical set codes to series and names.

    Expected shape:

      PRB02:
        name: "Recording ALL PREMIUM BOOSTER -ONE PIECE CARD THE BEST vol.2- [PRB-02]"
        series: [556302]

      OP15:
        name: "Adventure on KAMI’s Island [OP-15]"
        series: [556115]
    """
    if not os.path.isfile(SERIES_MAP_FILE):
        return {}

    sets: dict[str, dict] = {}
    current: str | None = None

    with open(SERIES_MAP_FILE, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue

            # Top-level key (set code)
            if not line.startswith(" ") and line.endswith(":"):
                key = line[:-1].strip()
                current = key
                sets[current] = {"name": "", "series": []}
                continue

            if current is None:
                continue

            stripped = line.strip()
            if stripped.startswith("name:"):
                name_val = stripped[len("name:") :].strip()
                # Strip optional quotes
                if name_val.startswith(("'", '"')) and name_val.endswith(("'", '"')):
                    name_val = name_val[1:-1]
                sets[current]["name"] = name_val
            elif stripped.startswith("series:"):
                # Expect series: [556302, 556901]
                series_val = stripped[len("series:") :].strip()
                if series_val.startswith("[") and series_val.endswith("]"):
                    inner = series_val[1:-1].strip()
                    if inner:
                        nums: list[int] = []
                        for chunk in inner.split(","):
                            chunk = chunk.strip()
                            if chunk.isdigit():
                                nums.append(int(chunk))
                        sets[current]["series"] = nums

    return sets


def build_series_to_set_code(series_map: dict[str, dict]) -> dict[int, str]:
    """Invert the YAML map to series_id -> logical set code."""
    mapping: dict[int, str] = {}
    for set_code, info in series_map.items():
        for series_id in info.get("series", []):
            if isinstance(series_id, int):
                mapping[series_id] = set_code
    return mapping


def default_series_from_map(series_map: dict[str, dict]) -> list[int]:
    """Collect all series IDs from the YAML map."""
    series_ids: set[int] = set()
    for info in series_map.values():
        for sid in info.get("series", []):
            if isinstance(sid, int):
                series_ids.add(sid)
    return sorted(series_ids)


def write_series_map(series_map: dict[str, dict]) -> None:
    """Write the in-memory series_map back to series_map.yaml."""
    with open(SERIES_MAP_FILE, "w", encoding="utf-8") as f:
        for code in sorted(series_map.keys()):
            info = series_map[code]
            name = info.get("name", "") or ""
            # Strip any leftover HTML tags or entities from the name before writing.
            # This ensures a clean YAML file even if upstream labels contained markup.
            name = html.unescape(re.sub(r"<[^>]+>", "", name)).strip()
            series_ids = info.get("series", []) or []
            f.write(f"{code}:\n")
            if name:
                # Quote the name to avoid YAML issues with colons, brackets, etc.
                safe_name = name.replace('"', '\\"')
                f.write(f'  name: "{safe_name}"\n')
            else:
                f.write("  name: \"\"\n")
            if series_ids:
                ids_str = ", ".join(str(sid) for sid in series_ids if isinstance(sid, int))
                f.write(f"  series: [{ids_str}]\n")
            else:
                f.write("  series: []\n")


def discover_series_numbers_from_site() -> List[int]:
    """
    Discover all available series numbers from the official card list dropdown.

    This keeps the scraper in sync with newly released sets without manually
    keeping the YAML mapping up to date.
    """
    # Kept for backward compatibility if needed elsewhere; unused by refresh-list now.
    url = DISCOVERY_URL
    print_utf8(f"Discovering series numbers from {url}")
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        print_utf8(f"Failed to discover series numbers from site: {exc}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    options = soup.select("select[name='series'] option") or soup.find_all("option")
    discovered: List[int] = []
    for opt in options:
        val = (opt.get("value") or "").strip()
        if val.isdigit():
            discovered.append(int(val))

    discovered = sorted(set(discovered))
    if not discovered:
        print_utf8("No series numbers discovered from site.")
        return []

    print_utf8(f"Discovered {len(discovered)} series numbers from site.")
    return discovered


def load_series_numbers(series_map: dict[str, dict]) -> List[int]:
    """
    Determine which series numbers to scrape.

    Keep it simple:
    - If series_map.yaml has entries, use ONLY those IDs.
    - If it is empty, fall back to discovering IDs from the site.
    """
    yaml_ids = default_series_from_map(series_map)
    if yaml_ids:
        print_utf8(f"Using {len(yaml_ids)} series numbers from series_map.yaml.")
        return yaml_ids

    live_ids = discover_series_numbers_from_site()
    if not live_ids:
        print_utf8("No series numbers available (from YAML or site).")
        return []

    print_utf8(f"Using {len(live_ids)} series numbers discovered from site.")
    return live_ids


def refresh_series_list_file() -> None:
    """
    Refresh series_map.yaml starting from the dropdown on the discovery page,
    then correcting human-readable names using already-scraped set JSON files
    when available.

    We do NOT recurse into individual series pages here. All information we need
    is already exposed in the <select name="series">:
      - option @value => numeric series ID (e.g. 556202)
      - option text   => human name with logical code in brackets, e.g.
                         'EXTRA BOOSTER ... [EB-02]'

    Behaviour:
      - The dropdown is the single source of truth for which keys exist.
      - We build a NEW in-memory map from the dropdown.
      - If the old series_map.yaml has a matching key, we keep its custom name.
      - After that, if we have a matching JSON file under ./sets for a given
        set code, we trust its `card_set` label for that code and fix up the
        name (this corrects cases where the dropdown text is misleading).
      - In the future, we also want to populate a `release_date: YYYY-MM-DD`
        field per set in series_map.yaml, derived from the official product
        pages on the site, so frontends (like Punk Records) can list sets by
        release date without scraping again.
      - When done, we overwrite series_map.yaml (no appending to old contents).
    """
    old_map = load_series_map()

    url = DISCOVERY_URL
    print_utf8(f"Refreshing series_map.yaml from {url} (dropdown only, no per-series scraping).")
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        print_utf8(f"Failed to load discovery page: {exc}")
        return

    soup = BeautifulSoup(response.content, "html.parser")
    select = soup.find("select", attrs={"name": "series"})
    if not select:
        print_utf8("Could not find <select name='series'> on discovery page.")
        return

    options = select.find_all("option")
    if not options:
        print_utf8("No <option> elements found under <select name='series'>.")
        return

    # Build a fresh map purely from the dropdown.
    new_map: dict[str, dict] = {}
    updated = 0

    for opt in options:
        raw_val = (opt.get("value") or "").strip()
        if not raw_val.isdigit():
            continue
        series_id = int(raw_val)

        # Human-readable label; also strip any leftover HTML entities/tags
        raw_label = opt.get_text(" ", strip=True)
        label = html.unescape(raw_label)
        label = re.sub(r"<[^>]+>", "", label).strip()
        # Prefer logical code inside brackets, e.g. [OP-02], [ST-28], [EB-02], [PRB-02]
        m = re.search(r"\[([A-Z0-9\-]+)\]", label)
        if m:
            bracket_code = m.group(1)  # e.g. 'OP-02'
            set_code = bracket_code.replace("-", "")  # OP-02 -> OP02, ST-28 -> ST28
        else:
            # No [CODE] present (e.g. Promotion card / Family Deck / Limited Product Card):
            # fall back to using a sanitized version of the label as the key.
            set_code = sanitize_folder_name(label)

        # Prefer any custom name already defined for this key.
        preferred_name = ""
        if set_code in old_map:
            preferred_name = old_map[set_code].get("name", "") or ""
        if not preferred_name:
            preferred_name = label

        entry = new_map.get(set_code) or {"name": preferred_name, "series": []}
        # Ensure name is the preferred one (old custom name or label)
        if not entry.get("name"):
            entry["name"] = preferred_name
        if series_id not in entry.get("series", []):
            entry.setdefault("series", []).append(series_id)
            updated += 1
        new_map[set_code] = entry

    # Second pass: correct names from already-scraped set JSON files, if any.
    # This relies on the richer HTML that backs the card pages themselves,
    # which has proven more accurate for BOOSTER vs STARTER naming.
    sets_dir = os.path.join(BASE_DIR, "sets")
    if os.path.isdir(sets_dir):
        for filename in os.listdir(sets_dir):
            if not filename.endswith(".json"):
                continue
            json_path = os.path.join(sets_dir, filename)
            try:
                with open(json_path, "r", encoding="utf-8") as jf:
                    payload = json.load(jf)
            except (OSError, json.JSONDecodeError):
                continue

            data = payload.get("data") or {}
            set_code = data.get("code")
            cards = data.get("cards") or []
            if not set_code or not isinstance(set_code, str) or not cards:
                continue

            first = cards[0] or {}
            card_set_label = first.get("card_set") or ""
            if not isinstance(card_set_label, str) or not card_set_label.strip():
                continue

            fixed_label = html.unescape(re.sub(r"<[^>]+>", "", card_set_label)).strip()

            entry = new_map.get(set_code)
            if not entry:
                continue

            existing_name = entry.get("name") or ""
            # Heuristic: fix clearly wrong names, e.g. OPxx entries that still
            # reference [ST-yy] starter decks in their label.
            if (
                not existing_name
                or (set_code.startswith("OP") and "[ST-" in existing_name)
                or (set_code.startswith("EB") and "[ST-" in existing_name)
            ):
                entry["name"] = fixed_label
                new_map[set_code] = entry

    # Overwrite series_map.yaml with the freshly built (and corrected) map.
    write_series_map(new_map)
    print_utf8(f"series_map.yaml rewritten with {updated} (code,series_id) entries (names patched from set JSON where possible).")



# Function to sanitize folder names
def sanitize_folder_name(name: str) -> str:
    return re.sub(r"\W+", "", name)


# Create images directory if it doesn't exist
if download_images and not os.path.exists("images"):
    os.makedirs("images")


# Function to download an image and save it locally
def download_image(img_url: str, img_name: str, folder_name: str) -> str | None:
    if not download_images:
        return None
    folder_path = os.path.join("images", folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    print(f"Downloading image: {img_url}")
    response = requests.get(img_url)
    if response.status_code == 200:
        with open(f"{folder_path}/{img_name}", "wb") as file:
            file.write(response.content)
        print(f"Saved image to: {folder_path}/{img_name}")
        return f"{folder_path}/{img_name}"
    print(f"Failed to download image: {img_url}")
    return None

# Function to print with utf-8 encoding
def print_utf8(text: str) -> None:
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))

# Function to scrape data from a single URL
def scrape_series(series_number: int, series_to_set_code: dict[int, str] | None = None) -> dict | None:
    url = f"{base_url}{series_number}"
    print_utf8(f"Scraping URL: {url}")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        print_utf8(f"Failed to retrieve data for series {series_number}: {exc}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    card_elements = soup.find_all("dl", class_="modalCol")

    cards = []
    for card_element in card_elements:
        card_id = card_element.get("id", "N/A")
        
        info_col = card_element.find("div", class_="infoCol")
        if info_col:
            info_text = info_col.text.split('|')
            card_number = info_text[0].strip() if len(info_text) > 0 else 'N/A'
            card_type = info_text[1].strip() if len(info_text) > 1 else 'N/A'
            card_class = info_text[2].strip() if len(info_text) > 2 else 'N/A'
        else:
            card_number = card_type = card_class = "N/A"

        card_name = (
            card_element.find("div", class_="cardName").text.strip()
            if card_element.find("div", class_="cardName")
            else "N/A"
        )

        cost = (
            card_element.find("div", class_="cost").text.replace("Cost", "").strip()
            if card_element.find("div", class_="cost")
            else "N/A"
        )

        attribute = card_element.find("div", class_="attribute")
        if attribute:
            attribute_text = attribute.find("i").text.strip() if attribute.find("i") else "N/A"
        else:
            attribute_text = "N/A"

        power = (
            card_element.find("div", class_="power").text.replace("Power", "").strip()
            if card_element.find("div", class_="power")
            else "N/A"
        )

        counter = (
            card_element.find("div", class_="counter")
            .text.replace("Counter", "")
            .strip()
            if card_element.find("div", class_="counter")
            else "N/A"
        )

        color = (
            card_element.find("div", class_="color").text.replace("Color", "").strip()
            if card_element.find("div", class_="color")
            else "N/A"
        )

        feature = (
            card_element.find("div", class_="feature").text.replace("Type", "").strip()
            if card_element.find("div", class_="feature")
            else "N/A"
        )

        # Block Icon (1–4) is rendered as:
        # <div class="block"><h3>Block<br> Icon</h3>4</div>
        block_div = card_element.find("div", class_="block")
        if block_div:
            # Full text looks like "BlockIcon4" or similar, strip the label parts
            raw = block_div.get_text(strip=True)
            value = (
                raw.replace("Block", "")
                .replace("Icon", "")
                .strip()
            )
            block_icon = value or "N/A"
        else:
            block_icon = "N/A"

        effect = (
            card_element.find("div", class_="text").text.replace("Effect", "").strip()
            if card_element.find("div", class_="text")
            else "N/A"
        )

        trigger = (
            card_element.find("div", class_="trigger")
            .text.replace("Trigger[Trigger]", "[Trigger]")
            if card_element.find("div", class_="trigger")
            else "N/A"
        )

        card_set = (
            card_element.find("div", class_="getInfo")
            .text.replace("Card Set(s)", "")
            .strip()
            if card_element.find("div", class_="getInfo")
            else "N/A"
        )
        folder_name = sanitize_folder_name(card_set)

        image_url = f"{image_base_url}{card_id}.png"
        image_path = (
            download_image(image_url, f"{card_id}.png", folder_name)
            if download_images
            else f"images/{folder_name}/{card_id}.png"
        )

        cards.append({
            "id": card_id,
            "number": card_number,
            "type": card_type,
            "class": card_class,
            "name": card_name,
            "image_path": image_path,
            "cost": cost,
            "attribute": [] if attribute_text == "N/A" else attribute_text.split("/"),
            "trigger": trigger,
            "power": power,
            "counter": counter,
            "color": color.split("/") if color != "N/A" else [],
            "feature": feature.split("/") if feature != "N/A" else [],
             # 1–4, or "N/A" when not present
            "block_icon": block_icon,
            "effect": effect,
            "card_set": card_set,
            "image_url": image_url,
        })
        
        print_utf8(f"Scraped card: {card_name} (ID: {card_id}, Number: {card_number})")

    if not cards:
        print_utf8(f"No cards found for series {series_number}")
        return None

    # Derive set code.
    # Prefer explicit mapping from series_map.yaml if available, then fall back
    # to hard-coded specials, then to first card number prefix.
    if series_to_set_code and series_number in series_to_set_code:
        set_code = series_to_set_code[series_number]
    elif series_number in SPECIAL_SERIES_CODES:
        set_code = SPECIAL_SERIES_CODES[series_number]
    else:
        first_number = cards[0]["number"]
        set_code = first_number.split("-")[0] if "-" in first_number else first_number
    today = datetime.date.today().isoformat()

    set_info = {
        "meta": {
            "date": today,
            "version": "1.0.0",
            # Keep track of the numeric source from the official site, but call it "set"
            # to align terminology across the project.
            "set": series_number,
        },
        "data": {
            "code": set_code,
            "cards": cards,
        },
    }

    return set_info


def main():
    parser = argparse.ArgumentParser(description="Scrape One Piece TCG card data.")
    parser.add_argument(
        "--refresh-list",
        action="store_true",
        help="Only write the default series numbers to the list file and exit.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=True,
        help="Do not hit the official site; use series_numbers.txt as-is.",
    )
    parser.add_argument(
        "--series",
        nargs="+",
        type=int,
        help="Only scrape the given series IDs (e.g. 556115 556302).",
    )
    parser.add_argument(
        "--set",
        dest="set_codes",
        nargs="+",
        help="Only scrape logical set codes from series_map.yaml (e.g. OP15 PRB02).",
    )
    parser.add_argument(
        "--list-sets",
        action="store_true",
        help="List available sets from series_map.yaml and exit.",
    )
    args = parser.parse_args()

    if args.refresh_list:
        refresh_series_list_file()
        return

    series_map = load_series_map()
    series_to_set_code = build_series_to_set_code(series_map)

    if args.list_sets:
        if not series_map:
            print_utf8("No series_map.yaml found or file is empty.")
            return
        print_utf8("Available sets from series_map.yaml:")
        for code, info in sorted(series_map.items()):
            name = info.get("name", "")
            series_ids = ", ".join(str(s) for s in info.get("series", []))
            print_utf8(f"  {code}: {name} (series: {series_ids})")
        return

    if args.offline:
        # Offline: rely solely on YAML mapping
        if not series_map:
            print_utf8("Offline mode requires series_map.yaml to define series IDs.")
            return
        series_numbers = default_series_from_map(series_map)
        print_utf8(
            f"Running in offline mode with {len(series_numbers)} series IDs from series_map.yaml.",
        )
    else:
        series_numbers = load_series_numbers(series_map)

    # If --set is provided, resolve to series IDs using the YAML map
    if args.set_codes:
        if not series_map:
            print_utf8("Warning: --set was provided but series_map.yaml is missing or empty.")
        wanted: set[int] = set()
        for code in args.set_codes:
            info = series_map.get(code)
            if not info:
                print_utf8(f"Warning: set code {code} not found in series_map.yaml.")
                continue
            for sid in info.get("series", []):
                if isinstance(sid, int):
                    wanted.add(sid)
        if wanted:
            series_numbers = sorted(wanted & set(series_numbers))
            print_utf8(f"Filtering to {len(series_numbers)} series from --set: {', '.join(str(s) for s in series_numbers)}")

    # If --series is provided, override to those explicit IDs
    if args.series:
        series_numbers = sorted(set(args.series))
        print_utf8(f"Filtering to explicit --series: {', '.join(str(s) for s in series_numbers)}")

    # Scrape data from all series
    os.makedirs("sets", exist_ok=True)
    for series_number in series_numbers:
        print_utf8(f"Scraping series {series_number}")
        set_info = scrape_series(series_number, series_to_set_code=series_to_set_code)
        if isinstance(set_info, dict) and "data" in set_info:
            out_path = os.path.join("sets", f'{set_info["data"]["code"]}.json')
            with open(out_path, "w", encoding="utf-8") as jsonfile:
                json.dump(set_info, jsonfile, ensure_ascii=False, indent=4)
            print_utf8(f"Wrote set file: {out_path}")

    print_utf8("Scraping completed and data saved to sets/")


if __name__ == "__main__":
    main()
