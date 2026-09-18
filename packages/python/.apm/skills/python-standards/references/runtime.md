# Runtime Examples

Worked ✅/❌ pairs for [python-standards §6](../SKILL.md#6-errors), [§7](../SKILL.md#7-resources-io-and-subprocesses), [§8](../SKILL.md#8-logging) and [§9](../SKILL.md#9-concurrency).

## Errors

### A package-specific hierarchy

❌ **BAD** — callers must catch `Exception` to catch yours, which catches everything else too:
```python
raise ValueError("bad config")
```

✅ **GOOD**:
```python
class ConfigError(Exception):
    """Base for every failure this package raises."""

class MissingKeyError(ConfigError): ...
class MalformedValueError(ConfigError): ...

raise MissingKeyError(f"key {key!r} not found in {path}")
```

### Chain the cause

❌ **BAD** — the original traceback is gone, and with it the reason:
```python
try:
    data = json.loads(text)
except json.JSONDecodeError:
    raise ConfigError("could not read config")
```

✅ **GOOD**:
```python
try:
    data = json.loads(text)
except json.JSONDecodeError as err:
    raise MalformedValueError(f"{path} is not valid JSON") from err
```

### Catch narrowly

❌ **BAD** — swallows typos, interrupts and programming errors along with the expected failure:
```python
try:
    value = registry[key]
    result = transform(value)
    write(result)
except Exception:
    pass
```

✅ **GOOD** — states which failure is being ignored, and why nothing else is:
```python
with contextlib.suppress(KeyError):
    value = registry[key]
    ...
```

### Messages name the value

❌ **BAD**: `raise ValidationError("invalid input")`

✅ **GOOD**: `raise ValidationError(f"port must be 1-65535, got {port!r} from {source}")`

### Expected outcomes are return values

❌ **BAD** — forces the caller into a `try` block for the normal case:
```python
def find_user(user_id: int) -> User:
    row = db.get(user_id)
    if row is None:
        raise UserNotFoundError(user_id)
    return parse_user(row)
```

✅ **GOOD** when "absent" is ordinary:
```python
def find_user(user_id: int) -> User | None:
    row = db.get(user_id)
    return parse_user(row) if row is not None else None
```

Keep the raising version when absence genuinely is a defect — but pick one and name it accordingly (`find_` returns optional, `get_` raises).

## Resources and processes

### Explicit encoding

❌ **BAD** — reads as cp1252 on some Windows machines, UTF-8 elsewhere:
```python
text = open(path).read()
```

✅ **GOOD**:
```python
text = Path(path).read_text(encoding="utf-8")
```

### Subprocesses

❌ **BAD** — an injection primitive, and a failure that returns silently:
```python
subprocess.run(f"git clone {url} {dest}", shell=True)
```

✅ **GOOD**:
```python
subprocess.run(
    ["git", "clone", "--", url, str(dest)],
    check=True,
    capture_output=True,
    text=True,
    timeout=300,
)
```

`check=True` turns a non-zero exit into a `CalledProcessError` instead of a value nobody inspected; `--` stops a URL beginning with `-` from being read as a flag.

### Own the lifecycle

✅ **GOOD** — a resource with setup and teardown gets a context manager:
```python
@contextlib.contextmanager
def acquired_lock(path: Path) -> Iterator[None]:
    path.touch(exist_ok=False)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)
```

### Inject the clock and the environment

❌ **BAD** — untestable without patching module internals:
```python
def is_expired(token: Token) -> bool:
    return token.expires_at < datetime.now(UTC)
```

✅ **GOOD**:
```python
def is_expired(token: Token, now: datetime) -> bool:
    return token.expires_at < now
```

## Logging

❌ **BAD** — configures logging as a side effect of import, formats eagerly, discards the traceback, and leaks a token:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

logging.info(f"calling {url} with {token}")
try:
    call(url)
except HTTPError as err:
    logging.error(str(err))
```

✅ **GOOD**:
```python
logger = logging.getLogger(__name__)

logger.info("calling %s", url)
try:
    call(url)
except HTTPError:
    logger.exception("request to %s failed", url)
    raise
```

Configuration (`basicConfig`, handlers, levels) happens once, in the application entry point — never in an importable module.

## Concurrency

### Structured concurrency

❌ **BAD** — nothing awaits these; exceptions vanish, and tasks may be collected mid-flight:
```python
for url in urls:
    asyncio.create_task(fetch(url))
```

✅ **GOOD** (3.11+) — every task is awaited, and a failure cancels the rest:
```python
async with asyncio.TaskGroup() as group:
    tasks = [group.create_task(fetch(url)) for url in urls]
results = [task.result() for task in tasks]
```

### Never block the loop

❌ **BAD** — stalls every other coroutine for the duration:
```python
async def handle(path: Path) -> str:
    return path.read_text(encoding="utf-8")
```

✅ **GOOD**:
```python
async def handle(path: Path) -> str:
    return await asyncio.to_thread(path.read_text, encoding="utf-8")
```

### Match the model to the workload

```python
# I/O-bound, sync codebase
with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(fetch, urls))

# CPU-bound — threads will not help
with ProcessPoolExecutor() as pool:
    results = list(pool.map(compress, blobs))
```

### Deadlines

✅ **GOOD** — an operation without a timeout is an operation that can hang forever:
```python
async with asyncio.timeout(30):
    result = await fetch(url)
```
