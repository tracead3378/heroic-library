#!/bin/bash

# Navigate to your repository
cd ~/heroic-github || exit

# Run the python update script
/usr/bin/python3 update_library.py

# Check if index.html was changed, then commit and push
git add index.html
if ! git diff --quiet || ! git diff --staged --quiet; then
    git pull --rebase origin main
    git commit -m "Automated daily local library refresh (Epic, GOG, Prime)"
    git push
fi
