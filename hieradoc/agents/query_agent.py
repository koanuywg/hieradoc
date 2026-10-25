import os
import json
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from hieradoc.storage.base import BaseTreeStorage
from hieradoc.tools.query_tools import UNIVERSAL_QUERY_TOOLS, UniversalToolExecutor
from hieradoc.agents.synthesizer import QuerySynthesizer
from hieradoc.schemas.query import QueryRequest, QueryResponse

class TreeQueryAgent:
    """
    Autonomous Hierarchical Tree Navigator Agent.
    Navigates tree structures (Cluster -> Document -> Branch -> Leaf)
    using progressive zoom-in reasoning to retrieve exact verbatim evidence.
    """

    def __init__(
        self,
        storage: BaseTreeStorage,
        model_name: str = "gpt-4o-mini",
        client: Optional[OpenAI] = None
    ):
        self.storage = storage
        self.model = model_name
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.executor = UniversalToolExecutor(storage=self.storage)

    def query(self, request: QueryRequest | str) -> QueryResponse:
        if isinstance(request, str):
            request = QueryRequest(query=request)

        start_time = time.time()
        total_tokens = 0
        traversal_path = []
        collected_leaf_evidences = []
        seen_leaf_ids = set()

        system_prompt = """
        You are HieraDoc - An Autonomous Hierarchical Document Navigator.
        Your mission is to answer user queries by exploring hierarchical tree structures (Clusters -> Documents -> Branches -> Leaves)
        and collecting VERBATIM GROUNDED EVIDENCE (Leaf Content).

        PROGRESSIVE ZOOM-IN NAVIGATION STRATEGY:
        1. UNDERSTAND NODE TYPES:
           - 'cluster': Document cluster. Call explore_tree_node(node_id=id) to reveal contained documents.
           - 'document': High-level document. DO NOT call read_leaf_node on document nodes! Call explore_tree_node(node_id=id) to inspect branches.
           - 'branch': Chapter/Part/Section. Call explore_tree_node(node_id=id) to list child articles/leaves.
           - 'leaf': Leaf Node (contains verbatim clauses/text). MUST call read_leaf_node(leaf_node_id=id) to collect raw evidence!

        2. FAST SEARCH TACTICS:
           - STEP 1: Use search_keyword_index(keyword=...) with 1-3 essential terms (e.g., 'confidentiality duration', 'uptime SLA', 'penalty') 
             or call explore_tree_node(node_id=null) to inspect root clusters.
           - STEP 2: When search_keyword_index returns 'branch' or 'document' nodes, call explore_tree_node(node_id=...) to drill down to child leaves.
           - STEP 3: As soon as a relevant 'leaf' node appears, immediately call read_leaf_node(leaf_node_id=id) to read and collect evidence.

        3. STRICT EVIDENCE REQUIREMENT:
           - You MUST inspect at least one leaf node containing actual content before finalizing your answer!
           - If a branch does not contain the answer, backtrack and explore another candidate branch.
        """

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Query: {request.query}"}
        ]

        if request.target_docs:
            messages.append({
                "role": "user", 
                "content": f"[Filter]: Restrict search to documents: {', '.join(request.target_docs)}"
            })

        step = 0
        while step < request.max_steps:
            step += 1
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=UNIVERSAL_QUERY_TOOLS,
                tool_choice="auto",
                temperature=0.0
            )

            msg = response.choices[0].message
            u = response.usage
            if u:
                total_tokens += (u.prompt_tokens + u.completion_tokens)

            messages.append(msg.model_dump())

            if not msg.tool_calls:
                break

            for tc in msg.tool_calls:
                func_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}

                step_log = f"Step {step}: {func_name}({args})"
                traversal_path.append(step_log)

                tool_result_str = self.executor.execute_tool(func_name, args)

                if func_name in ("read_leaf_node", "read_leaf_node_supabase"):
                    try:
                        leaf_data = json.loads(tool_result_str)
                        leaf_key = leaf_data.get("leaf_id") or leaf_data.get("title")
                        if "content" in leaf_data and leaf_key not in seen_leaf_ids:
                            seen_leaf_ids.add(leaf_key)
                            collected_leaf_evidences.append(leaf_data)
                    except Exception:
                        pass

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": func_name,
                    "content": tool_result_str[:4000]
                })

        synth_res, s_inp, s_out = QuerySynthesizer.synthesize_answer(
            query=request.query,
            collected_evidences=collected_leaf_evidences,
            client=self.client,
            model=self.model
        )
        total_tokens += (s_inp + s_out)

        exec_time = time.time() - start_time

        return QueryResponse(
            answer=synth_res.answer,
            citations=synth_res.citations,
            traversal_path=traversal_path,
            total_tokens=total_tokens,
            execution_time_seconds=round(exec_time, 2)
        )
