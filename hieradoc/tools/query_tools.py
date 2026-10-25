import json
from typing import Dict, Any, List, Optional
from hieradoc.storage.base import BaseTreeStorage

UNIVERSAL_QUERY_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "explore_tree_node",
            "description": (
                "Explore child nodes of a given hierarchical node:\n"
                "- If node_id is omitted/null: Returns top Root Clusters.\n"
                "- If node_id is Cluster: Returns Sub-clusters or Documents inside it.\n"
                "- If node_id is Document: Returns Branches (Chapters/Sections/Parts).\n"
                "- If node_id is Branch: Returns Leaves (Articles/Clauses/Paragraphs)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "ID of node to explore. Omit or null to start from root clusters."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_keyword_index",
            "description": (
                "Search keyword index across titles, summaries and leaf content on the tree.\n"
                "Returns top relevant candidate nodes ranked by relevance score."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "1 to 3 key terms to search (e.g. 'confidentiality duration', 'uptime SLA', 'penalty')."
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_leaf_node",
            "description": (
                "Read the exact verbatim content of a leaf node (Article, Clause, Paragraph) "
                "with line-number citations [start_line, end_line] to gather hard evidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "leaf_node_id": {
                        "type": "string",
                        "description": "ID of leaf node to read verbatim text."
                    }
                },
                "required": ["leaf_node_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_branch_full",
            "description": (
                "Read the entire contiguous text of an entire Branch/Chapter in one call (Parent Rollup). "
                "Use this when the query asks for broad procedures, comprehensive policies, or multiple contiguous articles."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "branch_id": {
                        "type": "string",
                        "description": "ID of the branch/chapter to read in its entirety."
                    }
                },
                "required": ["branch_id"]
            }
        }
    }
]

class UniversalToolExecutor:
    """Executes tool calls against any BaseTreeStorage instance."""

    def __init__(self, storage: BaseTreeStorage):
        self.storage = storage

    def execute_tool(self, func_name: str, args: Dict[str, Any]) -> str:
        try:
            if func_name == "explore_tree_node":
                node_id = args.get("node_id")
                res = self.storage.explore_node(node_id)
                return json.dumps(res, ensure_ascii=False)

            elif func_name == "search_keyword_index":
                kw = args.get("keyword", "")
                res = self.storage.search_keyword(kw)
                return json.dumps(res, ensure_ascii=False)

            elif func_name in ("read_leaf_node", "read_leaf_node_supabase"):
                leaf_id = args.get("leaf_node_id") or args.get("leaf_id")
                if not leaf_id:
                    return json.dumps({"error": "Missing leaf_node_id parameter"})
                res = self.storage.read_leaf(leaf_id)
                return json.dumps(res, ensure_ascii=False)

            elif func_name == "read_branch_full":
                b_id = args.get("branch_id")
                if not b_id:
                    return json.dumps({"error": "Missing branch_id parameter"})
                res = self.storage.read_branch_full(b_id)
                return json.dumps(res, ensure_ascii=False)

            return json.dumps({"error": f"Unknown tool function: {func_name}"})
        except Exception as e:
            return json.dumps({"error": f"Tool execution failed: {str(e)}"})
