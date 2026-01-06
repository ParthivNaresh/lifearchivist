import json
from typing import Any, Dict, Optional


class ToolPromptBuilders:

    @staticmethod
    def document_search_system() -> str:
        return (
            "You are a retrieval strategist. "
            "Return ONLY compact JSON with keys: "
            "method ('semantic'|'keyword'|'hybrid'|'metadata'), "
            "query, filters (optional), top_k, semantic_weight, similarity_threshold, rerank_top_k."
        )

    @staticmethod
    def structured_extraction_system(
        full_schema: Dict[str, Any],
        instructions: str,
    ) -> str:
        schema_json = json.dumps(full_schema, indent=2, ensure_ascii=False)

        return (
            "You are a JSON extraction system. Your ONLY job is to output valid JSON.\n\n"
            "CRITICAL: Do NOT write explanations, summaries, or prose. Output ONLY the JSON object.\n\n"
            f"TASK:\n{instructions}\n\n"
            f"REQUIRED OUTPUT FORMAT:\n{schema_json}\n\n"
            "STRICT RULES:\n"
            "1. Output MUST be valid JSON matching the schema exactly\n"
            "2. Do NOT wrap in markdown code blocks (no ```json)\n"
            "3. Do NOT add any text before or after the JSON\n"
            "4. Do NOT write explanations or summaries\n"
            "5. If a field has no data, use null (not explanatory text)\n"
            "6. Include document_id in provenance array for citations\n\n"
            "OUTPUT ONLY THE JSON OBJECT NOW:"
        )

    @staticmethod
    def text_extraction_system(
        style: str,
        focus: Optional[str],
        max_output_length: int,
        include_citations: bool,
    ) -> str:
        style_guidance = {
            "concise": "Be brief and to the point. Use short sentences and avoid unnecessary details.",
            "detailed": "Provide comprehensive coverage with thorough explanations and context.",
            "bullet_points": "Use bullet points or numbered lists to organize information clearly.",
            "narrative": "Write in a flowing, story-like format that connects ideas smoothly.",
            "technical": "Use precise technical language and include relevant technical details.",
            "executive": "Focus on high-level insights and actionable takeaways for decision-makers.",
        }

        focus_guidance = {
            "overview": "Provide a comprehensive overview covering all major aspects.",
            "key_points": "Identify and highlight the most important points and findings.",
            "insights": "Extract deeper insights, patterns, and non-obvious observations.",
            "recommendations": "Focus on actionable recommendations and next steps.",
            "analysis": "Provide analytical perspective with critical evaluation.",
            "comparison": "Compare and contrast different aspects, highlighting similarities and differences.",
        }

        style_instruction = style_guidance.get(style, style_guidance["detailed"])
        focus_instruction = focus_guidance.get(focus, "") if focus else ""

        citation_instruction = (
            "\n\nCITATIONS:\n"
            "- Reference document IDs when making specific claims or citing information\n"
            "- Use format: [document_id] or (document_id) when referencing sources\n"
            "- Ensure all major points are attributed to source documents"
            if include_citations
            else ""
        )

        return (
            "You are a document analysis and summarization system. Your task is to extract, "
            "analyze, and present information from documents in clear, well-structured prose.\n\n"
            f"OUTPUT STYLE:\n{style_instruction}\n\n"
            + (f"FOCUS:\n{focus_instruction}\n\n" if focus_instruction else "")
            + f"LENGTH CONSTRAINT:\n"
            f"Target approximately {max_output_length} words. Be thorough but respect this constraint.\n"
            + citation_instruction
            + "\n\nCRITICAL RULES:\n"
            "1. Output ONLY the requested text content - no JSON, no metadata wrappers\n"
            "2. Do NOT add explanatory prefixes like 'Here is the summary:' or 'Based on the documents:'\n"
            "3. Start directly with the content\n"
            "4. Be factual and grounded in the provided document content\n"
            "5. Do NOT fabricate information not present in the documents\n"
            "6. If documents lack information on a topic, acknowledge this clearly\n"
            "7. Maintain professional tone and clarity throughout\n\n"
            "BEGIN YOUR RESPONSE NOW:"
        )
