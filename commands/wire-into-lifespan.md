---
name: wire-into-lifespan
version: "1.0.0"
description: "Wire component into FastAPI lifespan"
auto_chain: ynp
---

# /wire-into-lifespan — Lifespan Wiring

## WHAT IT DOES

Wire service/client into FastAPI lifespan:

1. Add to startup
2. Add to shutdown
3. Register singleton
4. Verify wiring

---

## PATTERN

```python
# api/server.py lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_service()
    
    yield
    
    # Shutdown
    await close_service()
```

---

## EXECUTION

### 1. IDENTIFY SERVICE

```
Service: {name}
Init: {init_function}
Close: {close_function}
Singleton: {yes/no}
```

### 2. ADD TO LIFESPAN

Location: `api/server.py`

```python
# Add import
from {module} import init_{service}, close_{service}

# Add to startup
await init_{service}()

# Add to shutdown
await close_{service}()
```

### 3. REGISTER SINGLETON (if applicable)

```python
@register_singleton(category="{category}")
async def get_{service}():
    ...
```

---

## OUTPUT

```markdown
## 🔌 LIFESPAN WIRING: {service}

### Changes
| File | Change |
|------|--------|
| api/server.py | Add init/close |

### Verification
- [ ] Import works
- [ ] Startup succeeds
- [ ] Shutdown clean
```

→ **Auto-chains to /ynp**

--- End Command ---
