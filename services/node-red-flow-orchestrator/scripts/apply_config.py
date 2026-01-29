import json
import sys
import os

def apply_config(flow_path, config_path):
    with open(flow_path, 'r') as f:
        flow_content = f.read()

    config = {}
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
    
    # Also include environment variables that might be passed from mise
    # This allows hybrid approach if needed, but config file takes precedence if keys match
    # (Or we can make config take precedence. Let's make config take precedence)
    
    # Perform substitution
    # Simple string replacement for ${VAR} syntax
    for key, value in config.items():
        placeholder = f"${{{key}}}"
        flow_content = flow_content.replace(placeholder, value)
    
    return flow_content

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_config.py <flow_json_path> [config_json_path]", file=sys.stderr)
        sys.exit(1)
        
    flow_path = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = apply_config(flow_path, config_path)
    print(result)
