"""
SharedState Contract — Thread-safe, versioned state for multi-agent coordination.

Design pattern: MVCC (Multi-Version Concurrency Control).
    - Atomic writes with full audit trail
    - Immutable snapshots for time-travel debugging
    - Checkpoint/restore for crash recovery
    - Role-based access (enforced at orchestrator level)
"""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading


class StateOperation(Enum):
    """Types of state modifications."""

    SET = "set"
    APPEND = "append"
    INCREMENT = "increment"
    MERGE = "merge"
    DELETE = "delete"


@dataclass
class StateSnapshot:
    """Immutable snapshot of state at a point in time."""

    version: int
    timestamp: datetime
    data: Dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Get value from snapshot."""
        return self.data.get(key, default)


@dataclass
class StateChange:
    """Record of a state modification for audit trail."""

    version: int
    timestamp: datetime
    actor_id: str
    operation: StateOperation
    key: str
    old_value: Any
    new_value: Any
    context: Dict[str, Any] = field(default_factory=dict)


class SharedState:
    """
    Thread-safe shared state for multi-agent coordination.

    Supports:
        - get / get_all  → read (with optional version for time-travel)
        - set / increment / append / merge  → write (with audit trail)
        - checkpoint / from_checkpoint  → crash recovery
        - get_history  → audit trail query
    """

    def __init__(
        self,
        initial_data: Optional[Dict[str, Any]] = None,
        on_change: Optional[Callable[[StateChange], None]] = None,
    ):
        self._lock = threading.RLock()
        self._data = deepcopy(initial_data or {})
        self._version = 0
        self._change_history: List[StateChange] = []
        self._snapshots: Dict[int, StateSnapshot] = {}
        self._on_change = on_change

        # Take initial snapshot
        self._create_snapshot()

    # ── Read operations ──────────────────────────────────────────

    def get(
        self,
        key: str,
        default: Any = None,
        version: Optional[int] = None,
    ) -> Any:
        """Get value from state, optionally from a specific version."""
        with self._lock:
            if version is not None:
                if version in self._snapshots:
                    return self._snapshots[version].get(key, default)
                raise ValueError(f"State version {version} not found")
            return self._data.get(key, default)

    def get_all(self, version: Optional[int] = None) -> Dict[str, Any]:
        """Get entire state as a deep copy."""
        with self._lock:
            if version is not None:
                if version in self._snapshots:
                    return deepcopy(self._snapshots[version].data)
                raise ValueError(f"State version {version} not found")
            return deepcopy(self._data)

    # ── Write operations ─────────────────────────────────────────

    def set(
        self,
        key: str,
        value: Any,
        actor_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set state value with audit trail."""
        with self._lock:
            old_value = self._data.get(key)
            self._data[key] = deepcopy(value)
            self._record_change(
                StateOperation.SET, key, old_value, deepcopy(value),
                actor_id, context,
            )

    def increment(
        self,
        key: str,
        amount: float,
        actor_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Increment numeric value atomically."""
        with self._lock:
            old_value = self._data.get(key, 0)
            new_value = old_value + amount
            self._data[key] = new_value
            self._record_change(
                StateOperation.INCREMENT, key, old_value, new_value,
                actor_id, context,
            )

    def append(
        self,
        key: str,
        item: Any,
        actor_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append to a list atomically."""
        with self._lock:
            if key not in self._data:
                self._data[key] = []
            old_value = deepcopy(self._data[key])
            self._data[key].append(deepcopy(item))
            self._record_change(
                StateOperation.APPEND, key, old_value, deepcopy(self._data[key]),
                actor_id, context,
            )

    def merge(
        self,
        key: str,
        update_dict: Dict[str, Any],
        actor_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Deep merge a dict into existing value."""
        with self._lock:
            if key not in self._data:
                self._data[key] = {}
            old_value = deepcopy(self._data[key])
            self._deep_merge(self._data[key], update_dict)
            self._record_change(
                StateOperation.MERGE, key, old_value, deepcopy(self._data[key]),
                actor_id, context,
            )

    # ── History & checkpointing ──────────────────────────────────

    def get_history(
        self,
        key: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[StateChange]:
        """Get state change history, optionally filtered by key."""
        with self._lock:
            history = self._change_history
            if key:
                history = [c for c in history if c.key == key]
            if limit:
                history = history[-limit:]
            return deepcopy(history)

    def checkpoint(self) -> Dict[str, Any]:
        """Create a serializable checkpoint for crash recovery."""
        with self._lock:
            return {
                "version": self._version,
                "timestamp": datetime.now().isoformat(),
                "data": deepcopy(self._data),
                "history": [
                    {
                        "version": c.version,
                        "timestamp": c.timestamp.isoformat(),
                        "actor_id": c.actor_id,
                        "operation": c.operation.value,
                        "key": c.key,
                        "old_value": c.old_value,
                        "new_value": c.new_value,
                        "context": c.context,
                    }
                    for c in self._change_history
                ],
            }

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint: Dict[str, Any],
        on_change: Optional[Callable] = None,
    ) -> "SharedState":
        """Restore state from a checkpoint."""
        instance = cls(initial_data=checkpoint.get("data"), on_change=on_change)
        instance._version = checkpoint.get("version", 0)
        return instance

    # ── Internal helpers ─────────────────────────────────────────

    def _record_change(
        self,
        operation: StateOperation,
        key: str,
        old_value: Any,
        new_value: Any,
        actor_id: str,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Record a change, bump version, snapshot, and notify."""
        self._version += 1
        change = StateChange(
            version=self._version,
            timestamp=datetime.now(),
            actor_id=actor_id,
            operation=operation,
            key=key,
            old_value=old_value,
            new_value=new_value,
            context=context or {},
        )
        self._change_history.append(change)
        self._create_snapshot()
        if self._on_change:
            self._on_change(change)

    def _create_snapshot(self) -> StateSnapshot:
        """Create immutable snapshot of current state."""
        snapshot = StateSnapshot(
            version=self._version,
            timestamp=datetime.now(),
            data=deepcopy(self._data),
        )
        self._snapshots[self._version] = snapshot
        return snapshot

    @staticmethod
    def _deep_merge(target: Dict, source: Dict) -> None:
        """Recursively merge source dict into target dict."""
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                SharedState._deep_merge(target[key], value)
            else:
                target[key] = deepcopy(value)
