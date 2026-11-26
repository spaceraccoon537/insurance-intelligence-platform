import re

from fastapi import HTTPException


CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
INSTRUCTION_OVERRIDE_PATTERN = re.compile(
    r"\b("
    r"ignore\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+instructions"
    r"|disregard\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+instructions"
    r"|reveal\s+(?:the\s+)?(?:system\s+prompt|hidden\s+instructions)"
    r"|act\s+as\s+(?:a\s+)?(?:developer|system|root)"
    r"|jailbreak"
    r")\b",
    re.IGNORECASE,
)


def validate_user_query(text: str) -> str:
    """Sanitize plain-text input and reject explicit prompt-override attempts."""
    sanitized = CONTROL_CHARACTERS.sub("", text).strip()
    if not sanitized:
        raise HTTPException(status_code=422, detail="The request text is empty.")
    if INSTRUCTION_OVERRIDE_PATTERN.search(sanitized):
        raise HTTPException(
            status_code=422,
            detail="Instruction override attempts are not accepted.",
        )
    return sanitized
