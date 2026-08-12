import os
import json
import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# Falls back to local credentials when running on Bazzite PC
STEAM_API_KEY = os.getenv("STEAM_API_KEY", "YOUR_LOCAL_32_CHAR_KEY")
STEAM_ID = os.getenv("STEAM_ID", "7656119XXXXXXXXXX")

# Paths
HEROIC_CACHE_PATH = os.path.expanduser("~/.var/app/com.heroicgameslauncher.hgl/config/heroic/store_cache")
INDEX_HTML_PATH = os.path.expanduser("~/heroic-github/index.html")

def safe_load_json(file_path):
    """Safely load JSON files if they exist locally."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")
    return None

def extract_existing_non_steam_games():
    """Extract non-Steam games directly from index.html if local caches are missing."""
    saved_games = []
    if not os.path.exists(INDEX_HTML_PATH):
        return saved_games

    try:
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            cards = soup.find_all("div", class_="game-card")
            
            for card in cards:
                store_type = card.get("data-store")
                if store_type in ["epic", "gog", "prime"]:
                    # Look specifically for game-title div or h3
                    title_elem = card.find("div", class_="game-title") or card.find("h3")
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        store_label = "Epic Games" if store_type == "epic" else ("GOG" if store_type == "gog" else "Prime Gaming")
                        saved_games.append({
                            "title": title,
                            "store": store_label,
                            "key": store_type
                        })
        print(f"Preserved {len(saved_games)} existing non-Steam games from index.html")
    except Exception as e:
        print(f"Warning: Could not extract non-Steam games: {e}")
        
    return saved_games
    try:
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            cards = soup.find_all("div", class_="game-card")
            
            for card in cards:
                store_type = card.get("data-store")
                if store_type in ["epic", "gog", "prime"]:
                    title_elem = card.find("h3") or card.find("div", class_="game-title")
                    title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"
                    
                    store_label = "Epic Games" if store_type == "epic" else ("GOG" if store_type == "gog" else "Prime Gaming")
                    saved_games.append({
                        "title": title,
                        "store": store_label,
                        "key": store_type
                    })
        print(f"Preserved {len(saved_games)} existing non-Steam games from index.html")
    except Exception as e:
        print(f"Warning: Could not extract non-Steam games from index.html: {e}")
        
    return saved_games

def fetch_steam_games():
    """Fetch owned games using Steam Web API."""
    steam_games = []
    if not STEAM_API_KEY or "YOUR_LOCAL" in STEAM_API_KEY:
        print("Steam API Key not set. Skipping Steam fetch.")
        return steam_games

    url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={STEAM_API_KEY}&steamid={STEAM_ID}&include_appinfo=true&format=json"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            games_list = data.get("response", {}).get("games", [])
            
            for game in games_list:
                steam_games.append({
                    "title": game.get("name", "Unknown Steam Game"),
                    "store": "Steam",
                    "key": "steam",
                    "appid": game.get("appid")
                })
        print(f"Successfully fetched {len(steam_games)} games from Steam API.")
    except Exception as e:
        print(f"Error fetching Steam games: {e}")

    return steam_games

def load_local_heroic_games():
    """Load Epic, GOG, and Prime games from local Heroic cache files."""
    heroic_games = []

    # 1. Epic Games
    epic_data = safe_load_json(os.path.join(HEROIC_CACHE_PATH, "legendary_library.json"))
    if epic_data:
        for item in epic_data.get("library", []):
            if not item.get("is_dlc", False) and item.get("app_type", "").upper() in ["GAME", "BASE", ""]:
                if item.get("title"):
                    heroic_games.append({"title": item.get("title"), "store": "Epic Games", "key": "epic"})

    # 2. GOG
    gog_data = safe_load_json(os.path.join(HEROIC_CACHE_PATH, "gog_library.json"))
    if gog_data:
        for item in gog_data.get("games", []):
            if not item.get("is_dlc", False) and not item.get("is_hidden", False):
                if item.get("title"):
                    heroic_games.append({"title": item.get("title"), "store": "GOG", "key": "gog"})

    # 3. Prime Gaming
    nile_data = safe_load_json(os.path.join(HEROIC_CACHE_PATH, "nile_library.json"))
    if nile_data:
        for item in nile_data.get("library", []):
            if item.get("title"):
                heroic_games.append({"title": item.get("title"), "store": "Prime Gaming", "key": "prime"})

    return heroic_games

def main():
    print("--- Starting Library Sync ---")

    # Fetch Steam Games
    steam_games = fetch_steam_games()

    # Fetch Heroic Games (Local or Preserved)
    local_heroic_games = load_local_heroic_games()
    
    if local_heroic_games:
        print(f"Found {len(local_heroic_games)} games locally in Heroic caches.")
        non_steam_games = local_heroic_games
    else:
        print("Heroic cache files not found locally. Preserving games from index.html...")
        non_steam_games = extract_existing_non_steam_games()

    # Combine all games and remove duplicates
    all_games = steam_games + non_steam_games
    unique_games = {g['title']: g for g in all_games}.values()
    sorted_games = sorted(unique_games, key=lambda x: x['title'].lower())

    print(f"Total Unique Games to Render: {len(sorted_games)}")

    # Update index.html
    if os.path.exists(INDEX_HTML_PATH):
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            content = f.read()

        # Build Card HTML
        cards_html = []
        for g in sorted_games:
            card = f'''      <div class="game-card" data-store="{g['key']}">
        <div class="game-title">{g['title']}</div>
        <div class="store-badge {g['key']}">{g['store']}</div>
      </div>'''
            cards_html.append(card)

        new_grid_content = "\n" + "\n".join(cards_html) + "\n    "
        
        # Replace grid container content safely
        updated_content = re.sub(
            r'(<div id="game-grid"[^>]*>)(.*?)(</div>\s*<!-- /game-grid -->|</div>\s*</main>)',
            rf'\1{new_grid_content}\3',
            content,
            flags=re.DOTALL
        )

        with open(INDEX_HTML_PATH, "w", encoding="utf-8") as f:
            f.write(updated_content)

        print("Successfully updated index.html with all combined libraries!")
    else:
        print("Error: index.html was not found.")

if __name__ == "__main__":
    main()
