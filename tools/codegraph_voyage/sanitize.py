"""Path and content sanitization — exclude sensitive paths before remote transmission."""

import re

# Patterns that match sensitive paths to exclude from embedding content.
# Each pattern is compiled and checked against the relative file path.
SENSITIVE_PATH_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?:^|/)\.env(?:\..*)?$", re.IGNORECASE),
    re.compile(r"(?:^|/)\.aws/(?:credentials|config)$", re.IGNORECASE),
    re.compile(r"(?:^|/)\.ssh/", re.IGNORECASE),
    re.compile(r"(?:^|/)\.docker/config\.json$", re.IGNORECASE),
    re.compile(r"(?:^|/)\.(?:kube|gnupg)/", re.IGNORECASE),
    re.compile(r"(?:^|/)(?:credentials|secrets)(?:[^/]*)?(?:/|$)", re.IGNORECASE),
    re.compile(r"(?:^|/)(?:private_key[^/]*|id_[^/]+|[^/]*_(?:rsa|dsa|ecdsa|ed25519))$", re.IGNORECASE),
    re.compile(r"(?:^|/)\.(?:pgpass|netrc|npmrc|pypirc|git-credentials)$", re.IGNORECASE),
    re.compile(r"(?:^|/)(?:tokens\.json|service-account[^/]*\.json|vault-token)$", re.IGNORECASE),
    re.compile(r"(?:^|/)(?:secret|password|private_key|token|api_key|keyring)[^/]*$", re.IGNORECASE),
    re.compile(r"\.(?:pem|key|p12|pfx|crt|cer|jks|keystore)$", re.IGNORECASE),
    re.compile(r"(?:^|/)\.git/"),
    re.compile(r"(?:^|/)__pycache__/"),
    re.compile(r"(?:^|/)node_modules/"),
    re.compile(r"(?:^|/)\.venv/"),
    re.compile(r"(?:^|/)venv/"),
    re.compile(r"(?:^|/)\.codegraph/"),
    re.compile(r"(?:^|/)\.hermes/"),
    re.compile(r"(?:^|/)runtime/"),
    re.compile(r"(?:^|/)target/"),
    re.compile(r"(?:^|/)dist/"),
    re.compile(r"(?:^|/)build/"),
]

# Line-level patterns: skip embedding of lines that match these.
SENSITIVE_LINE_PATTERNS: list[re.Pattern] = [
    re.compile(
        r"(?:^|[,{\s])['\"]?(?:password|passwd|secret|api_key|apikey|auth_token|"
        r"access_token|refresh_token|private_key|client_secret|aws_secret_access_key|token)"
        r"['\"]?\s*(?:=>|->|=|:)\s*(?P<value>.+?)\s*$",
        re.IGNORECASE,
    ),
    re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE),
]

_PRIVATE_KEY_END = re.compile(r"-----END [A-Z0-9 ]*PRIVATE KEY-----", re.IGNORECASE)
_PLACEHOLDER_VALUES = re.compile(
    r"^(?:['\"])?(?:|placeholder|changeme|change[-_ ]?me|example|dummy|sample|"
    r"redacted|masked|none|null|nil|x+|\*+|your[-_ ].*|<[^>]+>|\$\{[^}]+\})"
    r"(?:['\"])?$",
    re.IGNORECASE,
)


def _is_obvious_placeholder(value: str) -> bool:
    normalized = value.strip().rstrip(",").rstrip()
    # A JSON object contributes its closing brace after the quoted value.
    if normalized.endswith("}") and normalized[:1] in {"'", '"'}:
        normalized = normalized[:-1].rstrip()
    return bool(_PLACEHOLDER_VALUES.fullmatch(normalized))


def is_sensitive_path(rel_path: str) -> bool:
    """Return True if rel_path matches any sensitive-path pattern."""
    str_path = rel_path.replace("\\", "/")
    for pat in SENSITIVE_PATH_PATTERNS:
        if pat.search(str_path):
            return True
    return False


def sanitize_content(content: str, rel_path: str = "") -> str:
    """Remove lines that match sensitive patterns from content.

    Returns the sanitized content. Lines are replaced with a comment marker.
    If the entire document is consumed (all lines removed), a placeholder is
    returned so the embedding is not empty.
    """
    if is_sensitive_path(rel_path):
        return "[content excluded: sensitive path]"

    lines = content.splitlines(keepends=True)
    kept: list[str] = []
    in_private_key = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            kept.append(line)
            continue
        if in_private_key:
            kept.append("# [redacted by codegraph-voyage sanitizer]\n")
            if _PRIVATE_KEY_END.search(stripped):
                in_private_key = False
            continue

        is_sensitive = False
        for pat in SENSITIVE_LINE_PATTERNS:
            match = pat.search(stripped)
            if not match:
                continue
            if "BEGIN" in stripped.upper() and "PRIVATE KEY" in stripped.upper():
                in_private_key = True
                is_sensitive = True
                break
            value = match.groupdict().get("value")
            if value is None or not _is_obvious_placeholder(value):
                is_sensitive = True
                break
        if is_sensitive:
            kept.append(f"# [redacted by codegraph-voyage sanitizer]\n")
        else:
            kept.append(line)

    result = "".join(kept).strip()
    return result if result else "[content excluded: all lines redacted]"


# Exported list of path patterns (for documentation / debugging).
EXCLUDED_PATH_PATTERNS = [p.pattern for p in SENSITIVE_PATH_PATTERNS]