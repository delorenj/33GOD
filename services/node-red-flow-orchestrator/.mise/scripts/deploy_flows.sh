#!/usr/bin/env bash
set -euo pipefail

NODE_RED_DIR="/home/delorenj/.node-red"
FLOWS_DIR="${FLOWS_DIR}"
# SCRIPTS_DIR is provided by mise environment
APPLY_CONFIG_SCRIPT="${SCRIPTS_DIR}/apply_config.py"

echo "Deploying flows from ${FLOWS_DIR} to ${NODE_RED_DIR}..."

# Backup current flows
if [[ -f "${NODE_RED_DIR}/flows.json" ]]; then
	cp "${NODE_RED_DIR}/flows.json" "${NODE_RED_DIR}/flows.json.bak"
	echo "Backed up existing flows to flows.json.bak"
fi

# Prepare a temporary directory for processed flows
TEMP_FLOW_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_FLOW_DIR"' EXIT

echo "Processing flow files with configuration..."

# Iterate over json files in FLOWS_DIR
# Note: This loop assumes filenames don't contain newlines
find "${FLOWS_DIR}" -maxdepth 1 -name "*.json" -not -name "*.config.json" -print0 | while IFS= read -r -d '' flow_file; do
	filename=$(basename "$flow_file")
	base="${filename%.json}"
	config_file="${FLOWS_DIR}/${base}.config.json"

	echo "Processing $filename..."

	if [[ -f "$config_file" ]]; then
		echo "  Applying config from ${base}.config.json"
		python3 "$APPLY_CONFIG_SCRIPT" "$flow_file" "$config_file" >"${TEMP_FLOW_DIR}/${filename}"
	else
		echo "  No config file found, using as-is"
		# Still run through script to handle potential env var substitutions if we expanded scope,
		# but for now just copy or run without config arg
		python3 "$APPLY_CONFIG_SCRIPT" "$flow_file" >"${TEMP_FLOW_DIR}/${filename}"
	fi
done

# Merge all processed flow files into a single flows.json
echo "Merging processed flows..."
# Use find on the TEMP_FLOW_DIR to get the processed files
find "${TEMP_FLOW_DIR}" -name "*.json" -type f -exec cat {} + | jq -s 'add' >"${NODE_RED_DIR}/flows.json"

echo "Restarting Node-RED..."
pm2 restart node-red || pm2 start ~/.node-red/ecosystem.config.js

echo "Deploy complete."
pm2 logs node-red --lines 5 --nostream
