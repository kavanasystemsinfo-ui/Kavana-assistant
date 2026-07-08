# KAVANA Assistant IA — Documentación Técnica

> **Proyecto:** Asistente Técnico Inteligente para Maquinaria Industrial  
> **Versión:** 1.0.0  
> **Fecha:** 08/07/2026  
> **Clasificación:** IT Consulting — Documentación de Arquitectura  
> **Repositorio:** `github.com/kavanasystemsinfo-ui/kavana-assistant`

---

## 1. Resumen Ejecutivo

**KAVANA Assistant** es un asistente técnico basado en IA que permite a operarios de fábrica consultar en lenguaje natural sobre el funcionamiento, errores y mantenimiento de maquinaria industrial (perfiladoras, plegadoras, robots láser, etc.).

**Arquitectura:** Microservicio independiente desacoplado, diseñado para funcionar standalone o como módulo integrado en KAVANA V3 (MES).

**Diferenciación:**
- **Sin dependencias pesadas:** No usa LangChain/CrewAI. LLM directo + ChromaDB.
- **RAG sobre documentos técnicos:** Indexa manuales reales y responde con precisión.
- **Tool Calling:** Puede consultar bases de datos en vivo (stock, OEE, producción).
- **TDD desde el día 1:** 13+ tests antes de escribir código de producción.

---

## 2. Arquitectura del Sistema

### 2.1 Diagrama de Capas

```
┌────────────────────────────────────────────────────────┐
│                   USUARIO (Operario)                    │
│   (Web / PWA Móvil / Dashboard V3)                      │
└──────────────────────┬────────────────────────────────┘
                       │ HTTPS / WSS
                       ▼
┌────────────────────────────────────────────────────────┐
│              FastAPI (Python 3.11+)                     │
│  /chat     → RAG + LLM                                 │
│  /upload   → Indexar manuales                          │
│  /machines → Catálogo de máquinas                      │
│  /login    → Auth JWT                                  │
│  /health   → Health check                              │
└──────┬──────────────────────┬─────────────────────────┘
       │                      │
       ▼                      ▼
┌──────────────┐    ┌──────────────────┐
│  ChromaDB     │    │  PostgreSQL      │
│  (Vectorial)  │    │  (Tools / V3)    │
│  Manuales     │    │  Stock, OEE...   │
│  técnicos     │    │                  │
└──────────────┘    └──────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────┐
│              OpenAI API (GPT-4o-mini)                   │
│  Sin LangChain — llamadas directas HTTP                 │
└────────────────────────────────────────────────────────┘
```

### 2.2 Flujo de Datos

#### Flujo A: Consulta sobre manual técnico (RAG)

```
Operario: "¿Qué significa el error E-101 en la perfiladora?"
                        │
                        ▼
            ┌─────────────────────┐
            │  1. FastAPI recibe   │
            │     /chat endpoint   │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │  2. ChromaDB busca   │
            │  fragmentos similares│
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │  3. Recupera        │
            │  entrada E-101:     │
            │  "Desviación de     │
            │  perfil hacia arriba"│
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │  4. OpenAI genera   │
            │  respuesta con      │
            │  contexto           │
            └─────────┬───────────┘
                      │
                      ▼
  "Error E-101 indica que el perfil se desvía hacia arriba.
   Posibles causas:
   - Desgaste en rodillos superiores estación 3
   - Presión hidráulica desigual
   
   Solución: verificar rodillos y ajustar presión 5 bar..."
```

#### Flujo B: Consulta a datos vivos (Tool Calling)

```
Operario: "¿Cuántos rodillos de repuesto quedan?"
                        │
                        ▼
            ┌─────────────────────┐
            │  1. LLM detecta que  │
            │  necesita tool       │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │  2. Ejecuta función  │
            │  get_stock("rodillo")│
            │  → consulta BD       │
            └─────────┬───────────┘
                      │
                      ▼
            ┌─────────────────────┐
            │  3. Responde con    │
            │  dato vivo: 142 uds │
            └─────────────────────┘
```

---

## 3. Stack Tecnológico

| Componente | Tecnología | Versión | Razón |
|------------|-----------|---------|-------|
| **API** | FastAPI + Uvicorn | 0.111+ | Async nativo, OpenAPI auto, rendimiento |
| **Vector DB** | ChromaDB | 0.5+ | Ligera, embedded, suficiente para miles de docs |
| **LLM** | OpenAI API directa | gpt-4o-mini | Sin dependencias (no LangChain), económico |
| **Auth** | JWT + SHA256 | — | Simple, sin dependencias externas |
| **Frontend** | React + Vite (planificado) | — | PWA-ready, dashboard o standalone |
| **Testing** | pytest | 9+ | TDD desde el día 1 |
| **Container** | Docker | — | Portable, mismo deploy en dev y prod |

---

## 4. Módulos

| Módulo | Archivo | Tests | Líneas | Propósito |
|--------|---------|-------|--------|-----------|
| `rag.py` | Motor de búsqueda vectorial | 8 | ~150 | Indexar y consultar manuales en ChromaDB |
| `llm.py` | Cliente OpenAI | 5 | ~120 | Generar respuestas con contexto RAG |
| `auth.py` | Autenticación JWT | 5 | ~100 | Login y tokens (independiente de V3) |
| `main.py` | API FastAPI | — | ~200 | Endpoints REST + orquestación |
| **Total** | **4 módulos** | **18** | **~570** | |

### 4.1 `rag.py` — Motor RAG

```python
rag = RAGEngine()
rag.index_manual(manual_json)     # Indexa un manual
results = rag.query("error E-101")  # Busca fragmentos similares
```

**Tecnología:** ChromaDB con `cosine` distance + embeddings por defecto (`all-MiniLM-L6-v2`).

**Estrategia de indexación:**
- Cada entrada del manual (error, mantenimiento, tip) se indexa como documento independiente
- Los IDs son MD5 del contenido para evitar duplicados
- Metadatos: máquina, sección, código, categoría

### 4.2 `llm.py` — Cliente OpenAI (sin LangChain)

```python
llm = LLMClient(api_key="sk-...")
answer = llm.ask("¿Qué significa E-101?", context=rag_results)
```

**Sin LangChain:** Llamadas HTTP directas a la API de OpenAI.  
**System prompt:** Ingeniero experto en maquinaria industrial.  
**Temperatura:** 0.3 (respuestas precisas, no creativas).

### 4.3 `auth.py` — Autenticación JWT

Independiente del módulo de auth de V3. Cuando se integre, se puede reemplazar por SSO.

**Usuarios por defecto:**

| Email | Contraseña | Rol |
|-------|-----------|-----|
| `admin@kavana.com` | `admin123` | admin |

**Configuración en producción:** Variable de entorno `ASSISTANT_USERS` con JSON.

### 4.4 `main.py` — API FastAPI

**Endpoints:**

| Ruta | Método | Auth | Descripción |
|------|--------|------|-------------|
| `/health` | GET | No | Health check + docs indexados |
| `/chat` | POST | No* | Preguntar al asistente |
| `/login` | POST | No | Obtener token JWT |
| `/upload` | POST | Sí* | Subir manual JSON |
| `/machines` | GET | No | Listar máquinas disponibles |
| `/stats` | GET | No | Estadísticas del sistema |

*Auth por implementar en endpoints de admin.

---

## 5. Datos de Ejemplo (MVP)

### Manual: Perfiladora CNC PF-2000

| Sección | Entradas | Ejemplo |
|---------|----------|---------|
| **Errores** | 5 códigos | E-101: Desviación de perfil |
| **Mantenimiento** | 4 rutinas | M-001: Lubricación cada 8h |
| **Tips** | 4 consejos | T-001: Perfil no cierra |

### Manual: Plegadora CNC PH-100T

| Sección | Entradas | Ejemplo |
|---------|----------|---------|
| **Errores** | 3 códigos | EP-101: Desviación de ángulo |
| **Tips** | 3 consejos | TP-001: Material agrietado |

**Total de entradas indexables:** 19

---

## 6. Registro de Decisiones Técnicas (ADRs)

### ADR-001: No usar LangChain

**Contexto:** LangChain es el estándar de facto para aplicaciones RAG.  
**Decisión:** NO usarlo. Llamadas directas a OpenAI + ChromaDB.  
**Razón:** LangChain añade ~500MB de dependencias, curva de aprendizaje, y abstracciones que ocultan el flujo real. Para un RAG simple + 1 tool, es overkill.  
**Consecuencia:** El código es más simple, más rápido de compilar, y más fácil de debuguear.

### ADR-002: ChromaDB sobre Pinecone/Qdrant

**Contexto:** Múltiples opciones de bases vectoriales.  
**Decisión:** ChromaDB (embedded, persistente local).  
**Razón:** Para un MVP con miles de documentos, ChromaDB es suficiente. Pinecone y Qdrant son para millones de docs con equipos dedicados. ChromaDB se despliega con un `pip install` y un `docker run`.  
**Migración futura:** Si se necesita escalar, la interfaz es la misma (todas usan cosine similarity).

### ADR-003: Microservicio independiente (no módulo forzado de V3)

**Contexto:** El asistente podría ser solo un módulo más de KAVANA V3.  
**Decisión:** Es un microservicio independiente con integración opcional a V3.  
**Razón:** El producto se vende standalone a empresas que no quieren el MES completo, y se integra con V3 cuando el cliente ya lo tiene.  
**Arquitectura:** Misma base de datos, endpoints adicionales, SSO compartido.

### ADR-004: JWT simple sobre Supabase Auth

**Contexto:** Podríamos usar Supabase Auth como en CleanStock.  
**Decisión:** JWT simple con SHA256 para el MVP.  
**Razón:** El asistente es un microservicio ligero. Supabase Auth añadiría una dependencia externa. Cuando se integre con V3 (que sí tiene auth), se reemplaza.  

---

## 7. Despliegue

### Requisitos

- Docker Engine 24+
- Python 3.11+
- API key de OpenAI

### Instalación

```bash
git clone git@github.com:kavanasystemsinfo-ui/kavana-assistant
cd kavana-assistant
cp .env.example .env   # Editar OPENAI_API_KEY
docker compose up -d
```

### Variables de Entorno

| Variable | Requerida | Default | Descripción |
|----------|-----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | API key de OpenAI |
| `JWT_SECRET` | ❌ | dev-secret | Secreto para firmar tokens |
| `ASSISTANT_USERS` | ❌ | admin/admin123 | Usuarios adicionales (JSON) |
| `CHROMA_DB_PATH` | ❌ | /app/chromadb | Ruta de persistencia vectorial |

### Verificación

```bash
curl http://localhost:8000/health
# {"status":"ok","documents_indexed":19,"llm_ready":false}

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Qué significa el error E-101?"}'
```

---

## 8. Pruebas (TDD)

```bash
cd kavana-assistant
source .venv/bin/activate
python -m pytest tests/ -v

# Resultado esperado: 18 passed
```

### Cobertura actual

| Módulo | Tests | Cubre |
|--------|-------|-------|
| `rag.py` | 8 | Indexación, consulta, límites, secciones |
| `llm.py` | 5 | Formateo contexto, análisis preguntas |
| `auth.py` | 5 | Login, tokens, errores |
| **Total** | **18** | |

---

## 9. Integración con KAVANA V3

Cuando un cliente tiene V3, el asistente se conecta a:

| Dato de V3 | Tool del asistente |
|------------|-------------------|
| `inventario_centros` | "¿Quedan rodillos?" |
| `registro_movimientos` | "¿Cuánto se produjo ayer?" |
| `incidencias` | "¿Esto ya pasó antes?" |
| `usuarios` | SSO (misma auth) |

**Arquitectura de integración:**

```
kavana-assistant (standalone)  ⇄  API de V3  ⇄  Misma BD PostgreSQL
       │                               │
       └── Auth JWT propia             └── Auth de V3 (SSO)
```

---

## 10. Roadmap

| Fase | Hito | Estado |
|------|------|--------|
| **1** | RAG + LLM + API básica | ✅ Completado |
| **2** | Frontend chat React | ⬜ Pendiente |
| **3** | Tool Calling (BD en vivo) | ⬜ Pendiente |
| **4** | Integración con V3 | ⬜ Pendiente |
| **5** | Panel admin + multi-tenant | ⬜ Pendiente |
| **6** | Deploy producción | ⬜ Pendiente |

---

## 11. Costes Estimados

| Recurso | Coste | Para qué |
|---------|-------|----------|
| OpenAI API | ~2-5€/mes | 1000 consultas/día con gpt-4o-mini |
| ChromaDB | 0€ | Embedded, sin servidor adicional |
| Docker (VPS existente) | 0€ extra | Mismo VPS que otros servicios |
| **Total** | **~2-5€/mes** | |

---

## 12. Licencia

Uso interno — KAVANA Systems  
Contacto: Jorge Adán — Creador de KAVANA Systems
