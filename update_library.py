import os
import json
import re
import urllib.request

# --- CONFIGURATION ---
STEAM_API_KEY = os.getenv("STEAM_API_KEY", "EEA98A0A9E0090B7D0723287A82BA0EF")
STEAM_ID = os.getenv("STEAM_ID", "76561198847656848")

# Paths
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML_PATH = os.path.join(REPO_DIR, "index.html")
HEROIC_CACHE_PATH = os.path.expanduser("~/.var/app/com.heroicgameslauncher.hgl/config/heroic/store_cache")

def safe_load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
    return None

def fetch_steam_games():
    steam_games = []
    if not STEAM_API_KEY or "YOUR_LOCAL" in STEAM_API_KEY:
        print("Steam API key missing. Skipping Steam fetch.")
        return steam_games

    url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={STEAM_API_KEY}&steamid={STEAM_ID}&include_appinfo=true&format=json"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            for game in data.get("response", {}).get("games", []):
                if game.get("name"):
                    steam_games.append({"title": game.get("name"), "store": "Steam", "key": "steam"})
        print(f"Loaded {len(steam_games)} Steam games.")
    except Exception as e:
        print(f"Error fetching Steam games: {e}")
    return steam_games

def load_heroic_games():
    games = []
    
    # 1. Epic Games
    epic_data = safe_load_json(os.path.join(HEROIC_CACHE_PATH, "legendary_library.json"))
    if epic_data:
        for item in epic_data.get("library", []):
            if not item.get("is_dlc") and item.get("app_type", "").upper() in ["GAME", "BASE", ""]:
                if item.get("title"):
                    games.append({"title": item.get("title"), "store": "Epic Games", "key": "epic"})

    # 2. GOG
    gog_data = safe_load_json(os.path.join(HEROIC_CACHE_PATH, "gog_library.json"))
    if gog_data:
        for item in gog_data.get("games", []):
            if not item.get("is_dlc") and not item.get("is_hidden"):
                if item.get("title"):
                    games.append({"title": item.get("title"), "store": "GOG", "key": "gog"})

    # 3. Prime Gaming
    nile_data = safe_load_json(os.path.join(HEROIC_CACHE_PATH, "nile_library.json"))
    if nile_data:
        for item in nile_data.get("library", []):
            if item.get("title"):
                games.append({"title": item.get("title"), "store": "Prime Gaming", "key": "prime"})

    print(f"Loaded {len(games)} non-Steam games from Heroic cache.")
    return games

def main():
    print("--- Reading All Local Libraries ---")
    all_games = fetch_steam_games() + load_heroic_games()
    
    unique_games = {g['title'].strip(): g for g in all_games}.values()
    sorted_games = sorted(unique_games, key=lambda x: x['title'].lower())

    print(f"Total Combined Games: {len(sorted_games)}")

    cards_html = []
    for g in sorted_games:
        card = (
            f'      <div class="game-card" data-store="{g["key"]}">\n'
            f'        <div class="game-title">{g["title"]}</div>\n'
            f'        <div class="store-badge {g["key"]}">{g["store"]}</div>\n'
            f'      </div>'
        )
        cards_html.append(card)

    new_grid = "\n" + "\n".join(cards_html) + "\n    "

    with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    updated_content = re.sub(
        r'(<div id="game-grid"[^>]*>)(.*?)(</div>\s*<!-- /game-grid -->|</div>\s*</main>)',
        rf'\1{new_grid}\3',
        content,
        flags=re.DOTALL
    )

    with open(INDEX_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(updated_content)

    print("Success: index.html updated with all libraries!")

if __name__ == "__main__":
    main()
