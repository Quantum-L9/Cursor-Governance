---
name: Add Persistence Substrates
overview: "Move substrate implementations from staging, add shared Protocol base class, field mapper, context managers, and integration tests. Address critical risks: Cypher injection, datetime serialization, import cycles."
todos:
  - id: preflight
    content: "Pre-flight validation: check staging files for ghost imports and known issues"
    status: pending
  - id: create-base
    content: Create world_model/substrates/ directory with base.py (PersistenceSubstrate Protocol) and field_mapper.py
    status: pending
  - id: copy-files
    content: Copy 3 substrate files from _pack_staging/ to world_model/ (not move yet)
    status: pending
  - id: fix-imports
    content: "Fix imports: world_model.state instead of interfaces, add TYPE_CHECKING guards"
    status: pending
  - id: fix-fields
    content: Update Entity/Relation field names using field_mapper (entity_id, entity_type, source_id, target_id)
    status: pending
  - id: fix-schema
    content: Replace EntityTypeSchema/RelationTypeSchema with dict-based store_entity_type(type_name, properties)
    status: pending
  - id: add-context-mgr
    content: Add __enter__/__exit__ context manager and connection() helper to all substrates
    status: pending
  - id: fix-neo4j
    content: "Audit and fix Neo4j Cypher queries: use parameterized queries, not f-strings"
    status: pending
  - id: fix-redis
    content: "Fix Redis datetime serialization: use .isoformat() for datetime fields"
    status: pending
  - id: add-exports
    content: Add substrate exports to world_model/__init__.py
    status: pending
  - id: add-tests
    content: Create tests/world_model/test_substrates.py with roundtrip tests
    status: pending
  - id: validate-cleanup
    content: Validate imports work, delete staging files
    status: pending
---

# Add Persistence Substrates Plan (Revised)

## Overview

Move complete substrate implementations from `world_model/_pack_staging/` to production, adding:

- Shared `PersistenceSubstrate` Protocol for polymorphism
- Programmatic field name mapping (staging ↔ production)
- Context manager support for auto-connect/disconnect
- Dict-based schema registry (replacing ghost classes)
- Integration tests for roundtrip verification

## Critical Risks Addressed

| Risk | Severity | Mitigation |

|------|----------|------------|

| Ghost imports (`EntityTypeSchema`) | CRITICAL | Replace with dict-based API |

| Neo4j Cypher injection | CRITICAL | Parameterized queries |

| Import cycle (`state.py` ↔ substrates) | HIGH | `TYPE_CHECKING` guards |

| Redis datetime serialization | MEDIUM | `.isoformat()` conversion |

| Transaction isolation | MEDIUM | `SERIALIZABLE` isolation |

## Implementation Steps (11 Steps)

### Step 0: Pre-Flight Validation

Verify staging file state before migration:

```bash
python -c "
import ast
for f in ['postgres_substrate.py', 'neo4j_substrate.py', 'redis_substrate.py']:
    path = f'world_model/_pack_staging/{f}'
    with open(path) as fp:
        content = fp.read()
    if 'EntityTypeSchema' in content:
        print(f'⚠️  {f}: EntityTypeSchema references found')
    if 'from world_model.interfaces import' in content:
        print(f'❌ {f}: Imports from interfaces (will fail)')
    if 'f\"' in content or \"f'\" in content:
        print(f'⚠️  {f}: f-string queries detected (check for injection)')
"
```

### Step 1: Create Substrate Base Protocol + Field Mapper

Create new directory structure:

```
world_model/substrates/
├── __init__.py
├── base.py          # PersistenceSubstrate Protocol
└── field_mapper.py  # Bidirectional field mapping
```

**base.py** - Contract all persistence backends must honor:

```python
from typing import Protocol, Optional, List
from world_model.state import Entity, Relation, WorldModelState

class PersistenceSubstrate(Protocol):
    """Contract all persistence backends must honor."""

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def store_entity(self, entity: Entity) -> None: ...
    def load_entity(self, entity_id: str) -> Optional[Entity]: ...
    def store_relation(self, relation: Relation) -> None: ...
    def load_relation(self, relation_id: str) -> Optional[Relation]: ...
    def sync_state_to_db(self, state: WorldModelState) -> None: ...
    def load_state_from_db(self) -> WorldModelState: ...
```

**field_mapper.py** - Centralized field name mapping:

```python
ENTITY_MAPPING = {
    "id": "entity_id",
    "type": "entity_type",
}

RELATION_MAPPING = {
    "id": "relation_id",
    "type": "relation_type",
    "source_entity_id": "source_id",
    "target_entity_id": "target_id",
}

def entity_to_db(entity: Entity) -> dict:
    """Convert Entity to DB-compatible dict."""
    return {
        "id": entity.entity_id,
        "type": entity.entity_type,
        "attributes": entity.attributes,
    }

def db_to_entity(row: tuple) -> Entity:
    """Convert DB row to Entity."""
    return Entity(
        entity_id=row[0],
        entity_type=row[1],
        attributes=row[2] or {},
    )
```

### Step 2: Copy Staging Files

Copy (not move) files to allow rollback:

```bash
cp world_model/_pack_staging/postgres_substrate.py world_model/postgres_substrate.py
cp world_model/_pack_staging/neo4j_substrate.py world_model/neo4j_substrate.py
cp world_model/_pack_staging/redis_substrate.py world_model/redis_substrate.py
```

### Step 3: Fix Import Statements (All 3 Files)

Replace imports in each substrate:

```python
# ❌ OLD (will fail):
from world_model.interfaces import Entity, Relation, EntityTypeSchema, RelationTypeSchema

# ✓ NEW:
from __future__ import annotations
import structlog
from typing import TYPE_CHECKING, Optional, List, Dict, Any

if TYPE_CHECKING:
    from world_model.state import WorldModelState

from world_model.state import Entity, Relation
from world_model.substrates.field_mapper import entity_to_db, db_to_entity, relation_to_db, db_to_relation
```

### Step 4: Fix Entity/Relation Field Names

Update all field references using the mapper functions:

**postgres_substrate.py** changes:

- `store_entity()`: Use `entity_to_db(entity)` instead of manual field access
- `load_entity()`: Use `db_to_entity(row)` instead of manual construction
- `store_relation()`: Use `relation_to_db(relation)`
- `load_relation()`: Use `db_to_relation(row)`

### Step 5: Replace Schema Classes with Dict API

Simplify `store_entity_type` and `store_relation_type`:

```python
# ❌ OLD (ghost class):
def store_entity_type(self, type_name: str, schema: EntityTypeSchema) -> None:
    cursor.execute(..., schema.description, schema.properties)

# ✓ NEW (dict-based):
def store_entity_type(self, type_name: str, description: str = "", properties: dict = None) -> None:
    """Store entity type schema."""
    properties = properties or {}
    cursor.execute(
        "INSERT INTO entity_types (type_name, description, properties) VALUES (%s, %s, %s) ON CONFLICT ...",
        (type_name, description, json.dumps(properties))
    )
```

### Step 6: Add Context Manager Support

Add to all 3 substrate classes:

```python
from contextlib import contextmanager

class PostgresSubstrate:
    def __enter__(self):
        """Support: with PostgresSubstrate(config) as substrate:"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Auto-disconnect on exit."""
        self.disconnect()
        return False

    @contextmanager
    def connection(self):
        """Get connection with automatic return to pool."""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.return_connection(conn)
```

### Step 7: Fix Neo4j Cypher Queries

Audit and fix string interpolation in `neo4j_substrate.py`:

```python
# ❌ VULNERABLE (string interpolation):
session.run(f"""
    MERGE (e:{labels} {{id: '{entity.id}'}})
    SET e += {entity.attributes}
""")

# ✓ SAFE (parameterized):
session.run(
    """
    MERGE (e:Entity {entity_id: $entity_id})
    SET e.entity_type = $entity_type, e += $attributes
    """,
    entity_id=entity.entity_id,
    entity_type=entity.entity_type,
    attributes=entity.attributes,
)
```

### Step 8: Fix Redis Datetime Serialization

Update `redis_substrate.py` to handle datetime:

```python
def cache_entity(self, entity: Entity, ttl: Optional[int] = None) -> None:
    """Cache entity with datetime serialization."""
    data = json.dumps({
        "entity_id": entity.entity_id,
        "entity_type": entity.entity_type,
        "attributes": entity.attributes,
        "created_at": entity.created_at.isoformat() if entity.created_at else None,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
    })
    self._client.setex(key, ttl, data)

def get_cached_entity(self, entity_id: str) -> Optional[Entity]:
    """Retrieve entity with datetime deserialization."""
    data = self._client.get(key)
    if not data:
        return None
    parsed = json.loads(data)
    return Entity(
        entity_id=parsed["entity_id"],
        entity_type=parsed["entity_type"],
        attributes=parsed.get("attributes", {}),
        created_at=datetime.fromisoformat(parsed["created_at"]) if parsed.get("created_at") else None,
        updated_at=datetime.fromisoformat(parsed["updated_at"]) if parsed.get("updated_at") else None,
    )
```

### Step 9: Add Exports to `__init__.py`

Add to [world_model/__init__.py](world_model/__init__.py):

```python
# Persistence substrates (v2.1.0+)
from world_model.postgres_substrate import PostgresSubstrate, PostgresConfig
from world_model.neo4j_substrate import Neo4jSubstrate, Neo4jConfig
from world_model.redis_substrate import RedisSubstrate, RedisConfig

# Substrate base
from world_model.substrates import PersistenceSubstrate

__all__ = [
    # ... existing exports ...
    # Substrates
    "PersistenceSubstrate",
    "PostgresSubstrate",
    "PostgresConfig",
    "Neo4jSubstrate",
    "Neo4jConfig",
    "RedisSubstrate",
    "RedisConfig",
]
```

### Step 10: Add Integration Tests

Create [tests/world_model/test_substrates.py](tests/world_model/test_substrates.py):

```python
import pytest
from datetime import datetime
from world_model.state import Entity, Relation, WorldModelState
from world_model import PostgresSubstrate, PostgresConfig

@pytest.fixture
def postgres_substrate():
    """Provide connected postgres substrate."""
    config = PostgresConfig(database="l9_test")
    with PostgresSubstrate(config) as substrate:
        substrate.drop_schema()
        substrate.create_schema()
        yield substrate
        substrate.drop_schema()

def test_entity_roundtrip(postgres_substrate):
    """Entity persist + load preserves all fields."""
    entity = Entity(
        entity_id="user_1",
        entity_type="Person",
        attributes={"name": "Alice", "age": 30},
    )
    postgres_substrate.store_entity(entity)
    loaded = postgres_substrate.load_entity("user_1")

    assert loaded is not None
    assert loaded.entity_id == "user_1"
    assert loaded.entity_type == "Person"
    assert loaded.attributes == {"name": "Alice", "age": 30}

def test_relation_roundtrip(postgres_substrate):
    """Relation persist + load preserves all fields."""
    # Create entities first
    postgres_substrate.store_entity(Entity(entity_id="e1", entity_type="Type1"))
    postgres_substrate.store_entity(Entity(entity_id="e2", entity_type="Type2"))

    relation = Relation(
        relation_id="r1",
        relation_type="CONNECTS",
        source_id="e1",
        target_id="e2",
        attributes={"weight": 1.0},
    )
    postgres_substrate.store_relation(relation)
    loaded = postgres_substrate.load_relation("r1")

    assert loaded is not None
    assert loaded.source_id == "e1"
    assert loaded.target_id == "e2"

def test_state_sync_roundtrip(postgres_substrate):
    """Full WorldModelState sync/restore works."""
    state = WorldModelState()
    state.add_entity(Entity(entity_id="e1", entity_type="T1"))
    state.add_entity(Entity(entity_id="e2", entity_type="T2"))
    state.add_relation(Relation(relation_id="r1", relation_type="REL", source_id="e1", target_id="e2"))

    postgres_substrate.sync_state_to_db(state)
    restored = postgres_substrate.load_state_from_db()

    assert len(list(restored.get_all_entities())) == 2
    assert len(list(restored.get_all_relations())) == 1
```

### Step 11: Validation + Cleanup

Final validation:

```bash
# Verify imports
python -c "
from world_model import PostgresSubstrate, Neo4jSubstrate, RedisSubstrate, PersistenceSubstrate
from world_model.substrates import entity_to_db, db_to_entity
print('✓ All imports successful')
"

# Run tests
pytest tests/world_model/test_substrates.py -v

# Lint check
ruff check world_model/postgres_substrate.py world_model/neo4j_substrate.py world_model/redis_substrate.py
```

Delete staging files after validation passes:

```bash
rm world_model/_pack_staging/postgres_substrate.py
rm world_model/_pack_staging/neo4j_substrate.py
rm world_model/_pack_staging/redis_substrate.py
```

## Files Modified

| File | Action |

|------|--------|

| `world_model/substrates/__init__.py` | Create (new) |

| `world_model/substrates/base.py` | Create (Protocol) |

| `world_model/substrates/field_mapper.py` | Create (mapping utils) |

| `world_model/postgres_substrate.py` | Create (from staging + fixes) |

| `world_model/neo4j_substrate.py` | Create (from staging + fixes) |

| `world_model/redis_substrate.py` | Create (from staging + fixes) |

| `world_model/__init__.py` | Edit (add exports) |

| `tests/world_model/test_substrates.py` | Create (integration tests) |

| `world_model/_pack_staging/*.py` | Delete (cleanup) |

## Success Criteria

1. All 3 substrates import without error
2. Context manager pattern works (`with PostgresSubstrate() as s:`)
3. Entity/Relation roundtrip tests pass
4. State sync/restore tests pass
5. No Cypher injection vulnerabilities (parameterized queries)
6. Datetime fields serialize/deserialize correctly in Redis
7. ruff check passes with no errors
