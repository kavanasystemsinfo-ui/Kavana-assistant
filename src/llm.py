"""Módulo LLM — Conexión directa con OpenAI (sin LangChain)."""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

logger = logging.getLogger("kavana.assistant.llm")


class LLMClient:
    """Cliente ligero para LLM vía OpenAI o OpenRouter.
    
    Sin LangChain: llama directamente a la API.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", 
                 base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
        if not self.api_key:
            raise ValueError("Se requiere OPENROUTER_API_KEY o OPENAI_API_KEY")

    def ask(self, question: str, context: list[dict]) -> str:
        import openai

        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        # Construir contexto a partir de los fragmentos recuperados
        context_text = self._format_context(context)

        system_prompt = """Eres un asistente técnico experto en maquinaria industrial.
Tu función es ayudar a operarios de fábrica a diagnosticar y solucionar problemas
con sus máquinas: perfiladoras, plegadoras, robots láser, etc.

REGLAS:
1. Responde SIEMPRE basándote en el contexto proporcionado (manuales técnicos).
2. Si no encuentras la respuesta en el contexto, di que no lo sabes.
3. Sé claro, directo y usa lenguaje que un operario entienda.
4. Si el problema es un código de error, explica la causa y la solución paso a paso.
5. Cuando sea relevante, incluye consejos de prevención.
6. Responde en español, con el mismo tono que un compañero experimentado."""

        user_message = f"CONTEXTO (manuales técnicos):\n{context_text}\n\n---\n\nPREGUNTA DEL OPERARIO:\n{question}"
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        return response.choices[0].message.content or ""

    def _format_context(self, context: list[dict]) -> str:
        """Formatea los fragmentos de contexto para el prompt."""
        parts = []
        for i, c in enumerate(context, 1):
            machine = c.get("machine", "?")
            section = c.get("section", "?")
            code = c.get("code", "")
            content = c.get("content", "")
            header = f"[{i}] Máquina: {machine} | Sección: {section}"
            if code:
                header += f" | Código: {code}"
            parts.append(f"{header}\n{content}\n")
        return "\n".join(parts)

    def analyze_question(self, question: str) -> dict:
        """Determina si la pregunta necesita RAG, Tool o ambas."""
        import openai
        client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": """Analiza la pregunta del operario y determina:
- "type": "rag" si pregunta sobre manuales, errores, soluciones técnicas
- "type": "tool" si necesita datos en vivo (stock, producción, inventario)
- "type": "both" si necesita ambas

Responde SOLO con JSON: {"type": "rag"|"tool"|"both", "reason": "explicación breve"}"""},
                {"role": "user", "content": question},
            ],
            temperature=0.1,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        try:
            return json.loads(response.choices[0].message.content or "{}")
        except json.JSONDecodeError:
            return {"type": "rag", "reason": "fallback"}
