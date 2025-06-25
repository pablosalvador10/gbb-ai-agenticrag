import json
import logging
import os
from typing import Optional, Set, Tuple

from azure.ai.projects import AIProjectClient
from azure.core.exceptions import HttpResponseError, ServiceRequestError
from azure.identity import DefaultAzureCredential


def process_citations(text_msg) -> str:
    """
    Given a text_message with .text.value and .text.annotations, append a
    **Citations** section with unique URL citations.
    """
    base = text_msg.text.value
    seen: Set[Tuple[str, str]] = set()

    for annot in getattr(text_msg.text, "annotations", []):
        uc = getattr(annot, "url_citation", None)
        if uc and uc.url:
            seen.add((annot.text, uc.url))

    if seen:
        base += "\n\n**Citations:**\n"
        for quote, url in seen:
            base += f"- **Quote**: {quote}  \n"
            base += f"  **URL**: [{url}]({url})\n"

    return base


def run_agent(
    project_client: AIProjectClient, agent_id: str, user_input: str
) -> Tuple[str, str]:
    """
    • Posts `user_input` to a new thread on `agent_id`.
    • Blocks until the run completes.
    • Gathers only the *real* assistant replies, enriches with citations.
    Returns (conversation_text, thread_id).
    """
    try:
        # 1) create thread & send question
        thread = project_client.agents.create_thread()
        project_client.agents.create_message(
            thread_id=thread.id, role="user", content=user_input
        )

        # 2) run & wait
        project_client.agents.create_and_process_run(
            thread_id=thread.id, agent_id=agent_id
        )

        # 3) collect & enrich only true assistant messages
        responses = ""
        pager = project_client.agents.list_messages(thread_id=thread.id)
        messages = pager.data if hasattr(pager, "data") else list(pager)

        for msg in messages:
            # only look at assistant turns
            if msg.role.lower() != "assistant":
                continue

            for text_msg in getattr(msg, "text_messages", []):
                content = text_msg.text.value.strip()

                # skip exact echoes of the prompt
                if content == user_input.strip():
                    continue

                enriched = process_citations(text_msg)
                responses += f"\n🤖 Assistant: {enriched}\n"

        return responses, thread.id
    except ServiceRequestError as e:
        logging.error(f"ServiceRequestError: {e}")
        return f"❌ Service request error: {e}", ""
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return f"❌ Unexpected error: {e}", ""
