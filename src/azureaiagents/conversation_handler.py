import logging
import re
from typing import Any, Dict, Generator, List, Optional, Tuple

from azure.ai.projects import AIProjectClient
from azure.core.exceptions import HttpResponseError

logger = logging.getLogger(__name__)


class MyChatMessage:
    """
    A simple message container class resembling a typical chat message.
    This can stand in for a Gradio ChatMessage or any other message format.

    Attributes:
        role (str): The role of the speaker (e.g. "user", "assistant").
        content (str): The textual content of the message.
        metadata (dict): Arbitrary metadata (e.g., status, references, etc.).
    """

    def __init__(self, role: str, content: str, metadata: Optional[Dict] = None):
        self.role = role
        self.content = content
        self.metadata = metadata or {}


def extract_bing_query(request_url: str) -> str:
    """
    Extracts a query string from Bing request URLs of the form:
      https://api.bing.microsoft.com/v7.0/search?q="latest news about Microsoft"
    Returns the extracted query string or the entire URL if no match.
    """
    match = re.search(r'q="([^"]+)"', request_url)
    if match:
        return match.group(1)
    return request_url


def convert_dict_to_mychatmessage(msg: dict) -> MyChatMessage:
    """
    Converts a legacy dict-based message into a MyChatMessage object.
    If 'metadata' is present, it’s attached to MyChatMessage.metadata.
    """
    return MyChatMessage(
        role=msg["role"], content=msg["content"], metadata=msg.get("metadata", {})
    )


class ConversationHandler:
    """
    Streams conversation events from an Azure AI Agent, handling partial tool calls
    and partial assistant text in real time—without depending on azure.ai.foundry.conversations.ChatMessage.

    Attributes:
        project_client (AIProjectClient): Authenticated Foundry Projects client.
        agent_id (str): The ID of the agent to handle this conversation.
        thread_id (str): The conversation thread ID (created beforehand).
        event_handler (AgentEventHandler): Custom event handler for partial logging.
        function_titles (dict): Mapping of function/tool names to user-friendly titles.
        conversation (List[MyChatMessage]): Running list of messages in MyChatMessage form.

    Typical usage:
        1) Construct with your project_client, agent/thread IDs, etc.
        2) Pass a user message + a dict-based history to stream_user_message(...).
        3) Iterate over the returned generator to see partial updates in real time.
    """

    def __init__(
        self,
        project_client: AIProjectClient,
        agent_id: str,
        thread_id: str,
        event_handler: Optional[Any] = None,
        function_titles: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        :param project_client: Authenticated AIProjectClient.
        :param agent_id: The ID of the Azure AI Agent.
        :param thread_id: The ID of the conversation thread.
        :param event_handler: A custom AgentEventHandler for partial message logging.
        :param function_titles: Optional dict of function/tool names to user-friendly titles.
        """
        self.project_client = project_client
        self.agent_id = agent_id
        self.thread_id = thread_id
        self.event_handler = event_handler

        self.function_titles = function_titles or {
            "fetch_weather": "☁️ fetching weather",
            "fetch_datetime": "🕒 fetching datetime",
            "fetch_stock_price": "📈 fetching financial info",
            "send_email": "✉️ sending mail",
            "file_search": "📄 searching docs",
            "bing_grounding": "🔍 searching bing",
        }

        # Internal store of MyChatMessage objects
        self.conversation: List[MyChatMessage] = []

        # Partial call tracking for function calls
        self.call_id_for_index: Dict[int, str] = {}
        self.partial_calls_by_index: Dict[int, Dict[str, str]] = {}
        self.partial_calls_by_id: Dict[str, Dict[str, str]] = {}
        self.in_progress_tools: Dict[str, MyChatMessage] = {}

    def get_function_title(self, fn_name: str) -> str:
        """
        Returns a user-friendly label for a given function/tool name.
        """
        return self.function_titles.get(fn_name, f"🛠 calling {fn_name}")

    def accumulate_args(self, storage: dict, name_chunk: str, arg_chunk: str) -> None:
        """
        Accumulates partial JSON for function calls.
        """
        if name_chunk:
            storage["name"] += name_chunk
        if arg_chunk:
            storage["args"] += arg_chunk

    def finalize_tool_call(self, call_id: str) -> None:
        """
        Creates or updates a MyChatMessage representing a tool/function call.
        If the call_id is new, we add a "pending" message. If it exists, we update it.
        """
        if call_id not in self.partial_calls_by_id:
            return

        data = self.partial_calls_by_id[call_id]
        fn_name = data["name"].strip()
        fn_args = data["args"].strip()
        if not fn_name:
            return

        # If we don't already have a message for this call_id, create one
        if call_id not in self.in_progress_tools:
            msg_obj = MyChatMessage(
                role="assistant",
                content=fn_args or "",
                metadata={
                    "title": self.get_function_title(fn_name),
                    "status": "pending",
                    "id": f"tool-{call_id}",
                },
            )
            self.conversation.append(msg_obj)
            self.in_progress_tools[call_id] = msg_obj
        else:
            # Update existing bubble
            msg_obj = self.in_progress_tools[call_id]
            msg_obj.content = fn_args or ""
            msg_obj.metadata["title"] = self.get_function_title(fn_name)

    def upsert_tool_call(self, tcall: dict) -> None:
        """
        Processes partial calls for:
         - "bing_grounding"
         - "file_search"
         - any "function" calls with partial name/arguments
        """
        t_type = tcall.get("type", "")
        c_id = tcall.get("id")

        # 1) Bing Grounding
        if t_type == "bing_grounding":
            request_url = tcall.get("bing_grounding", {}).get("requesturl", "")
            if not request_url.strip():
                return
            query_str = extract_bing_query(request_url)
            if not query_str.strip():
                return

            msg_obj = MyChatMessage(
                role="assistant",
                content=query_str,
                metadata={
                    "title": self.get_function_title("bing_grounding"),
                    "status": "pending",
                    "id": f"tool-{c_id}" if c_id else "tool-noid",
                },
            )
            self.conversation.append(msg_obj)
            if c_id:
                self.in_progress_tools[c_id] = msg_obj
            return

        # 2) File Search
        if t_type == "file_search":
            msg_obj = MyChatMessage(
                role="assistant",
                content="searching docs...",
                metadata={
                    "title": self.get_function_title("file_search"),
                    "status": "pending",
                    "id": f"tool-{c_id}" if c_id else "tool-noid",
                },
            )
            self.conversation.append(msg_obj)
            if c_id:
                self.in_progress_tools[c_id] = msg_obj
            return

        # 3) If not recognized or not a "function", do nothing
        if t_type != "function":
            return

        # 4) Partial function calls
        index = tcall.get("index")
        new_call_id = c_id
        fn_data = tcall.get("function", {})
        name_chunk = fn_data.get("name", "")
        arg_chunk = fn_data.get("arguments", "")

        # Store new call_id
        if new_call_id:
            self.call_id_for_index[index] = new_call_id

        final_call_id = self.call_id_for_index.get(index)
        if not final_call_id:
            # Accumulate partial data
            if index not in self.partial_calls_by_index:
                self.partial_calls_by_index[index] = {"name": "", "args": ""}
            self.accumulate_args(
                self.partial_calls_by_index[index], name_chunk, arg_chunk
            )
            return

        # Ensure partial_calls_by_id has a dict
        if final_call_id not in self.partial_calls_by_id:
            self.partial_calls_by_id[final_call_id] = {"name": "", "args": ""}

        # Merge partial data
        if index in self.partial_calls_by_index:
            old_data = self.partial_calls_by_index.pop(index)
            self.partial_calls_by_id[final_call_id]["name"] += old_data.get("name", "")
            self.partial_calls_by_id[final_call_id]["args"] += old_data.get("args", "")

        # Accumulate the new chunk
        self.accumulate_args(
            self.partial_calls_by_id[final_call_id], name_chunk, arg_chunk
        )
        self.finalize_tool_call(final_call_id)

    def stream_user_message(
        self, user_message: str, history: List[dict]
    ) -> Generator[
        Tuple[List[MyChatMessage], str], None, Tuple[List[MyChatMessage], str]
    ]:
        """
        Streams partial conversation updates in real time.

        Yields (conversation, "") at multiple points:
         - Right after adding the user's message,
         - Whenever a new partial tool call or partial assistant text arrives,
         - When the final "done" event is reached.

        :param user_message: The user’s new message text.
        :param history: The existing conversation in dict form (each dict with role, content, metadata).
        :yield: (updated_conversation, "") multiple times.
        :return: Final (updated_conversation, "") at completion.
        """

        ########################################################################
        # Step A) Convert history to MyChatMessage
        ########################################################################
        self.conversation = []
        for msg_dict in history:
            self.conversation.append(convert_dict_to_mychatmessage(msg_dict))

        # Add the user's message
        user_msg = MyChatMessage(role="user", content=user_message)
        self.conversation.append(user_msg)

        # Immediately yield once—could help if there's a UI needing to clear user input
        yield self.conversation, ""

        ########################################################################
        # Step B) Create user message in the Foundry agent's thread
        ########################################################################
        from azure.core.exceptions import HttpResponseError

        try:
            self.project_client.agents.create_message(
                thread_id=self.thread_id, role="user", content=user_message
            )
        except HttpResponseError as e:
            logger.error(f"Failed to create user message: {e}")
            raise

        ########################################################################
        # Step C) Stream partial events from the agent
        ########################################################################
        try:
            with self.project_client.agents.create_stream(
                thread_id=self.thread_id,
                assistant_id=self.agent_id,
                event_handler=self.event_handler,
            ) as stream:
                for item in stream:
                    # item is typically (event_type, event_data, ...)
                    event_type = item[0]
                    event_data = item[1]

                    logger.info(f"RECEIVED EVENT >>> {event_type} | {event_data}")

                    # Make sure no None in the conversation
                    self.conversation = [m for m in self.conversation if m is not None]

                    # 1) Partial tool calls
                    if event_type == "thread.run.step.delta":
                        step_delta = event_data.get("delta", {}).get("step_details", {})
                        if step_delta.get("type") == "tool_calls":
                            for tcall in step_delta.get("tool_calls", []):
                                self.upsert_tool_call(tcall)
                            yield self.conversation, ""

                    # 2) run_step
                    elif event_type == "run_step":
                        step_type = event_data["type"]
                        step_status = event_data["status"]

                        if step_type == "tool_calls" and step_status == "in_progress":
                            for tcall in event_data["step_details"].get(
                                "tool_calls", []
                            ):
                                self.upsert_tool_call(tcall)
                            yield self.conversation, ""

                        elif step_type == "tool_calls" and step_status == "completed":
                            for cid, msg_obj in self.in_progress_tools.items():
                                msg_obj.metadata["status"] = "done"
                            self.in_progress_tools.clear()
                            self.partial_calls_by_id.clear()
                            self.partial_calls_by_index.clear()
                            self.call_id_for_index.clear()
                            yield self.conversation, ""

                        elif (
                            step_type == "message_creation"
                            and step_status == "in_progress"
                        ):
                            msg_id = event_data["step_details"]["message_creation"].get(
                                "message_id"
                            )
                            if msg_id:
                                self.conversation.append(
                                    MyChatMessage(role="assistant", content="")
                                )
                            yield self.conversation, ""

                        elif (
                            step_type == "message_creation"
                            and step_status == "completed"
                        ):
                            yield self.conversation, ""

                    # 3) Partial assistant text
                    elif event_type == "thread.message.delta":
                        agent_msg = ""
                        for chunk in event_data["delta"]["content"]:
                            agent_msg += chunk["text"].get("value", "")

                        message_id = event_data["id"]

                        # find an existing assistant bubble if it matches ID
                        matching_msg = None
                        for msg in reversed(self.conversation):
                            if (
                                msg.metadata
                                and msg.metadata.get("id") == message_id
                                and msg.role == "assistant"
                            ):
                                matching_msg = msg
                                break

                        if matching_msg:
                            matching_msg.content += agent_msg
                        else:
                            # If no match, create or append to the last assistant bubble
                            if (
                                not self.conversation
                                or self.conversation[-1].role != "assistant"
                                or (
                                    self.conversation[-1].metadata
                                    and str(
                                        self.conversation[-1].metadata.get("id", "")
                                    ).startswith("tool-")
                                )
                            ):
                                self.conversation.append(
                                    MyChatMessage(role="assistant", content=agent_msg)
                                )
                            else:
                                self.conversation[-1].content += agent_msg

                        yield self.conversation, ""

                    # 4) Entire assistant message completed
                    elif event_type == "thread.message":
                        if (
                            event_data["role"] == "assistant"
                            and event_data["status"] == "completed"
                        ):
                            for cid, msg_obj in self.in_progress_tools.items():
                                msg_obj.metadata["status"] = "done"
                            self.in_progress_tools.clear()
                            self.partial_calls_by_id.clear()
                            self.partial_calls_by_index.clear()
                            self.call_id_for_index.clear()
                            yield self.conversation, ""

                    # 5) Final done
                    elif event_type == "thread.message.completed":
                        for cid, msg_obj in self.in_progress_tools.items():
                            msg_obj.metadata["status"] = "done"
                        self.in_progress_tools.clear()
                        self.partial_calls_by_id.clear()
                        self.partial_calls_by_index.clear()
                        self.call_id_for_index.clear()
                        yield self.conversation, ""
                        break

        except HttpResponseError as e:
            logger.error(f"Failed to stream conversation: {e}")
            raise

        # Return final conversation
        return self.conversation, ""
