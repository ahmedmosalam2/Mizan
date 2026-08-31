from enum import Enum

class ScenarioType(str, Enum):
    """The 7 benchmark dimensions."""
    ORCHESTRATION = "orchestration"
    TOOL_USE = "tool_use"
    SAFETY = "safety"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"
    MEMORY = "memory"
    OBSERVABILITY = "observability"
    MULTIMODAL = "multimodal"
