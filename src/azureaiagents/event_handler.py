# event_handler.py

import logging

from azure.ai.projects.models import (
    AgentEventHandler,
    MessageDeltaChunk,
    RunStep,
    RunStepDeltaChunk,
    ThreadMessage,
    ThreadRun,
)

logger = logging.getLogger(__name__)


class MyEventHandler(AgentEventHandler):
    """
    Custom event handler to log partial text and run steps for debugging.
    """

    def __init__(self):
        super().__init__()
        self._current_message_id = None
        self._accumulated_text = ""

    def on_message_delta(self, delta: MessageDeltaChunk) -> None:
        if delta.id != self._current_message_id:
            if self._current_message_id is not None:
                print()
            self._current_message_id = delta.id
            self._accumulated_text = ""
            print("\nassistant > ", end="")

        partial_text = ""
        if delta.delta.content:
            for chunk in delta.delta.content:
                partial_text += chunk.text.get("value", "")
        self._accumulated_text += partial_text

        print(partial_text, end="", flush=True)

    def on_thread_message(self, message: ThreadMessage) -> None:
        if message.status == "completed" and message.role == "assistant":
            print()
            self._current_message_id = None
            self._accumulated_text = ""
        else:
            logger.debug(f"{message.role} message, status={message.status}")

    def on_thread_run(self, run: ThreadRun) -> None:
        logger.info(f"Run status changed to {run.status.name.lower()}")
        if run.status == "failed":
            logger.error(f"Agent run failed with error: {run.last_error}")

    def on_run_step(self, step: RunStep) -> None:
        logger.debug(
            f"Run step type={step.type.name.lower()}, status={step.status.name.lower()}"
        )

    def on_run_step_delta(self, delta: RunStepDeltaChunk) -> None:
        if delta.delta.step_details and delta.delta.step_details.tool_calls:
            for tcall in delta.delta.step_details.tool_calls:
                if getattr(tcall, "function", None) and tcall.function.name:
                    logger.info(f"tool call > {tcall.function.name}")

    def on_unhandled_event(self, event_type: str, event_data):
        logger.debug(f"Unhandled event > {event_type}: {event_data}")

    def on_error(self, data: str) -> None:
        logger.error(f"Event handler error: {data}")

    def on_done(self) -> None:
        print("\nDone.")
