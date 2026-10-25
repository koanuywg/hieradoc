from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseTreeStorage(ABC):
    """Abstract Base Class for Hierarchical Tree Storage."""

    @abstractmethod
    def save_document_tree(
        self,
        doc_id: str,
        title: str,
        summary: str,
        tree_data: List[Dict[str, Any]],
        cluster_title: str = "Tài Liệu Chung"
    ) -> Dict[str, Any]:
        """Save a hierarchical document tree structure into storage."""
        pass

    @abstractmethod
    def explore_node(self, node_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Explore children of a given node:
        - If node_id is None: Returns root clusters or top-level documents.
        - If node_id is cluster/document/branch: Returns immediate child nodes.
        """
        pass

    @abstractmethod
    def search_keyword(self, keyword: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Search nodes matching keyword using relevance-weighted scoring."""
        pass

    @abstractmethod
    def read_leaf(self, leaf_id: str) -> Dict[str, Any]:
        """
        Read exact leaf raw text, lines and contextual parent titles.
        Returns: {
            'leaf_id': str,
            'title': str,
            'doc_title': str,
            'branch_title': str,
            'summary': str,
            'content': str,
            'start_line': int,
            'end_line': int
        }
        """
        pass

    @abstractmethod
    def read_branch_full(self, branch_id: str) -> Dict[str, Any]:
        """
        Read the entire contiguous text of all child leaves in a branch in one call (Parent Rollup).
        Returns: {
            'branch_id': str,
            'title': str,
            'doc_title': str,
            'summary': str,
            'content': str,
            'start_line': int,
            'end_line': int,
            'leaves_count': int
        }
        """
        pass

    @abstractmethod
    def list_documents(self) -> List[Dict[str, Any]]:
        """List all indexed documents with summary overview."""
        pass
