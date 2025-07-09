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


@dataclass
class Template:
    """Data structure for prompt templates."""
    
    name: str
    description: str
    persona: Optional[str] = None
    task: Optional[str] = None
    context: Optional[str] = None
    constraints: Optional[str] = None
    tags: Optional[List[str]] = None
    
    def __post_init__(self):
        """Initialize empty list for tags if None."""
        if self.tags is None:
            self.tags = []
    
    def to_prompt_data(self) -> PromptData:
        """Convert template to PromptData object."""
        return PromptData(
            persona=self.persona,
            task=self.task,
            context=self.context,
            constraints=self.constraints
        )