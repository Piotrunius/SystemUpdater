"""
Secret redaction and terminal escape sanitization for SystemUpdater.
"""

from __future__ import annotations

import re

ANSI_ESCAPE_PATTERN = re.compile(
    r"\x1B(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1B\\)|[@-Z\\-_])"
)
TERMINAL_CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")

PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN (?:[A-Z0-9_\-]+ )?PRIVATE KEY(?: BLOCK)?-----[\s\S]*?-----END (?:[A-Z0-9_\-]+ )?PRIVATE KEY(?: BLOCK)?-----"
)
BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
BASIC_AUTH_PATTERN = re.compile(
    r"(?i)\b((?:Proxy-)?Authorization\s*:\s*Basic\s+)[A-Za-z0-9+/=]+"
)
URL_CREDENTIAL_PATTERN = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://)([^/@\s\r\n]+@)")
TOKEN_PATTERN = re.compile(
    r"(?i)\b(?:"
    r"gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"github_pat_[A-Za-z0-9_]{20,}|"
    r"glpat-[A-Za-z0-9_\-]{20,}|"
    r"glcbt-[A-Za-z0-9_\-]{20,}|"
    r"xox[baprs]-[0-9a-zA-Z]{10,}|"
    r"AKIA[0-9A-Z]{16}|"
    r"sk-[A-Za-z0-9_\-]{20,}|"
    r"sk-ant-[A-Za-z0-9_\-]{20,}|"
    r"pypi-[A-Za-z0-9_\-]{50,}|"
    r"npm_[A-Za-z0-9]{36}|"
    r"hf_[A-Za-z0-9]{34,}"
    r")\b"
)
ASSIGNMENT_SECRET_PATTERN = re.compile(
    r"(?i)(\b[\"\']?(?:token|password|passwd|secret|key|api[_-]?key|auth[_-]?token|access[_-]?token|refresh[_-]?token|client[_-]?secret|api[_-]?secret|private[_-]?key|secret[_-]?key|ssh[_-]?key|deploy[_-]?key|credential|credentials|session[_-]?token)[\"\']?)(\s*[=:]\s*)(\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;]+)"
)
FLAG_SECRET_PATTERN = re.compile(
    r"(?i)(--(?:token|password|passwd|secret|api[_-]?key|auth[_-]?token|access[_-]?token|client[_-]?secret|api[_-]?secret|private[_-]?key)(?:=|\s+))(\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s]+)"
)


def redact_text(value: str) -> str:
    """Remove terminal control sequences and mask common credentials."""
    if not isinstance(value, str):
        return "" if value is None else str(value)
    safe_value = ANSI_ESCAPE_PATTERN.sub("", value)
    safe_value = TERMINAL_CONTROL_PATTERN.sub("", safe_value)
    redacted = PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", safe_value)
    redacted = BASIC_AUTH_PATTERN.sub(r"\1[REDACTED]", redacted)
    redacted = BEARER_PATTERN.sub("Bearer [REDACTED]", redacted)
    redacted = URL_CREDENTIAL_PATTERN.sub(r"\1[REDACTED]@", redacted)
    redacted = TOKEN_PATTERN.sub("[REDACTED_TOKEN]", redacted)

    def _sub_assign(m: re.Match[str]) -> str:
        prefix = m.group(1)
        sep = m.group(2)
        val = m.group(3)
        if val.startswith(('"', "'")) and len(val) >= 2 and val[-1] == val[0]:
            q = val[0]
            return f"{prefix}{sep}{q}[REDACTED]{q}"
        return f"{prefix}{sep}[REDACTED]"

    redacted = ASSIGNMENT_SECRET_PATTERN.sub(_sub_assign, redacted)

    def _sub_flag(m: re.Match[str]) -> str:
        prefix = m.group(1)
        val = m.group(2)
        if val.startswith(('"', "'")) and len(val) >= 2 and val[-1] == val[0]:
            q = val[0]
            return f"{prefix}{q}[REDACTED]{q}"
        return f"{prefix}[REDACTED]"

    return FLAG_SECRET_PATTERN.sub(_sub_flag, redacted)
