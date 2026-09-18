# Typing Examples

Worked ✅/❌ pairs for [python-standards §2](../SKILL.md#2-typing).

## Modern syntax

❌ **BAD** — pre-3.10 spellings in new code:
```python
from typing import Dict, List, Optional, Union

def load(paths: List[str], limit: Optional[int] = None) -> Dict[str, Union[int, str]]:
    ...
```

✅ **GOOD**:
```python
def load(paths: list[str], limit: int | None = None) -> dict[str, int | str]:
    ...
```

## Aliases and generics (3.12+)

❌ **BAD**:
```python
from typing import TypeAlias, TypeVar, Generic

T = TypeVar("T")
Rows: TypeAlias = list[dict[str, str]]

class Cache(Generic[T]):
    ...
```

✅ **GOOD** — PEP 695 syntax:
```python
type Rows = list[dict[str, str]]

class Cache[T]:
    ...

def first[T](items: Sequence[T]) -> T | None:
    return items[0] if items else None
```

## Implicit Optional

❌ **BAD** — the annotation lies; `None` is accepted but not declared:
```python
def connect(timeout: float = None) -> Connection:
    ...
```

✅ **GOOD**:
```python
def connect(timeout: float | None = None) -> Connection:
    ...
```

## Accept wide, return narrow

❌ **BAD** — demands a `list` when it only iterates, and hides the return shape:
```python
def summarise(rows: list[Row]) -> Iterable[str]:
    return [row.label for row in rows]
```

✅ **GOOD** — any iterable works; the caller gets something it can index:
```python
def summarise(rows: Iterable[Row]) -> list[str]:
    return [row.label for row in rows]
```

## `Any` confined to an adapter

❌ **BAD** — `Any` leaks through the whole call chain:
```python
def get_user(client: Any) -> Any:
    return client.fetch("/user")

def greet(user: Any) -> str:
    return f"hi {user['name']}"
```

✅ **GOOD** — one boundary function converts, everything downstream is typed:
```python
@dataclass(frozen=True, slots=True)
class User:
    name: str
    id: int

def parse_user(payload: Mapping[str, object]) -> User:
    name = payload["name"]
    user_id = payload["id"]
    if not isinstance(name, str) or not isinstance(user_id, int):
        raise UserPayloadError(f"unexpected user payload: {payload!r}")
    return User(name=name, id=user_id)

def greet(user: User) -> str:
    return f"hi {user.name}"
```

## `Protocol` over inheritance

❌ **BAD** — forces every caller into your class hierarchy:
```python
class BaseReader(ABC):
    @abstractmethod
    def read(self) -> str: ...

def parse(reader: BaseReader) -> Config:
    ...
```

✅ **GOOD** — anything with the right shape qualifies, including `io.StringIO`:
```python
class Readable(Protocol):
    def read(self) -> str: ...

def parse(reader: Readable) -> Config:
    ...
```

## Closing the value space

❌ **BAD** — four of these strings are typos waiting to happen:
```python
def render(data: Data, fmt: str = "json") -> str:
    ...
```

✅ **GOOD**:
```python
type Format = Literal["json", "yaml", "table"]

def render(data: Data, fmt: Format = "json") -> str:
    ...
```

## Type-only imports

❌ **BAD** — imports a heavy module at runtime purely for an annotation:
```python
import pandas as pd

def describe(frame: pd.DataFrame) -> str:
    ...
```

✅ **GOOD**:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

def describe(frame: pd.DataFrame) -> str:
    ...
```

## Narrowing both branches

❌ **BAD** — `TypeGuard` leaves the `else` branch un-narrowed:
```python
def is_str_list(value: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(item, str) for item in value)
```

✅ **GOOD** (3.13+) — `TypeIs` narrows the negative branch too:
```python
def is_str_list(value: list[object]) -> TypeIs[list[str]]:
    return all(isinstance(item, str) for item in value)
```

## `@override`

❌ **BAD** — a base-class rename turns this into a dead method, silently:
```python
class JsonExporter(Exporter):
    def serialise(self, rows: list[Row]) -> str:
        ...
```

✅ **GOOD** — the checker fails if the base no longer declares it:
```python
class JsonExporter(Exporter):
    @override
    def serialise(self, rows: list[Row]) -> str:
        ...
```

## Suppressions

❌ **BAD** — suppresses every error on the line, forever, for no stated reason:
```python
result = client.fetch(url)  # type: ignore
```

✅ **GOOD**:
```python
# type: ignore[no-untyped-call]  # vendor stubs missing, tracked in #412
result = client.fetch(url)
```
