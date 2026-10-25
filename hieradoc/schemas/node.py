from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field

class HeadingCandidate(BaseModel):
    level: int = Field(..., description="Hierarchy level: 1 (Chapter/Part), 2 (Article/Section), 3 (Clause)")
    title: str = Field(..., description="Heading title")
    line_number: int = Field(..., description="Line number [L0001] in original text")
    raw_line: str = Field(..., description="Original raw line string")

class DocumentBlueprint(BaseModel):
    title: str = Field(..., description="Document main title")
    document_type: str = Field(..., description="Type of document, e.g. contract, sla, policy, essay")
    detected_language: str = Field(..., description="Primary language e.g. vi, en")
    has_explicit_headings: bool = Field(..., description="True if document has structured chapters/articles")
    hierarchy_levels: List[str] = Field(
        default_factory=lambda: ["Chương", "Điều", "Khoản", "Điểm"],
        description="Names of hierarchy levels from top to bottom"
    )
    level_1_pattern: Optional[str] = Field(None, description="Regex pattern for Level 1 headings (e.g. Chương/PART)")
    level_2_pattern: Optional[str] = Field(None, description="Regex pattern for Level 2 headings (e.g. Điều/ARTICLE)")
    level_3_pattern: Optional[str] = Field(None, description="Regex pattern for Level 3 headings")
    level_4_pattern: Optional[str] = Field(None, description="Regex pattern for Level 4 headings")

class TreeNodePayload(BaseModel):
    title: str
    node_type: Literal["branch", "leaf"]
    summary: Optional[str] = None
    content_text: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    children: List["TreeNodePayload"] = Field(default_factory=list)

class TreeNode(BaseModel):
    id: str
    parent_id: Optional[str] = None
    document_id: Optional[str] = None
    node_type: str = Field(..., description="'cluster', 'document', 'branch', 'leaf'")
    title: str
    summary: Optional[str] = None
    content_text: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    node_index: int = 0
