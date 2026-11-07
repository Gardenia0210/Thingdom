"""Json utils."""
import json
import logging
import re
from typing import TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

def clean_and_parse_json(raw_text: str, schema: type[T]) -> T:
    """Clean and parse json."""
    if not raw_text or not raw_text.strip():
        raise ValueError("模型返回空文本")

    cleaned = raw_text

    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)

    md_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", cleaned, re.DOTALL)
    if md_match:
        cleaned = md_match.group(1)

    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        return schema.model_validate(data)
    except (json.JSONDecodeError, Exception):
        pass

    json_text = _extract_json_block(cleaned)
    if json_text:
        try:
            data = json.loads(json_text)
            return schema.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"提取的 JSON 块解析失败: {e}")

    raise ValueError(
        f"无法从模型输出中解析有效 JSON。"
        f"原始文本前 200 字符: {raw_text[:200]}"
    )

def _extract_json_block(text: str) -> str | None:
    """Extract json block."""
    start = -1
    open_char = None
    close_char = None

    for i, ch in enumerate(text):
        if ch == '{':
            start = i
            open_char = '{'
            close_char = '}'
            break
        elif ch == '[':
            start = i
            open_char = '['
            close_char = ']'
            break

    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == '\\' and in_string:
            escape_next = True
            continue

        if ch == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None
