from dataclasses import dataclass
from typing import Optional, List


@dataclass
class PromptData:
    """Data structure to hold the state of an interactive prompt session."""
    
    persona: Optional[str] = None
    task: Optional[str] = None
    context: Optional[str] = None
    schemas: Optional[List[str]] = None
    examples: Optional[List[str]] = None
    constraints: Optional[str] = None
    
    def __post_init__(self):
        """Initialize empty lists for schemas and examples if None."""
        if self.schemas is None:
            self.schemas = []
        if self.examples is None:
            self.examples = []