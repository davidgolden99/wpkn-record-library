#!/bin/bash
# Pull the latest main from GitHub and restart the live service.
# Run this ON THE SERVER, from /opt/wpkn-record-library, by a user with sudo
# (currently: wpknadmin). Requires no GitHub credentials — the repo is public.
set -e

echo "Pulling latest from GitHub..."
sudo -u library git -C /opt/wpkn-record-library pull

echo "Restarting wpkn-library service..."
sudo systemctl restart wpkn-library

echo "Done. Current status:"
sudo systemctl status wpkn-library --no-pager --lines=5
