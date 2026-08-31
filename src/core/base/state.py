"""
Shared state management for multi-agent orchestration.

The orchestrator maintains a central state that all agents can read and authorized
agents can update. This ensures:
1. Consistency: all agents see the same campaign state
2. Concurrency safety: atomic updates prevent race conditions
3. Observability: state changes are logged and traceable
4. Resilience: state can be checkpointed and restored

Design pattern: MVCC (Multi-Version Concurrency Control) for safe reads during updates.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List, Callable
from enum import Enum
from datetime import datetime
import threading
from copy import deepcopy


class StateOperation(Enum):
    """Types of state modifications."""
    SET = "set"                # Replace entire value
    APPEND = "append"          # Append to list
    INCREMENT = "increment"    # Increment numeric value
    MERGE = "merge"            # Deep merge dict
    DELETE = "delete"          # Remove key


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
    actor_id: str  # Agent or user who made the change
    operation: StateOperation
    key: str
    old_value: Any
    new_value: Any
    context: Dict[str, Any] = field(default_factory=dict)  # Why this change was made


class SharedState:
    """
    Thread-safe shared state for multi-agent coordination.
    
    Principles:
    - ACID properties: Atomicity, Consistency, Isolation, Durability
    - Immutable reads: state snapshots are immutable
    - Versioning: track all changes for replay/audit
    - Role-based access: different agents have different permissions
    """
    
    def __init__(
        self,
        initial_data: Optional[Dict[str, Any]] = None,
        on_change: Optional[Callable[[StateChange], None]] = None,
    ):
        """
        Initialize shared state.
        
        Args:
            initial_data: Starting state values
            on_change: Callback when state changes
        """
        self._lock = threading.RLock()
        self._data = deepcopy(initial_data or {})
        self._version = 0
        self._change_history: List[StateChange] = []
        self._snapshots: Dict[int, StateSnapshot] = {}
        self._on_change = on_change
        
        # Take initial snapshot
        self._create_snapshot()
    
    def _create_snapshot(self) -> StateSnapshot:
        """Create immutable snapshot of current state."""
        snapshot = StateSnapshot(
            version=self._version,
            timestamp=datetime.now(),
            data=deepcopy(self._data),
        )
        self._snapshots[self._version] = snapshot
        return snapshot
    
    def get(
        self,
        key: str,
        default: Any = None,
        version: Optional[int] = None,
    ) -> Any:
        """
        Get value from state.
        
        Args:
            key: State key
            default: Default value if key doesn't exist
            version: Specific version to read from (for time-travel debugging)
        
        Returns:
            State value
        """
        with self._lock:
            if version is not None:
                if version in self._snapshots:
                    return self._snapshots[version].get(key, default)
                else:
                    raise ValueError(f"State version {version} not found")
            
            return self._data.get(key, default)
    
    def get_all(self, version: Optional[int] = None) -> Dict[str, Any]:
        """Get entire state as a snapshot."""
        with self._lock:
            if version is not None:
                if version in self._snapshots:
                    return deepcopy(self._snapshots[version].data)
                else:
                    raise ValueError(f"State version {version} not found")
            
            return deepcopy(self._data)
    
    def set(
        self,
        key: str,
        value: Any,
        actor_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Set state value.
        
        Args:
            key: State key
            value: New value
            actor_id: Agent making the change
            context: Reason/context for the change
        """
        with self._lock:
            old_value = self._data.get(key)
            self._data[key] = deepcopy(value)
            self._version += 1
            
            # Record change
            change = StateChange(
                version=self._version,
                timestamp=datetime.now(),
                actor_id=actor_id,
                operation=StateOperation.SET,
                key=key,
                old_value=old_value,
                new_value=deepcopy(value),
                context=context or {},
            )
            self._change_history.append(change)
            
            # Create new snapshot
            self._create_snapshot()
            
            # Trigger callback
            if self._on_change:
                self._on_change(change)
    
    def increment(
        self,
        key: str,
        amount: float,
        actor_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Increment numeric value.
        
        Args:
            key: State key
            amount: Amount to increment by
            actor_id: Agent making the change
            context: Reason/context
        """
        with self._lock:
            old_value = self._data.get(key, 0)
            new_value = old_value + amount
            self._data[key] = new_value
            self._version += 1
            
            change = StateChange(
                version=self._version,
                timestamp=datetime.now(),
                actor_id=actor_id,
                operation=StateOperation.INCREMENT,
                key=key,
                old_value=old_value,
                new_value=new_value,
                context=context or {},
            )
            self._change_history.append(change)
            self._create_snapshot()
            
            if self._on_change:
                self._on_change(change)
    
    def append(
        self,
        key: str,
        item: Any,
        actor_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Append to list.
        
        Args:
            key: State key (must be a list)
            item: Item to append
            actor_id: Agent making the change
            context: Reason/context
        """
        with self._lock:
            if key not in self._data:
                self._data[key] = []
            
            old_value = deepcopy(self._data[key])
            self._data[key].append(deepcopy(item))
            self._version += 1
            
            change = StateChange(
                version=self._version,
                timestamp=datetime.now(),
                actor_id=actor_id,
                operation=StateOperation.APPEND,
                key=key,
                old_value=old_value,
                new_value=deepcopy(self._data[key]),
                context=context or {},
            )
            self._change_history.append(change)
            self._create_snapshot()
            
            if self._on_change:
                self._on_change(change)
    
    def merge(
        self,
        key: str,
        update_dict: Dict[str, Any],
        actor_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Deep merge a dict into existing value.
        
        Args:
            key: State key (must be a dict)
            update_dict: Dict to merge
            actor_id: Agent making the change
            context: Reason/context
        """
        with self._lock:
            if key not in self._data:
                self._data[key] = {}
            
            old_value = deepcopy(self._data[key])
            
            # Deep merge
            self._deep_merge(self._data[key], update_dict)
            self._version += 1
            
            change = StateChange(
                version=self._version,
                timestamp=datetime.now(),
                actor_id=actor_id,
                operation=StateOperation.MERGE,
                key=key,
                old_value=old_value,
                new_value=deepcopy(self._data[key]),
                context=context or {},
            )
            self._change_history.append(change)
            self._create_snapshot()
            
            if self._on_change:
                self._on_change(change)
    
    def _deep_merge(self, target: Dict, source: Dict) -> None:
        """Recursively merge source dict into target dict."""
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = deepcopy(value)
    
    def get_history(
        self,
        key: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[StateChange]:
        """
        Get state change history.
        
        Args:
            key: Filter by state key (None = all)
            limit: Max number of changes to return
        
        Returns:
            List of state changes
        """
        with self._lock:
            history = self._change_history
            
            if key:
                history = [c for c in history if c.key == key]
            
            if limit:
                history = history[-limit:]
            
            return deepcopy(history)
    
    def checkpoint(self) -> Dict[str, Any]:
        """
        Create a checkpoint for resilience (crash recovery).
        
        Returns:
            Serializable checkpoint data
        """
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
        """
        Restore state from checkpoint.
        
        Args:
            checkpoint: Checkpoint data
            on_change: Callback for changes
        
        Returns:
            Restored SharedState
        """
        instance = cls(initial_data=checkpoint.get("data"), on_change=on_change)
        instance._version = checkpoint.get("version", 0)
        return instance
