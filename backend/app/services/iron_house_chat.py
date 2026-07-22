import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import get_settings


SYSTEM_INSTRUCTIONS = """You are Iron House Chat, the in-product help assistant for Iron House OS.
Be concise, practical, and safety-conscious. Help management understand and use the OS, including
projects, estimating, cost codes, financial controls, field operations, employee portals, equipment,
documents, and reporting. Never claim that you changed a record: this build is read-only. Never ask
for or repeat passwords, API keys, SINs, banking information, medical information, or payroll details.
If the answer depends on data you cannot see, say so and identify the exact OS page where it can be
checked. Distinguish guidance from legal, financial, engineering, and safety approval."""


class AssistantUnavailable(RuntimeError):
    pass


def generate_help_reply(messages: list[dict[str, str]]) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise AssistantUnavailable(
            "Iron House Chat is installed but its separate OpenAI API credential has not been configured."
        )
    payload = {
        "model": settings.openai_chat_model,
        "instructions": SYSTEM_INSTRUCTIONS,
        "input": messages,
        "max_output_tokens": 700,
    }
    request = Request(
        f"{settings.openai_api_base_url.rstrip('/')}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise AssistantUnavailable(f"The AI provider rejected the request ({exc.code}): {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise AssistantUnavailable("The AI provider is temporarily unreachable.") from exc

    output_text = result.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    for item in result.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"]).strip()
    raise AssistantUnavailable("The AI provider returned no answer.")

