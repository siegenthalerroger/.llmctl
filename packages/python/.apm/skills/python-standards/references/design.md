# Design Examples

Worked ✅/❌ pairs for [python-standards §3](../SKILL.md#3-data-modelling) and [§4](../SKILL.md#4-module-and-api-boundaries).

## Data modelling

### Records are typed objects

❌ **BAD** — every consumer re-guesses the keys, and a typo is a runtime `KeyError`:
```python
def build_user(row) -> dict:
    return {"name": row[0], "email": row[1], "active": row[2]}

def notify(user: dict) -> None:
    send(user["emial"])  # nothing catches this
```

✅ **GOOD**:
```python
@dataclass(frozen=True, slots=True, kw_only=True)
class User:
    name: str
    email: str
    active: bool

def build_user(row: Sequence[object]) -> User:
    ...

def notify(user: User) -> None:
    send(user.email)  # a typo here is a type error
```

`frozen` prevents accidental mutation by a consumer, `slots` removes the per-instance `__dict__`, and `kw_only` means adding a field never silently reorders an existing call site.

### Parse, don't validate

❌ **BAD** — the same three checks appear at every use, and nothing guarantees they all happened:
```python
def process(config: dict) -> None:
    if "retries" not in config:
        raise ValueError("missing retries")
    if not isinstance(config["retries"], int):
        raise ValueError("retries must be an int")
    for _ in range(config["retries"]):
        ...

def report(config: dict) -> str:
    return f"retries={config['retries']}"  # trusts a check it never did
```

✅ **GOOD** — one conversion at the edge; everything downstream takes a `Config`:
```python
@dataclass(frozen=True, slots=True, kw_only=True)
class Config:
    retries: int
    endpoint: str

def parse_config(raw: Mapping[str, object]) -> Config:
    """Convert untrusted input into a Config, or raise ConfigError."""
    ...

def process(config: Config) -> None:
    for _ in range(config.retries):
        ...
```

### Closed sets

❌ **BAD**:
```python
if status == "pendng":  # silently never true
    ...
```

✅ **GOOD**:
```python
class Status(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"

if status is Status.PENDING:
    ...
```

## Module and API boundaries

### Functional core, imperative shell

❌ **BAD** — the calculation cannot be exercised without a filesystem, a clock and a network:
```python
def generate_report() -> None:
    rows = json.loads(Path("data.json").read_text(encoding="utf-8"))
    cutoff = datetime.now(UTC) - timedelta(days=30)
    recent = [r for r in rows if datetime.fromisoformat(r["at"]) > cutoff]
    total = sum(r["amount"] for r in recent)
    requests.post(WEBHOOK, json={"total": total})
    print(f"total: {total}")
```

✅ **GOOD** — the shell does I/O, the core is a pure function you can call with a list:
```python
def total_since(rows: Sequence[Entry], cutoff: datetime) -> Decimal:
    """Pure: no clock, no disk, no network. Testable with a literal list."""
    return sum((r.amount for r in rows if r.at > cutoff), start=Decimal(0))


def generate_report(source: Path, now: datetime, sink: Sink) -> Decimal:
    rows = parse_entries(source.read_text(encoding="utf-8"))
    total = total_since(rows, now - timedelta(days=30))
    sink.publish(total)
    return total
```

The clock is passed in rather than read inside. That one change is the difference between a test and a `freezegun` dependency.

### No work at import time

❌ **BAD** — importing this module opens a connection, so it cannot be imported by a test, a linter, or `--help`:
```python
config = json.loads(Path("/etc/app/config.json").read_text(encoding="utf-8"))
db = connect(config["dsn"])
```

✅ **GOOD**:
```python
def load_config(path: Path) -> Config: ...
def connect_db(config: Config) -> Connection: ...
```

### No module-level mutable state

❌ **BAD** — a process-wide singleton with no lifecycle; two callers fight over it:
```python
_cache: dict[str, Result] = {}

def get(key: str) -> Result:
    if key not in _cache:
        _cache[key] = compute(key)
    return _cache[key]
```

✅ **GOOD** — the caller owns the lifetime:
```python
class ResultCache:
    def __init__(self) -> None:
        self._entries: dict[str, Result] = {}

    def get(self, key: str) -> Result:
        ...
```

`functools.cache` on a pure function is the acceptable exception — it is still global, so it is only appropriate where the mapping is genuinely immutable and unbounded growth is not a risk.

### Declare the public surface

✅ **GOOD**:
```python
__all__ = ["Config", "load_config", "ConfigError"]

def _normalise_key(key: str) -> str:  # internal: free to change
    ...
```

### Take what you use

❌ **BAD** — couples the function to the whole config object to read two fields:
```python
def send(config: Config, message: str) -> None:
    post(config.endpoint, message, timeout=config.timeout_seconds)
```

✅ **GOOD**:
```python
def send(endpoint: str, message: str, *, timeout_seconds: float) -> None:
    post(endpoint, message, timeout=timeout_seconds)
```
