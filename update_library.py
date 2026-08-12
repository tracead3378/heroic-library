import glob
import json
import os
import re
import subprocess
import urllib.request
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
STEAM_API_KEY = os.getenv("STEAM_API_KEY", "EEA98A0A9E0090B7D0723287A82BA0EF")
STEAM_ID = os.getenv("STEAM_ID", "76561198847656848")

HEROIC_CACHE_PATH = os.path.expanduser(
    "~/.var/app/com.heroicgameslauncher.hgl/config/heroic/store_cache"
)
INDEX_HTML_PATH = "index.html"

def extract_existing_non_steam_games():
    """Extract and preserve non-Steam games from index.html during cloud runs."""
    preserved_games = []
    if not os.path.exists(INDEX_HTML_PATH):
        return preserved_games

    try:
        with open(INDEX_HTML_PATH, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
            cards = soup.find_all("div", class_="game-card")
            for card in cards:
                store_key = card.get("data-store")
                if store_key in ["epic", "gog", "prime"]:
                    title_elem = card.find("span", class_="game-title")
                    badge_elem = card.find("span", class_="badge")
                    if title_elem and badge_elem:
                        preserved_games.append({
                            "title": title_elem.get_text(strip=True),
                            "store": badge_elem.get_text(strip=True),
                            "key": store_key
                        })
        print(f"Cloud mode: Preserved {len(preserved_games)} non-Steam games from index.html.")
    except Exception as e:
        print(f"Warning: Failed to parse index.html for non-Steam preservation: {e}")
        
    return preserved_games

def load_games():
    games = []
    heroic_caches_found = os.path.exists(HEROIC_CACHE_PATH)

    if heroic_caches_found:
        # --- LOCAL MODE: Read directly from Heroic cache files ---
        # 1. Epic Games
        try:
            with open(os.path.join(HEROIC_CACHE_PATH, "legendary_library.json")) as f:
                data = json.load(f)
                for item in data.get("library", []):
                    app_type = item.get("app_type", "").upper()
                    if not item.get("is_dlc", False) and app_type in ["GAME", "BASE", ""]:
                        if item.get("title"):
                            games.append({"title": item.get("title"), "store": "Epic Games", "key": "epic"})
        except Exception as e:
            print(f"Warning: Epic library load issue: {e}")

        # 2. GOG
        try:
            with open(os.path.join(HEROIC_CACHE_PATH, "gog_library.json")) as f:
                data = json.load(f)
                for item in data.get("games", []):
                    is_dlc = item.get("is_dlc", False) or item.get("type") == "dlc"
                    if not is_dlc and not item.get("is_hidden", False):
                        if item.get("title"):
                            games.append({"title": item.get("title"), "store": "GOG", "key": "gog"})
        except Exception as e:
            print(f"Warning: GOG library load issue: {e}")

        # 3. Prime Gaming
        try:
            with open(os.path.join(HEROIC_CACHE_PATH, "nile_library.json")) as f:
                data = json.load(f)
                for item in data.get("library", []):
                    if item.get("title"):
                        games.append({"title": item.get("title"), "store": "Prime Gaming", "key": "prime"})
        except Exception as e:
            print(f"Warning: Prime library load issue: {e}")
    else:
        # --- CLOUD MODE: Preserve non-Steam games from current index.html ---
        games.extend(extract_existing_non_steam_games())

    # 4. Fetch Fresh Steam Library via Web API
    steam_titles = set()
    if STEAM_API_KEY and STEAM_ID:
        try:
            url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={STEAM_API_KEY}&steamid={STEAM_ID}&include_appinfo=true&include_played_free_games=true&format=json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as response:
                steam_data = json.loads(response.read().decode())
                for game in steam_data.get("response", {}).get("games", []):
                    if game.get("name"):
                        steam_titles.add(game.get("name"))
            print(f"Fetched {len(steam_titles)} Steam games from Web API.")
        except Exception as e:
            print(f"Warning: Steam Web API issue: {e}")

    for title in steam_titles:
        games.append({"title": title, "store": "Steam", "key": "steam"})

    # Deduplicate games
    unique_games = {}
    for g in games:
        unique_key = (g["title"].lower(), g["key"])
        if unique_key not in unique_games:
            unique_games[unique_key] = g

    return sorted(unique_games.values(), key=lambda x: x["title"].lower())

def main():
    games = load_games()

    epic_count = sum(1 for g in games if g["key"] == "epic")
    gog_count = sum(1 for g in games if g["key"] == "gog")
    prime_count = sum(1 for g in games if g["key"] == "prime")
    steam_count = sum(1 for g in games if g["key"] == "steam")

    cards_html = "".join(
        f"""
    <div class="game-card" data-store="{g['key']}" data-title="{g['title'].lower()}">
        <span class="game-title">{g['title']}</span>
        <span class="badge badge-{g['key']}">{g['store']}</span>
    </div>
    """
        for g in games
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>My PC Gaming Library</title>
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#121212">
    <link rel="manifest" href='data:application/manifest+json,{{
        "name": "My PC Gaming Library",
        "short_name": "Library",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#121212",
        "theme_color": "#121212"
    }}'>
    <style>
        * {{ box-sizing: border-box; -webkit-tap-highlight-color: transparent; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #121212;
            color: #ffffff;
            margin: 0;
            padding: 16px;
        }}
        .sticky-header {{
            position: sticky;
            top: 0;
            background: #121212;
            padding-bottom: 12px;
            border-bottom: 1px solid #2a2a2a;
            margin-bottom: 16px;
            z-index: 100;
        }}
        .title-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        h2 {{ margin: 0; font-size: 20px; font-weight: 700; color: #fff; }}
        .search-box {{
            width: 100%;
            padding: 12px 14px;
            background: #1e1e1e;
            border: 1px solid #333;
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
            outline: none;
            margin-bottom: 12px;
        }}
        .search-box:focus {{ border-color: #555; }}
        .tabs {{
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding-bottom: 4px;
            scrollbar-width: none;
        }}
        .tabs::-webkit-scrollbar {{ display: none; }}
        .tab-btn {{
            background: #1e1e1e;
            border: 1px solid #333;
            color: #aaa;
            padding: 8px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            white-space: nowrap;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .tab-btn.active {{
            background: #ffffff;
            color: #121212;
            border-color: #ffffff;
        }}
        .card-container {{
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}
        .game-card {{
            background: #1a1a1a;
            border: 1px solid #282828;
            border-radius: 10px;
            padding: 14px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }}
        .game-title {{
            font-size: 15px;
            font-weight: 500;
            color: #e2e8f0;
            padding-right: 12px;
            line-height: 1.3;
        }}
        .badge {{
            font-size: 11px;
            font-weight: 700;
            padding: 5px 9px;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            white-space: nowrap;
        }}
        .badge-steam {{ background: #171a21; color: #00adee; border: 1px solid #00adee; }}
        .badge-epic {{ background: rgba(255, 255, 255, 0.08); color: #f5f5f5; border: 1px solid #444; }}
        .badge-gog {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); }}
        .badge-prime {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }}
        .empty-state {{
            text-align: center;
            color: #666;
            padding: 40px 0;
            font-size: 14px;
            display: none;
        }}
    </style>
</head>
<body>
    <div class="sticky-header">
        <div class="title-row">
            <h2>My PC Gaming Library</h2>
            <span style="font-size: 13px; color: #888;">{len(games)} Total Games</span>
        </div>
        <input type="text" id="searchInput" class="search-box" placeholder="Search games..." oninput="filterGames()">
        <div class="tabs">
            <button class="tab-btn active" onclick="setCategory('all', this)">All ({len(games)})</button>
            <button class="tab-btn" onclick="setCategory('steam', this)">Steam ({steam_count})</button>
            <button class="tab-btn" onclick="setCategory('epic', this)">Epic ({epic_count})</button>
            <button class="tab-btn" onclick="setCategory('gog', this)">GOG ({gog_count})</button>
            <button class="tab-btn" onclick="setCategory('prime', this)">Prime ({prime_count})</button>
        </div>
    </div>
    <div class="card-container" id="cardContainer">
        {cards_html}
    </div>
    <div class="empty-state" id="emptyState">No games found</div>
    <script>
        let currentCategory = 'all';
        function setCategory(category, btn) {{
            currentCategory = category;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterGames();
        }}
        function filterGames() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.game-card');
            let visibleCount = 0;
            cards.forEach(card => {{
                const matchesCategory = (currentCategory === 'all' || card.dataset.store === currentCategory);
                const matchesSearch = card.dataset.title.includes(query);
                if (matchesCategory && matchesSearch) {{
                    card.style.display = 'flex';
                    visibleCount++;
                }} else {{
                    card.style.display = 'none';
                }}
            }});
            document.getElementById('emptyState').style.display = visibleCount === 0 ? 'block' : 'none';
        }}
    </script>
</body>
</html>"""

    with open(INDEX_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html successfully generated.")

if __name__ == "__main__":
    main()
