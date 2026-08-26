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

HELP_COACH_INSTRUCTIONS = """You are the Iron House Help Coach for employees, foremen, and
management using Iron House OS. Answer only from the APPROVED HELP ARTICLES supplied with the
request. Use plain construction language, short sentences, and no more than five numbered steps.
Do not use general knowledge to fill a gap. If the approved articles do not support the answer, say
that no approved guide covers it and direct the user to their supervisor or the static Help search.
Never claim to change a record. Never authorize a purchase, approval, schedule, price, payroll item,
contract decision, or safety release. Never ask for or repeat passwords, API keys, SINs, banking,
medical, payroll, disciplinary, or restricted first-aid information. For safety questions, never
declare work safe; tell the user to stop work and contact the supervisor when conditions are unsafe
or unclear. Mention the supporting article title in the answer."""


class AssistantUnavailable(RuntimeError):
    pass


def _request_response(payload: dict) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise AssistantUnavailable(
            "Iron House Chat is installed but its separate OpenAI API credential has not been configured."
        )
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


def generate_help_reply(messages: list[dict[str, str]], project_context: str = "") -> str:
    settings = get_settings()
    return _request_response(
        {
            "model": settings.openai_chat_model,
            "instructions": f"{SYSTEM_INSTRUCTIONS}\n\nPROJECT BRAIN CONTEXT\n{project_context}",
            "input": messages,
            "max_output_tokens": 700,
        }
    )


def generate_help_coach_reply(
    message: str,
    approved_context: str,
    *,
    route: str = "",
    project_name: str = "",
) -> str:
    settings = get_settings()
    safe_page_context = f"Current IHOS path: {route or 'not supplied'}"
    if project_name:
        safe_page_context += f"\nSelected project label: {project_name}"
    return _request_response(
        {
            "model": settings.openai_chat_model,
            "instructions": (
                f"{HELP_COACH_INSTRUCTIONS}\n\n"
                f"SAFE PAGE CONTEXT\n{safe_page_context}\n\n"
                f"APPROVED HELP ARTICLES\n{approved_context}"
            ),
            "input": message,
            "max_output_tokens": 500,
        }
    )
