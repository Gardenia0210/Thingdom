"""Extract a JSON response string across arbitrary model chunk boundaries."""
import json
import re


class StreamingAiMessageExtractor:
    """Stream ai_message without leaking other structured response fields."""

    def __init__(self, on_token=None):
        self._on_token = on_token
        self.reset()

    def feed(self, args_chunk: str):
        """Keep partial keys and escape sequences until their input is complete."""
        if self._done:
            return
        self._buffer += args_chunk
        if self._position is None:
            match = re.search(r'"ai_message"\s*:\s*"', self._buffer)
            if not match:
                return
            self._position = match.end()
        while self._position < len(self._buffer):
            i = self._position
            char = self._buffer[i]
            if char == '"':
                self._done = True
                return
            if char == '\\':
                if i + 1 >= len(self._buffer):
                    return
                width = 6 if self._buffer[i + 1] == 'u' else 2
                if i + width > len(self._buffer):
                    return
                if width == 6 and 0xD800 <= int(self._buffer[i + 2:i + 6], 16) <= 0xDBFF:
                    width = 12
                    if i + width > len(self._buffer):
                        return
                char = json.loads('"' + self._buffer[i:i + width] + '"')
                self._position += width
            else:
                self._position += 1
            self._message_buffer += char
            if self._on_token:
                self._on_token(char)

    def get_accumulated_message(self) -> str:
        """Return only the decoded ai_message text received so far."""
        return self._message_buffer

    @property
    def is_done(self) -> bool:
        return self._done

    def reset(self):
        """Reuse this extractor for a new structured response."""
        self._buffer = ''
        self._position = None
        self._message_buffer = ''
        self._done = False
