import json

import requests

from backend.app.config import settings
from backend.app.utils.exceptions import ServiceUnavailableException

# Generation on a local model can take a while, especially on the first request
# after Ollama loads the model into memory.
REQUEST_TIMEOUT_SECONDS = 120


def _parse_reply(body: str) -> str:
    """Join the reply text from Ollama's response.

    Some Ollama versions stream newline-delimited JSON even when stream is False,
    so read every line rather than assuming a single JSON object.
    """
    parts = [
        json.loads(line)["message"]["content"]
        for line in body.splitlines()
        if line.strip()
    ]
    return "".join(parts).strip()


def chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    """Send a chat to Ollama and return the assistant's reply text.

    messages looks like [{"role": "system", "content": "..."}, {"role": "user", ...}].
    A low temperature keeps answers close to the rules text.

    Raises:
        ServiceUnavailableException: Ollama is unreachable, slow, or returned an error.
    """
    try:
        response = requests.post(
            f"{settings.ollama_url}/api/chat",
            json={
                "model": settings.llm_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature},
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return _parse_reply(response.text)
    except requests.exceptions.Timeout:
        raise ServiceUnavailableException("The language model took too long to respond")
    except (requests.exceptions.RequestException, KeyError, ValueError):
        raise ServiceUnavailableException("The language model is unavailable")
