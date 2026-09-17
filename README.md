# KAVANA Assistant IA

Asistente técnico con IA para maquinaria industrial: permite a un operario de fábrica preguntar en lenguaje natural por el funcionamiento, los códigos de error y el mantenimiento de sus máquinas (perfiladoras, plegadoras, etc.), y responde con recuperación sobre manuales técnicos reales (RAG) más un LLM.

Es un microservicio independiente —FastAPI + ChromaDB + llamadas directas al proveedor del modelo, sin LangChain— pensado para funcionar standalone o como módulo integrado en KAVANA V3 (MES). El frontend es una app React + Vite que el propio backend sirve como estático.

## 💰 Cómo está construido y cómo lo construiría con presupuesto

KAVANA Assistant es, hoy, una pieza de portafolio con un único usuario real (su autor) y un objetivo de coste de 0 €/mes: por eso cada pieza tecnológica se ha elegido por lo que cuesta mantenerla encendida, no por lo que aguanta a escala. Lo que hay en el repositorio es un sistema funcional, con tests y evaluación de recuperación, montado sobre el plan gratuito de un proveedor de modelos y sobre el VPS que ya estaba pagado. Lo que sigue es, partida a partida, qué hay hoy, por qué está así y qué cambiaría el día que esto lo use gente que no soy yo.

- **Modelo de IA:** hoy el `.env.example` apunta a OpenRouter con `LLM_MODEL=meta-llama/llama-3.1-8b-instruct`, y el propio archivo recomienda OpenRouter «para modelos gratuitos»; el repositorio no fija ninguna cuota en número, porque es el proveedor quien la impone y por eso el proyecto se queda en el tramo gratuito. El código, en cambio, trae `gpt-4o-mini` como modelo por defecto y la documentación técnica estima ~2-5 €/mes para 1.000 consultas/día con ese modelo. Con usuarios reales: modelo de pago con acuerdo de nivel de servicio, elegido por calidad de respuesta, y la estimación de la documentación convertida en factura real.
- **Embeddings:** se usan los embeddings por defecto de ChromaDB (`all-MiniLM-L6-v2`, según la documentación técnica), que corren en la propia máquina. No hay API de embeddings, no hay coste por token indexado y el sistema funciona aunque no haya red. Con usuarios reales: modelo de embeddings servido por API, dimensiones mayores y reindexación controlada cuando cambie el modelo.
- **Base vectorial:** ChromaDB en modo embebido y persistente en disco (`PersistentClient`, colección `machine_manuals` con distancia coseno). Cero servidores extra y cero euros; el ADR-002 del repositorio ya asume que ChromaDB basta para miles de documentos y que Pinecone o Qdrant son para millones. Con usuarios reales: base vectorial gestionada, con réplica, copias de seguridad y aislamiento por cliente.
- **Corpus:** hoy hay dos manuales JSON en `data/manuals/` (Perfiladora CNC PF-2000, 13 entradas; Plegadora CNC PH-100T, 6 entradas), 19 entradas indexables escritas a mano, y `eval/rag_eval.py` con 10 preguntas reales de operario para medir recall@k. Es suficiente para demostrar el flujo completo, no para cubrir un parque de máquinas. Con usuarios reales: ingesta de los PDF de cada fabricante con revisión humana, versionado por máquina y por modelo, y permisos para que cada cliente solo recupere sus manuales.
- **Autenticación:** JWT HS256 firmado con `JWT_SECRET` y contraseñas con SHA256, con un usuario por defecto y posibilidad de añadir usuarios por la variable `ASSISTANT_USERS`. No hay proveedor de identidad, así que no hay coste ni cuota. La alternativa de Supabase Auth se descartó en el ADR-004 precisamente por ser una dependencia externa para un microservicio ligero. Con usuarios reales: SSO (el módulo se sustituye por el de V3 cuando el cliente lo tiene), hashing con bcrypt o argon2 y rotación de secretos.
- **Aislamiento y exposición:** el CORS dejó de ser `*` y pasa a una lista blanca configurable por la variable `CORS_ORIGINS`, cuyo valor por defecto son solo orígenes locales. Hoy el sistema se levanta en el mismo VPS, sin dominio público ni capa de cuotas. Con usuarios reales: dominio propio con HTTPS, límite de peticiones por usuario, trazas de uso y alertas de consumo del proveedor del modelo.
- **Hosting:** un único contenedor definido en `docker-compose.yml` (TZ Europe/Madrid, red del host, volúmenes para `data` y `chromadb`) sobre el VPS que ya estaba contratado; la documentación técnica lo cuenta como 0 € extra. No hay staging, ni réplicas, ni copias de seguridad automáticas. Con usuarios reales: entorno de preproducción, réplicas detrás de un balanceador, copias de seguridad del volumen vectorial y monitorización con alertas.
- **Frontend y entrega:** app React + Vite (`frontend/`) cuyo `dist` se sirve como estático desde el propio FastAPI (`app.mount("/", StaticFiles(...))`), con proxy `/api` solo en desarrollo. No hay CDN ni coste de distribución. Con usuarios reales: build servido por CDN, PWA instalable para el operario en planta y separación real del tráfico de API.

Lo que no cambia entre los dos escenarios es el diseño: RAG directo sin LangChain, ChromaDB como almacén vectorial con distancia coseno, FastAPI como única puerta de entrada, el mismo prompt de sistema que obliga a responder solo con el contexto recuperado y a decir «no lo sé» cuando el manual no cubre la pregunta, y la misma batería de 18 tests y de 10 preguntas de evaluación como red de seguridad.

## Instalación

Requisitos: Docker Engine 24+ (o Python 3.11+ para ejecutarlo a mano) y una clave del proveedor del modelo.

```bash
git clone https://github.com/kavanasystemsinfo-ui/Kavana-assistant.git
cd Kavana-assistant
cp .env.example .env    # edita OPENROUTER_API_KEY y JWT_SECRET
docker compose up -d
```

Al arrancar, el servicio indexa solo los manuales que encuentre en `data/manuals/`.

Variables de entorno principales:

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `OPENROUTER_API_KEY` / `OPENAI_API_KEY` | Sí | — | Clave del proveedor del modelo |
| `LLM_MODEL` | No | `gpt-4o-mini` | Modelo a usar (el `.env.example` propone uno gratuito de OpenRouter) |
| `LLM_BASE_URL` | No | `https://openrouter.ai/api/v1` | Endpoint compatible con la API de OpenAI |
| `JWT_SECRET` | No | secreto de desarrollo | Clave de firma de los tokens |
| `ASSISTANT_USERS` | No | `admin@kavana.com` | Usuarios adicionales en JSON |
| `CHROMA_DB_PATH` | No | `/app/chromadb` | Ruta de persistencia vectorial |
| `CORS_ORIGINS` | No | orígenes locales | Lista blanca de CORS separada por comas |

## Uso

```bash
curl http://localhost:8000/health
```

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Qué significa el error E-101?"}'
```

Endpoints disponibles: `GET /health`, `POST /chat`, `POST /login`, `POST /upload`, `GET /machines`, `GET /stats`.

En desarrollo, el frontend se levanta aparte con `npm install && npm run dev` en `frontend/` (Vite en el puerto 5173 y proxy `/api` hacia el 8000).

## Pruebas y evaluación

```bash
python -m pytest tests/ -v      # 18 tests: 8 de rag, 5 de llm, 5 de auth
python -m eval.rag_eval         # recall@k sobre 10 preguntas reales de operario
```

## Documentación

- `docs/technical-documentation.md` — arquitectura, módulos, despliegue y registro de decisiones.
- `docs/adr/ADR-005-coste-cero-y-decisiones-por-presupuesto.md` — por qué cada pieza está donde está.

## Licencia

Uso interno — KAVANA Systems. Contacto: Jorge Adán, creador de KAVANA Systems.
