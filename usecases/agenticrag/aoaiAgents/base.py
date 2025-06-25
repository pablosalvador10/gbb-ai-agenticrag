from __future__ import annotations

"""
rt_agent.py – Direct Azure OpenAI chat completions agent.

New in this version
-------------------
• Accepts API parameters directly for Azure OpenAI.
• Provides a `run()` method to call AzureOpenAIManager.generate_chat_response.
• Removed YAML, websocket, and prompt manager dependencies.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.aoai.aoai_helper import AzureOpenAIManager
from usecases.agenticrag.aoaiAgents.prompt_store.prompt_manager import PromptManager


class AzureOpenAIAgent:
    """Agent for Azure OpenAI chat completions, supporting YAML or direct params."""

    CONFIG_PATH: str | Path = "agent.yaml"

    def __init__(
        self,
        config_path: Optional[str | Path] = None,
        api_key: str = None,
        api_version: str = None,
        azure_endpoint: str = None,
        chat_model_name: str = None,
        **kwargs,
    ):
        self._cfg = None
        self.system_prompt_path = None
        self.user_prompt_path = None
        if config_path:
            cfg_path = Path(config_path or self.CONFIG_PATH).expanduser().resolve()
            try:
                with cfg_path.open("r", encoding="utf-8") as fh:
                    self._cfg = yaml.safe_load(fh) or {}
            except Exception as e:
                raise RuntimeError(f"Failed to load YAML config: {e}")
            self._validate_cfg()
            m = self._cfg["model"]
            self.api_key = (
                api_key or self._cfg.get("api_key") or os.getenv("AZURE_OPENAI_KEY")
            )
            self.api_version = (
                api_version
                or self._cfg.get("api_version")
                or os.getenv("AZURE_OPENAI_API_VERSION")
            )
            self.azure_endpoint = (
                azure_endpoint
                or self._cfg.get("azure_endpoint")
                or os.getenv("AZURE_OPENAI_API_ENDPOINT")
            )
            self.chat_model_name = (
                chat_model_name
                or m["deployment_id"]
                or os.getenv("AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID")
            )
            self.metadata = self._cfg.get("agent", {})
            # Capture system and user prompt paths if present
            prompts_cfg = self._cfg.get("prompts", {})
            self.system_prompt_path = prompts_cfg.get("system_path")
            self.user_prompt_path = prompts_cfg.get("user_path")
        else:
            self.api_key = api_key or os.getenv("AZURE_OPENAI_KEY")
            self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION")
            self.azure_endpoint = azure_endpoint or os.getenv(
                "AZURE_OPENAI_API_ENDPOINT"
            )
            self.chat_model_name = chat_model_name or os.getenv(
                "AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID"
            )
            self.metadata = {}
        self.aoai = AzureOpenAIManager(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.azure_endpoint,
            chat_model_name=self.chat_model_name,
        )
        self.prompt_manager = PromptManager()

    def _validate_cfg(self) -> None:
        required = [
            ("agent", ["name"]),
            ("model", ["deployment_id"]),
        ]
        for section, keys in required:
            if section not in self._cfg:
                raise ValueError(f"Missing '{section}' section in YAML config.")
            for key in keys:
                if key not in self._cfg[section]:
                    raise ValueError(f"Missing '{section}.{key}' in YAML config.")

    async def run(
        self,
        user_prompt: str,
        system_message_content: str = "You are an AI assistant that helps people find information. Please be precise, polite, and concise.",
        response_format: str = "json_object",
        conversation_history=None,
        **kwargs,
    ):
        conversation_history = conversation_history or []
        return await self.aoai.generate_chat_response(
            query=user_prompt,
            conversation_history=conversation_history,
            system_message_content=system_message_content,
            response_format=response_format,
            **kwargs,
        )

    def get_metadata(self) -> dict:
        """Return agent metadata from YAML or empty if not loaded."""
        return self.metadata

    def get_prompt_paths(self) -> dict:
        """Return the system and user prompt paths if loaded from YAML."""
        return {
            "system_prompt_path": self.system_prompt_path,
            "user_prompt_path": self.user_prompt_path,
        }
