"""
Prompt construction for RAG pipeline.

Handles formatting of context, conversation history, and system prompts.
"""

from typing import List, Optional

from ..llm.base_provider import LLMMessage


class PromptBuilder:
    """
    Constructs prompts for RAG-enhanced conversations.

    Provides templates and formatting for different scenarios:
    - With/without context
    - With/without conversation history
    - Custom system prompts
    """

    DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant with access to the user's personal documents and knowledge base.

When provided with context from documents:
- Use the information to provide accurate, detailed answers
- Cite specific information when relevant
- If the context doesn't fully answer the question, acknowledge this
- Maintain consistency with previously discussed information

When no context is provided:
- Provide helpful general responses
- Suggest what information might be helpful
- Be clear when you don't have access to specific information"""

    RAG_CONTEXT_TEMPLATE = """Based on your documents, here is relevant information:

{context}

Please use this information to answer the following question."""

    def build_rag_messages(
        self,
        user_query: str,
        context: str = "",
        conversation_history: Optional[List[LLMMessage]] = None,
        system_prompt: Optional[str] = None,
    ) -> List[LLMMessage]:
        """
        Build message list for LLM with RAG context.

        Args:
            user_query: Current user question
            context: Retrieved document context
            conversation_history: Previous messages
            system_prompt: Custom system prompt

        Returns:
            Formatted message list for LLM
        """
        messages = []

        effective_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT
        messages.append(LLMMessage(role="system", content=effective_prompt))

        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append(msg)

        if context:
            formatted_query = self._format_query_with_context(user_query, context)
        else:
            formatted_query = user_query

        messages.append(LLMMessage(role="user", content=formatted_query))

        return messages

    def _format_query_with_context(self, query: str, context: str) -> str:
        """
        Format user query with retrieved context.

        Args:
            query: User's question
            context: Retrieved context

        Returns:
            Formatted query with context
        """
        formatted_context = self.RAG_CONTEXT_TEMPLATE.format(context=context)
        return f"{formatted_context}\n\nUser Question: {query}"

    def build_rerank_prompt(self, query: str, document: str) -> str:
        """
        Build prompt for document reranking.

        Args:
            query: User's query
            document: Document to evaluate

        Returns:
            Reranking prompt
        """
        return f"""Rate the relevance of this document to the query on a scale of 0-10.

Query: {query}

Document: {document}

Provide only a number between 0 and 10."""

    def build_summary_prompt(self, documents: List[str], query: str) -> str:
        """
        Build prompt for multi-document summarization.

        Args:
            documents: List of document texts
            query: User's query for focused summarization

        Returns:
            Summarization prompt
        """
        docs_text = "\n\n---\n\n".join(documents)

        return f"""Based on the following documents, provide a comprehensive answer to the user's question.

Documents:
{docs_text}

User Question: {query}

Provide a detailed answer that synthesizes information from all relevant documents."""

    def build_extraction_prompt(self, document: str, fields: List[str]) -> str:
        """
        Build prompt for structured information extraction.

        Args:
            document: Source document
            fields: Fields to extract

        Returns:
            Extraction prompt
        """
        fields_text = ", ".join(fields)

        return f"""Extract the following information from the document:

Fields to extract: {fields_text}

Document:
{document}

Provide the extracted information in a structured format."""
