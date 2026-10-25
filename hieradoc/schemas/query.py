from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class Citation(BaseModel):
    doc_id: str
    doc_title: str
    branch_title: Optional[str] = None
    leaf_title: str
    lines: List[int] = Field(default_factory=list, description="[start_line, end_line]")
    exact_quote: str = Field(..., description="Exact raw text citation as grounded evidence")

class QueryRequest(BaseModel):
    query: str = Field(..., description="User question or inquiry")
    target_docs: Optional[List[str]] = Field(None, description="Optional filter of document identifiers")
    max_steps: int = Field(10, description="Maximum tree-traversal reasoning steps")

class QueryResponse(BaseModel):
    answer: str = Field(..., description="Synthesized grounded answer")
    citations: List[Citation] = Field(default_factory=list, description="List of exact citations")
    traversal_path: List[str] = Field(default_factory=list, description="Step-by-step tree navigation path")
    total_tokens: int = 0
    execution_time_seconds: float = 0.0
