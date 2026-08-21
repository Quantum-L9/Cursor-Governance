---
name: DORA State Auto-Gen
overview: Create a unified script that consolidates all repo index extraction into a single auto-generated `.dora/state.yaml` file, replacing the current multi-file export approach with a structured YAML format suitable for LLM context and project state tracking.
todos:
  - id: create-generator
    content: Create scripts/generate_dora_state.py with all extractors
    status: pending
  - id: docker-extractor
    content: Implement docker-compose.yml parser for services/ports/depends_on
    status: pending
  - id: env-extractor
    content: Merge env extraction from code, .env.example, and docker-compose
    status: pending
  - id: yaml-output
    content: Generate structured YAML output with proper nesting
    status: pending
  - id: makefile-integration
    content: Add dora-update and dora-check targets to Makefile
    status: pending
  - id: test-run
    content: Run generator and verify output matches expected structure
    status: pending
  - id: deprecate-old
    content: Mark tools/export_repo_indexes.py as deprecated or refactor
    status: pending
---

# DORA State Auto-Generator

## Architecture

```mermaid
flowchart TD
    subgraph sources [Source Files]
        REQ[requirements.txt]
        DC[docker-compose.yml]
        PY[Python files]
        ENV[env.example]
        MIG[migrations/*.sql]
        CFG[config/*.yaml]
    end
    
    subgraph extractors [Extractors]
        E1[dependencies]
        E2[docker_services]
        E3[api_surface]
        E4[entry_points]
        E5[environment_vars]
        E6[repo_structure]
        E7[migrations]
        E8[class_defs]
        E9[config_files]
    end
    
    subgraph output [Output]
        YAML[.dora/state.yaml]
    end
    
    REQ --> E1
    DC --> E2
    PY --> E3
    PY --> E4
    PY --> E6
    PY --> E8
    ENV --> E5
    DC --> E5
    MIG --> E7
    CFG --> E9
    
    E1 --> YAML
    E2 --> YAML
    E3 --> YAML
    E4 --> YAML
    E5 --> YAML
    E6 --> YAML
    E7 --> YAML
    E8 --> YAML
    E9 --> YAML
```



## Implementation

### 1. Create the Generator Script

**File:** [`scripts/generate_dora_state.py`](scripts/generate_dora_state.py)Refactor extractors from [`tools/export_repo_indexes.py`](tools/export_repo_indexes.py) into YAML-native output:| Extractor | Source | Notes ||-----------|--------|-------|| `extract_dependencies()` | `generate_dependencies()` | Parse all `requirements*.txt` || `extract_docker_services()` | NEW | Parse `docker-compose.yml` services, ports, depends_on || `extract_api_surface()` | `generate_api_surfaces()` | Find APIRouter instances || `extract_entry_points()` | `generate_entrypoints()` | FastAPI apps + `__main__` scripts || `extract_environment_vars()` | `generate_env_refs()` | From code + `.env.example` + docker-compose || `extract_repo_structure()` | `generate_tree()` | Directory tree as nested dict || `extract_migrations()` | NEW | List `migrations/*.sql` || `extract_config_files()` | `generate_config_files()` | YAML/JSON/TOML configs || `extract_class_definitions()` | `generate_class_definitions()` | Optional, for LLM context |

### 2. YAML Output Structure

```yaml
# L9 DORA Workflow State
# AUTO-GENERATED - DO NOT EDIT MANUALLY
updated: "2025-12-18T12:00:00Z"
version: "2.0.0"

project:
  name: "L9 Unified Runtime"
  description: "AI Agent Runtime..."

dependencies:
  requirements.txt:
        - fastapi>=0.115.0
        - uvicorn[standard]>=0.30.0
  requirements_memory_substrate.txt:
        - asyncpg>=0.29.0

docker_services:
  postgres:
    image: pgvector/pgvector:pg16
    ports: ["5432:5432"]
    depends_on: []
  l9-api:
    build: deploy/Dockerfile.l9_api
    ports: ["8000:8000"]
    depends_on: [postgres, l9-memory-api]

environment_variables:
  from_code: [OPENAI_API_KEY, DATABASE_URL, ...]
  from_docker_compose: [POSTGRES_USER, POSTGRES_PASSWORD, ...]

api_surface:
  api:
        - {file: api/agent_routes.py, variable: router}
        - {file: api/webhook_slack.py, variable: router}
  services:
        - {file: services/research/research_api.py, variable: router}

entry_points:
    - file: api/server.py
    type: FastAPI
    title: "L9 Phase 2 Secure AI OS"
    routes: ["/", "/ws/agent", "/os/*", "/agent/*", "/memory/*"]
    - file: mac_agent/runner.py
    type: Script

migrations:
    - {file: "0001_init_memory_substrate.sql"}
    - {file: "0002_add_indexes.sql"}

repo_structure:
  api:
        - __init__.py
        - server.py
        - routes:
            - __init__.py
            - health.py
  memory:
        - substrate_models.py
        - substrate_service.py
```



### 3. Makefile Integration

Add to [`Makefile`](Makefile):

```makefile
dora-update:
	@echo "Regenerating .dora/state.yaml..."
	@python scripts/generate_dora_state.py

dora-check:
	@echo "Checking if .dora/state.yaml is stale..."
	@python scripts/generate_dora_state.py --check
```



### 4. Pre-commit Hook (Optional)

Create `.git/hooks/pre-commit` or add to existing:

```bash
#!/bin/bash
python scripts/generate_dora_state.py
git add .dora/state.yaml
```



### 5. Deprecate Old Export

After validation, the multi-file export in [`tools/export_repo_indexes.py`](tools/export_repo_indexes.py) can be:

- Marked as deprecated
- Refactored to read from `.dora/state.yaml` and format for external LLM use
- Or removed entirely if `.dora/state.yaml` serves all use cases

## Key Decisions

1. **Single file vs multi-file:** Single `.dora/state.yaml` for internal use; can still generate txt files for Dropbox export if needed
2. **Automation level:** Start with Makefile target, add pre-commit hook after validation
3. **Backward compatibility:** Keep `tools/export_repo_indexes.py` working until migration complete

## Not Included

- Manual phase/progress tracking (stays manual in a separate section)