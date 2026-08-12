#!/bin/bash

# Navigate to repo directory
cd ~/heroic-github || exit

# Load Steam credentials if defined in environment
export STEAM_API_KEY="EEA98A0A9E0090B7D0723287A82BA0EF"
export STEAM_ID="76561198847656848"

# Run the update script
/usr/bin/python3 update_library.py

# Pull remote changes, commit, and push automatically
git add index.html
if ! git diff --quiet || ! git diff --staged --quiet; then
    git pull --rebase origin main
    git commit -m "Automated daily library update from Bazzite"
    git push
fi
