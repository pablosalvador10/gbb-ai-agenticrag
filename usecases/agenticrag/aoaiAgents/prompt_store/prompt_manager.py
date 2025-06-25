# prompt_manager.py
# This module provides the PromptManager class for managing and rendering Jinja2 templates
# used to generate prompts for the backend of the multi-agent RAG system.
# Templates are stored in a structured "templates" directory.

import os
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader

from usecases.agenticrag.settings import (
    AZURE_AI_FOUNDRY_FABRIC_AGENT,
    AZURE_AI_FOUNDRY_SHAREPOINT_AGENT,
    AZURE_AI_FOUNDRY_WEB_AGENT,
)
from utils.ml_logging import get_logger

logger = get_logger()


class PromptManager:
    """
    Manages loading and rendering Jinja2 templates for system and user prompts.
    Provides convenience methods for common prompt types and supports any custom template/context.
    """

    # Template filenames
    SYSTEM_PLANNER = "planner_system.jinja2"
    SYSTEM_VERIFIER = "verifier_system.j2"
    SYSTEM_SUMMARY = "summary_system.j2"

    USER_PLANNER = "user_planner.j2"
    USER_VERIFIER = "user_verifier.j2"
    USER_SUMMARY = "user_summary.j2"

    def __init__(self, template_dir: str = "templates"):
        """
        Initialize the PromptManager with the given template directory.
        Args:
            template_dir (str): Directory containing Jinja2 templates.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, template_dir)
        self.env = Environment(
            loader=FileSystemLoader(searchpath=template_path),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template_path = template_path
        try:
            templates = self.env.list_templates()
            logger.info(f"Loaded templates: {templates}")
        except Exception as e:
            logger.error(f"Error listing templates: {e}")

    def list_templates(self):
        """Return a list of available template filenames."""
        try:
            return self.env.list_templates()
        except Exception as e:
            logger.error(f"Error listing templates: {e}")
            return []

    def get_prompt(self, template_name: str, **context: Any) -> str:
        """
        Render a Jinja2 template with context.
        Args:
            template_name (str): Template filename.
            **context: Variables for template rendering.
        Returns:
            str: Rendered prompt.
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering '{template_name}': {e}")
            raise ValueError(f"Error rendering template '{template_name}': {e}")

    # System prompts
    def create_system_prompt_planner(self, **context) -> str:
        """Render the planner system prompt. Accepts extra context if needed."""
        return self.get_prompt(self.SYSTEM_PLANNER, **context)

    def create_system_prompt_verifier(self, **context) -> str:
        """Render the verifier system prompt. Accepts extra context if needed."""
        return self.get_prompt(self.SYSTEM_VERIFIER, **context)

    def create_system_prompt_summary(self, **context) -> str:
        """Render the summary system prompt. Accepts extra context if needed."""
        return self.get_prompt(self.SYSTEM_SUMMARY, **context)

    # User prompts
    def create_user_prompt_planner(self, user_query: str, **context) -> str:
        """
        Render the user planner prompt. Allows override of agent names and extra context.
        """
        return self.get_prompt(
            self.USER_PLANNER,
            user_query=user_query,
            fabric_agent=context.get(
                "fabric_agent", self.AZURE_AI_FOUNDRY_FABRIC_AGENT
            ),
            sharepoint_agent=context.get(
                "sharepoint_agent", self.AZURE_AI_FOUNDRY_SHAREPOINT_AGENT
            ),
            web_agent=context.get("web_agent", self.AZURE_AI_FOUNDRY_WEB_AGENT),
            **{
                k: v
                for k, v in context.items()
                if k not in ["fabric_agent", "sharepoint_agent", "web_agent"]
            },
        )

    def create_user_prompt_verifier(
        self,
        user_query: str,
        fabric_data_summary: Optional[str] = None,
        sharepoint_data_summary: Optional[str] = None,
        bing_data_summary: Optional[str] = None,
        **context,
    ) -> str:
        """
        Render the user verifier prompt. Allows extra context for future extensibility.
        """
        return self.get_prompt(
            self.USER_VERIFIER,
            user_query=user_query,
            fabric_data_summary=fabric_data_summary,
            sharepoint_data_summary=sharepoint_data_summary,
            bing_data_summary=bing_data_summary,
            **context,
        )

    def create_user_prompt_summary(self, user_query: str, **context) -> str:
        """
        Render the user summary prompt. Allows extra context for future extensibility.
        """
        return self.get_prompt(
            self.USER_SUMMARY,
            user_query=user_query,
            **context,
        )

    def render_custom_prompt(self, template_name: str, **context) -> str:
        """
        Render any custom template with arbitrary context.
        """
        return self.get_prompt(template_name, **context)
