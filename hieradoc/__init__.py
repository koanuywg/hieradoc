import os
from typing import Optional, Union, Dict, Any
from hieradoc.storage.base import BaseTreeStorage
from hieradoc.storage.sqlite import SQLiteTreeStorage
from hieradoc.indexer import HierarchicalIndexer
from hieradoc.agents.query_agent import TreeQueryAgent
from hieradoc.schemas.query import QueryRequest, QueryResponse, Citation

__version__ = "0.1.0"
__all__ = [
    "HieraDoc",
    "HierarchicalIndexer",
    "TreeQueryAgent",
    "BaseTreeStorage",
    "SQLiteTreeStorage",
    "QueryRequest",
    "QueryResponse",
    "Citation"
]

class HieraDoc:
    """
    Unified High-Level Interface for HieraDoc.
    Provides 3-line indexing and grounded tree-traversal query.
    """

    def __init__(
        self,
        storage: Optional[Union[BaseTreeStorage, str]] = "sqlite",
        db_path: str = "hieradoc_vault.db",
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None
    ):
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        if isinstance(storage, BaseTreeStorage):
            self.storage = storage
        elif storage == "sqlite":
            self.storage = SQLiteTreeStorage(db_path=db_path)
        elif storage == "supabase":
            from hieradoc.storage.supabase import SupabaseTreeStorage
            self.storage = SupabaseTreeStorage()
        else:
            raise ValueError(f"Unknown storage type: {storage}")

        self.model = model
        self.indexer = HierarchicalIndexer(storage=self.storage, model=self.model)
        self.agent = TreeQueryAgent(storage=self.storage, model_name=self.model)

    def index(
        self,
        file_path_or_text: str,
        doc_id: Optional[str] = None,
        cluster: str = "Tài Liệu Chung"
    ) -> Dict[str, Any]:
        """Index a file path or raw text string into the hierarchical tree."""
        if os.path.exists(file_path_or_text):
            return self.indexer.index_file(file_path_or_text, doc_id=doc_id, cluster_title=cluster)
        else:
            code_name = doc_id or "doc_custom"
            return self.indexer.index_text(file_path_or_text, doc_id=code_name, cluster_title=cluster)

    def query(self, question: str, max_steps: int = 10) -> QueryResponse:
        """Run an autonomous tree-traversal query with exact line citations."""
        req = QueryRequest(query=question, max_steps=max_steps)
        return self.agent.query(req)
