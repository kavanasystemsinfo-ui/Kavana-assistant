# ADR-005: Coste cero y decisiones tomadas por presupuesto

> **Estado:** Aceptado
> **Ámbito:** KAVANA Assistant (RAG + LLM para maquinaria industrial)
> **Relación:** Continúa el registro de decisiones iniciado en
> `docs/technical-documentation.md` §6 (ADR-001 a ADR-004).

## Contexto

KAVANA Assistant es hoy una pieza de portafolio con un único usuario real, su autor, y no genera ingresos. El proyecto se construye sobre un VPS que ya estaba contratado y sobre el tramo gratuito de un proveedor de modelos, con el objetivo explícito de mantenerse en 0 €/mes de coste marginal.

Ese objetivo no es un detalle de despliegue: condiciona qué modelo se usa, dónde vive la base vectorial, cómo se autentican los usuarios y hasta qué punto se puede crecer sin tocar nada. Un RAG de producción con usuarios de pago tomaría varias de estas decisiones al revés. Este ADR deja escrito qué se decidió por presupuesto y bajo qué condiciones habría que revisarlo, para que la deuda no se descubra cuando ya haya un cliente delante.

## Decisión

Se acepta el coste cero como restricción de diseño de la versión actual y se resuelven las cinco partidas con coste variable a favor de la opción gratuita:

1. **Modelo:** OpenRouter como proveedor por defecto (`LLM_BASE_URL=https://openrouter.ai/api/v1`) con `LLM_MODEL=meta-llama/llama-3.1-8b-instruct`, propuesto en `.env.example` por ser un modelo gratuito. El código mantiene `gpt-4o-mini` como valor por defecto interno y la documentación técnica estima el salto a ese modelo en ~2-5 €/mes para 1.000 consultas/día.
2. **Embeddings:** los que ChromaDB trae por defecto (`all-MiniLM-L6-v2`), ejecutados en la propia máquina. Sin API de embeddings no hay coste por token indexado y el indexado funciona sin red.
3. **Base vectorial:** ChromaDB embebido y persistente en disco (`PersistentClient`), sin servidor dedicado.
4. **Autenticación:** JWT propio (HS256 sobre `JWT_SECRET`, contraseñas con SHA256 y usuarios por `ASSISTANT_USERS`), sin proveedor de identidad.
5. **Hosting:** un único contenedor en el VPS existente, que la documentación contabiliza como 0 € extra.

Como consecuencia del mismo criterio, el sistema no incorpora LangChain, no tiene CDN, no tiene entorno de preproducción y no tiene capa de cuotas por usuario. Nada de eso se descarta por criterio técnico, sino por ser coste recurrente que hoy no se puede justificar.

## Alternativas evaluadas

| Partida | Elegido hoy (coste 0 €) | Alternativa descartada | Motivo de la elección, según el repositorio |
|---------|-------------------------|------------------------|---------------------------------------------|
| Modelo | OpenRouter con `meta-llama/llama-3.1-8b-instruct` | OpenAI con `gpt-4o-mini` | `.env.example` recomienda OpenRouter «para modelos gratuitos»; el modelo de pago queda como estimación de ~2-5 €/mes en la documentación, sin contratar |
| Embeddings | `all-MiniLM-L6-v2` por defecto de ChromaDB, en local | Embeddings servidos por API | El cálculo corre en la máquina: 0 € y sin dependencia de red en el indexado |
| Base vectorial | ChromaDB embebido | Pinecone o Qdrant (ADR-002) | ChromaDB «es suficiente para miles de documentos» y se levanta con `pip install`; las gestionadas son para millones de documentos y equipos dedicados |
| Orquestación | Llamadas directas a la API, sin framework | LangChain (ADR-001) | LangChain añade ~500 MB de dependencias para un RAG simple con un único tipo de consulta |
| Autenticación | JWT propio con SHA256 | Supabase Auth (ADR-004) | Evitar una dependencia externa y su coste en un microservicio ligero; se sustituirá por el SSO de V3 cuando el cliente lo tenga |
| Hosting | Contenedor único en el VPS existente | Servicio gestionado o clúster | «Docker (VPS existente): 0 € extra», mismo VPS que el resto de servicios |
| Entrega del frontend | Estático servido por el propio FastAPI | CDN | El `dist` de React/Vite ya se monta en la misma aplicación; no hay tráfico que justifique una CDN |

## Consecuencias

**A favor**

- Coste marginal de 0 €/mes con el modelo gratuito, lo que permite mantener el sistema encendido indefinidamente sin ingresos.
- Menos piezas móviles: sin LangChain, sin proveedor de identidad, sin base vectorial gestionada y sin CDN. Todo el sistema cabe en un contenedor y su volumen.
- El indexado y la recuperación funcionan sin red, porque los embeddings son locales.
- La ruta de migración está escrita de antemano: los ADR-001, 002 y 004 ya identifican qué se sustituye y por qué.

**En contra (deuda asumida a conciencia)**

- El tramo gratuito del proveedor impone la cuota, y el repositorio no la controla: por encima de ese límite el asistente deja de responder sin que el proyecto tenga forma de facturar el exceso.
- El corpus es de 19 entradas escritas a mano en dos manuales JSON, no de documentación real de fabricante; la calidad de la recuperación medida con `eval/rag_eval.py` (recall@k sobre 10 preguntas) no es extrapolable a un parque de máquinas real.
- SHA256 sin sal para contraseñas y un usuario por defecto son aceptables para un único usuario y no lo son para usuarios de un cliente.
- Sin réplicas, sin copias de seguridad automáticas del volumen vectorial y sin preproducción: el sistema no está preparado para una caída que afecte a un tercero.
- El filtro por máquina que la API acepta no se aplica en la consulta; el aislamiento por cliente exigiría metadatos y permisos que hoy no existen.

## Señal de revisión

Este ADR debe revisarse cuando ocurra cualquiera de estas cosas:

1. Aparece el primer usuario distinto del autor, sea cliente que paga o usuario en pruebas de un tercero.
2. El consumo del modelo se sale del tramo gratuito del proveedor o la estimación de ~2-5 €/mes deja de ser teórica y pasa a ser una línea de factura.
3. El corpus crece por encima de los dos manuales JSON actuales, en especial si entra documentación de fabricante con revisión humana o más de un cliente con manuales propios.
4. El recall@k de `eval/rag_eval.py` se estanca por debajo de lo que exige el caso de uso y la calidad pasa a ser más importante que el coste.
5. Se aborda la fase 3 del roadmap (tool calling contra la base de datos en vivo) o la integración con KAVANA V3, porque ambas obligan a replantear autenticación, permisos y aislamiento.
