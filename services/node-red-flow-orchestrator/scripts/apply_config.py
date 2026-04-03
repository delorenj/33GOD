import json
import re
import sys
import os


def apply_config(flow_path, config_path):
    with open(flow_path, 'r') as f:
        flow_data = json.load(f)

    config = {}
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)

    if not config:
        return json.dumps(flow_data)

    pattern = re.compile(r'\$\{([^}]+)\}')

    def substitute(value):
        if not isinstance(value, str):
            return value
        def replacer(match):
            key = match.group(1)
            return config.get(key, match.group(0))
        return pattern.sub(replacer, value)

    def walk(node):
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [walk(item) for item in node]
        elif isinstance(node, str):
            return substitute(node)
        return node

    result = walk(flow_data)
    return json.dumps(result)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_config.py <flow_json_path> [config_json_path]", file=sys.stderr)
        sys.exit(1)

    flow_path = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None

    result = apply_config(flow_path, config_path)
    print(result)
