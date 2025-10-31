"""
Prompt utilities for conversation system prompts.

Provides format-aware prompt construction based on user preferences.
"""

from typing import Optional


class PromptFormatter:
    """Handles system prompt formatting based on user preferences."""

    CONCISE_INSTRUCTION = (
        "\n\nIMPORTANT: Be concise and to the point. "
        "Provide clear, direct answers without unnecessary elaboration. "
        "Focus on the essential information needed to answer the question."
    )

    VERBOSE_INSTRUCTION = (
        "\n\nIMPORTANT: Provide comprehensive, detailed responses. "
        "Include relevant context, examples, and thorough explanations. "
        "Elaborate on key points and provide additional insights where helpful."
    )

    @classmethod
    def apply_response_format(
        cls, base_prompt: str, response_format: Optional[str] = None
    ) -> str:
        """
        Apply response format instructions to a base system prompt.

        Args:
            base_prompt: The original system prompt
            response_format: User preference for response format ('concise' or 'verbose')

        Returns:
            System prompt with format instructions appended
        """
        if not response_format:
            return base_prompt

        if response_format == "concise":
            return base_prompt + cls.CONCISE_INSTRUCTION
        elif response_format == "verbose":
            return base_prompt + cls.VERBOSE_INSTRUCTION
        else:
            return base_prompt

    @classmethod
    def get_default_prompt(cls, response_format: Optional[str] = None) -> str:
        """
        Get the default system prompt with format applied.

        Args:
            response_format: User preference for response format

        Returns:
            Default prompt with format instructions
        """
        base_prompt = "You are a helpful assistant that answers questions based on the provided context."
        return cls.apply_response_format(base_prompt, response_format)
