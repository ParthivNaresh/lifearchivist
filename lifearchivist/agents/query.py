"""
Query agent for search and Q&A using RAG (Retrieval-Augmented Generation).
"""

import re
from typing import Any, Dict, List, Optional


class QueryAgent:
    """Agent responsible for handling search queries and Q&A using RAG."""

    def __init__(self, llamaindex_service, tool_registry):
        self.llamaindex_service = llamaindex_service
        self.tool_registry = tool_registry

    async def process(self, query: str) -> Dict[str, Any]:
        """Process a search query or question intelligently."""
        # Determine if this is a question or a search
        if self._is_question(query):
            return await self.answer_question(query)
        else:
            return await self.search_documents(query)

    def _is_question(self, query: str) -> bool:
        """Determine if a query is a question that requires RAG Q&A."""
        query_lower = query.lower().strip()

        # Question words at the beginning
        question_words = [
            "what",
            "how",
            "why",
            "when",
            "where",
            "who",
            "which",
            "can",
            "could",
            "should",
            "would",
            "is",
            "are",
            "was",
            "were",
            "do",
            "does",
            "did",
        ]

        # Check if starts with question word
        first_word = query_lower.split()[0] if query_lower.split() else ""
        if first_word in question_words:
            return True

        # Check if ends with question mark
        if query.strip().endswith("?"):
            return True

        # Check for questioning phrases
        questioning_phrases = [
            "tell me about",
            "explain",
            "describe",
            "summarize",
            "compare",
            "find information about",
        ]
        if any(phrase in query_lower for phrase in questioning_phrases):
            return True

        return False

    async def search_documents(
        self,
        query: str,
        mode: str = "hybrid",
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Search for documents matching the query."""
        try:
            # Use the search tool
            search_tool = self.tool_registry.get_tool("index.search")

            if not search_tool:
                return {"results": [], "total": 0, "error": "Search tool not found"}

            tool_result = await search_tool.execute(
                query=query, mode=mode, filters=filters, limit=limit
            )

            # Extract the actual search result from the tool execution result
            return dict(tool_result)

        except Exception as e:
            raise ValueError(e) from None

    async def answer_question(
        self, question: str, context_limit: int = 5, max_context_length: int = 4000
    ) -> Dict[str, Any]:
        """Answer a question using LlamaIndex RAG with fallback to custom implementation."""
        try:
            llamaindex_tool = self.tool_registry.get_tool("llamaindex.query")
            if llamaindex_tool:
                try:
                    result = await llamaindex_tool.execute(
                        question=question,
                        similarity_top_k=context_limit,
                    )

                    # Convert LlamaIndex response to our format
                    return {
                        "answer": result.get("answer", ""),
                        "confidence": result.get("confidence", 0.0),
                        "citations": self._convert_llamaindex_sources(
                            result.get("sources", [])
                        ),
                        "method": result.get("method", "llamaindex_rag"),
                        "metadata": result.get("metadata", {}),
                    }
                except Exception as e:
                    raise ValueError(e) from None
            else:
                return await self._custom_rag_implementation(
                    question, context_limit, max_context_length
                )

        except Exception as e:
            raise ValueError(e) from None

    def _convert_llamaindex_sources(self, sources: List[Dict]) -> List[Dict]:
        """Convert LlamaIndex sources to our citation format."""
        citations = []
        for source in sources:
            citations.append(
                {
                    "doc_id": source.get("document_id", ""),
                    "title": source.get("metadata", {}).get("title", "Document"),
                    "snippet": (
                        source.get("text", "")[:200] + "..."
                        if len(source.get("text", "")) > 200
                        else source.get("text", "")
                    ),
                    "score": source.get("score", 0.0),
                }
            )
        return citations

    async def _custom_rag_implementation(
        self, question: str, context_limit: int = 5, max_context_length: int = 4000
    ) -> Dict[str, Any]:
        """Custom RAG implementation as fallback."""
        # Step 1: Retrieve relevant documents using semantic search
        search_result = await self.search_documents(
            question,
            mode="semantic",
            limit=context_limit * 2,  # Get more to select best
        )

        if not search_result.get("results"):
            return {
                "answer": "I couldn't find any relevant documents to answer your question. Try rephrasing your question or check if relevant documents have been uploaded.",
                "confidence": 0.0,
                "citations": [],
                "method": "no_context",
            }

        # Step 2: Select and prepare context from top results
        context_info = await self._prepare_context(
            search_result["results"], max_context_length, question
        )

        if not context_info["context"]:
            return {
                "answer": "I found some potentially relevant documents, but couldn't extract sufficient context to answer your question.",
                "confidence": 0.1,
                "citations": context_info["citations"],
                "method": "insufficient_context",
            }

        # Step 3: Generate answer using Ollama
        ollama_tool = self.tool_registry.get_tool("llm.ollama")

        if not ollama_tool:
            return await self._fallback_answer(question, context_info["citations"])

        # Step 4: Call LLM with structured RAG prompt
        rag_response = await self._generate_rag_answer(
            ollama_tool, question, context_info
        )
        if not rag_response.get("answer"):
            return await self._fallback_answer(question, context_info["citations"])

        return {
            "answer": rag_response["answer"],
            "confidence": rag_response["confidence"],
            "citations": context_info["citations"],
            "search_results": search_result["results"][:context_limit],
            "context_length": len(context_info["context"]),
            "method": "custom_rag",
        }
        # return {
        #     "answer": f"I encountered an error while processing your question. Please try rephrasing your question or contact support if the issue persists. Error: {str(e)[:100]}",
        #     "confidence": 0.0,
        #     "citations": [],
        #     "method": "error",
        # }

    async def _prepare_context(
        self, search_results: List[Dict], max_length: int, question: str
    ) -> Dict[str, Any]:
        """Prepare context from search results for RAG."""
        context_pieces = []
        citations = []
        current_length = 0

        # Sort results by relevance score
        sorted_results = sorted(
            search_results, key=lambda x: x.get("score", 0), reverse=True
        )

        for i, result in enumerate(sorted_results):
            if current_length >= max_length:
                break

            # Get document content if available
            content = result.get("content", result.get("snippet", ""))
            if not content:
                continue

            # Extract relevant sentences based on the question
            relevant_text = self._extract_relevant_sentences(content, question)

            if not relevant_text:
                continue

            # Check if adding this would exceed limit
            if current_length + len(relevant_text) > max_length:
                # Truncate to fit
                remaining_space = max_length - current_length
                if remaining_space > 100:  # Only add if meaningful space remains
                    relevant_text = (
                        relevant_text[:remaining_space].rsplit(".", 1)[0] + "."
                    )
                else:
                    break

            # Add to context
            doc_title = result.get("title", f"Document {i+1}")
            context_piece = f"[Source: {doc_title}]\n{relevant_text}\n"
            context_pieces.append(context_piece)
            current_length += len(context_piece)

            # Add citation
            citations.append(
                {
                    "doc_id": result.get("document_id", ""),
                    "title": doc_title,
                    "snippet": (
                        relevant_text[:200] + "..."
                        if len(relevant_text) > 200
                        else relevant_text
                    ),
                    "score": result.get("score", 0),
                }
            )

        context = "\n".join(context_pieces)

        return {
            "context": context,
            "citations": citations,
            "total_sources": len(citations),
        }

    def _extract_relevant_sentences(
        self, text: str, question: str, max_sentences: int = 3
    ) -> str:
        """Extract sentences most relevant to the question."""
        if not text or not question:
            return text[:500] if text else ""

        # Split into sentences
        sentences = [
            s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 10
        ]

        if len(sentences) <= max_sentences:
            return text

        # Score sentences based on keyword overlap with question
        question_words = set(re.findall(r"\b\w+\b", question.lower()))
        question_words = {
            word for word in question_words if len(word) > 2
        }  # Filter short words

        scored_sentences = []
        for sentence in sentences:
            sentence_words = set(re.findall(r"\b\w+\b", sentence.lower()))
            overlap = len(question_words & sentence_words)
            scored_sentences.append((sentence, overlap))

        # Sort by score and take top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        best_sentences = [s[0] for s in scored_sentences[:max_sentences]]

        # Maintain original order
        result_sentences = []
        for sentence in sentences:
            if sentence in best_sentences:
                result_sentences.append(sentence)

        return ". ".join(result_sentences) + "." if result_sentences else text[:500]

    async def _generate_rag_answer(
        self, ollama_tool, question: str, context_info: Dict
    ) -> Dict[str, Any]:
        """Generate answer using Ollama with RAG prompt."""

        system_prompt = """You are a helpful AI assistant that answers questions based on provided context from documents. Your task is to:

1. Answer questions accurately using ONLY the information provided in the context
2. If the context doesn't contain enough information, say so clearly
3. Always cite which sources you're referencing
4. Be concise but thorough
5. If multiple sources say different things, acknowledge the discrepancy

Format your response as:
ANSWER: [Your answer here, referencing sources when needed]
CONFIDENCE: [A number from 0.0 to 1.0 indicating how confident you are in the answer]"""

        user_prompt = f"""Question: {question}

Context from documents:
{context_info['context']}

Please answer the question based on the provided context."""

        try:
            # Add timeout to prevent hanging due to Ollama memory issues
            import asyncio

            response = await asyncio.wait_for(
                ollama_tool.generate(
                    prompt=user_prompt,
                    system=system_prompt,
                    temperature=0.2,  # Low temperature for factual accuracy
                    max_tokens=1000,
                ),
                timeout=35.0,  # 35 second timeout
            )

            if not response:
                return {"answer": "", "confidence": 0.0}

            answer, confidence = self._parse_rag_response(response)
            return {"answer": answer, "confidence": confidence}

        except asyncio.TimeoutError:
            logger.error("Ollama generation timed out - likely memory issues")
            raise ValueError("Ollama timed out due to memory constraints") from None

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise ValueError(e) from None

    def _parse_rag_response(self, response: str) -> tuple[str, float]:
        """Parse the structured RAG response."""
        lines = response.strip().split("\n")
        answer = ""
        confidence = 0.5  # Default confidence

        current_section = None

        for line in lines:
            line = line.strip()
            if line.startswith("ANSWER:"):
                current_section = "answer"
                answer = line[7:].strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence_str = line[11:].strip()
                    confidence = float(confidence_str)
                    # Ensure confidence is between 0 and 1
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, IndexError):
                    confidence = 0.5
            elif current_section == "answer" and line:
                answer += " " + line

        # Fallback: if parsing failed, use the whole response as answer
        if not answer:
            answer = response.strip()
            # Try to extract confidence from the text
            import re

            conf_match = re.search(r"confidence[:\s]+([0-9.]+)", response.lower())
            if conf_match:
                try:
                    confidence = float(conf_match.group(1))
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    pass

        # Clean up the answer
        answer = answer.replace("ANSWER:", "").strip()

        return answer, confidence

    async def _fallback_answer(
        self, question: str, citations: List[Dict]
    ) -> Dict[str, Any]:
        """Provide a fallback answer when LLM is not available."""
        if not citations:
            return {
                "answer": "I couldn't find relevant information to answer your question.",
                "confidence": 0.0,
                "citations": [],
                "method": "fallback_no_citations",
            }

        # Create a simple answer based on available snippets
        snippets = [citation["snippet"] for citation in citations[:3]]

        answer = f"Based on the available documents, here's what I found: {' '.join(snippets)}"

        return {
            "answer": answer,
            "confidence": 0.3,  # Low confidence for fallback
            "citations": citations,
            "method": "fallback_simple",
        }
