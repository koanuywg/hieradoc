import os
import json
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from pydantic import BaseModel, Field
from hieradoc.storage.base import BaseTreeStorage
from hieradoc.agents.synthesizer import QuerySynthesizer
from hieradoc.schemas.query import QueryRequest, QueryResponse

class BranchCandidate(BaseModel):
    branch_id: str = Field(..., description="ID of the candidate branch/node to explore")
    branch_title: str = Field(..., description="Title of the branch")
    focus_objective: str = Field(..., description="Specific objective for the sub-agent exploring this branch")
    rollup_full_branch: bool = Field(False, description="True if sub-agent should read the entire branch at once (Parent Rollup)")

class QueryExpansion(BaseModel):
    expanded_terms: List[str] = Field(..., description="3 to 5 domain synonyms, related legal/technical terms, or conceptual variations")
    intent_summary: str = Field(..., description="Core underlying user intent")

class DispatcherDecision(BaseModel):
    reasoning: str = Field(..., description="Why these branches were selected for parallel exploration")
    selected_branches: List[BranchCandidate] = Field(..., description="List of 1 to 4 candidate branches to explore in parallel")

class BranchSubAgent:
    """
    Worker Sub-Agent: Explores a specific designated branch of the hierarchical tree
    in parallel, drills down to child leaves, and extracts verbatim grounded evidence.
    """

    def __init__(self, storage: BaseTreeStorage, client: OpenAI, model: str = "gpt-4o-mini"):
        self.storage = storage
        self.client = client
        self.model = model

    def explore_branch(self, branch_id: str, branch_title: str, objective: str, rollup_full_branch: bool = False) -> Dict[str, Any]:
        traversal_logs = [f"[SubAgent: {branch_title}] Started exploration for objective: '{objective}'"]
        collected_evidences = []

        # Parent Rollup: Nếu được yêu cầu đọc trọn vẹn cả Chương/Nhánh
        if rollup_full_branch:
            full_res = self.storage.read_branch_full(branch_id)
            if "content" in full_res and full_res["content"]:
                collected_evidences.append(full_res)
                traversal_logs.append(f"[SubAgent: {branch_title}] Rolled up entire branch ({full_res.get('leaves_count', 0)} leaves, Lines {full_res.get('start_line')}-{full_res.get('end_line')})")
                return {
                    "branch_id": branch_id,
                    "branch_title": branch_title,
                    "evidences": collected_evidences,
                    "traversal_logs": traversal_logs
                }

        # 1. Khảo sát các node con của nhánh này
        children = self.storage.explore_node(branch_id)
        traversal_logs.append(f"[SubAgent: {branch_title}] Found {len(children)} child nodes")

        if not children:
            # Nhánh rỗng hoặc chính nó là leaf
            leaf_res = self.storage.read_leaf(branch_id)
            if "content" in leaf_res and leaf_res["content"]:
                collected_evidences.append(leaf_res)
                traversal_logs.append(f"[SubAgent: {branch_title}] Read direct leaf content")
            return {
                "branch_id": branch_id,
                "branch_title": branch_title,
                "evidences": collected_evidences,
                "traversal_logs": traversal_logs
            }

        # 2. Phân loại node con
        child_leaves = [c for c in children if c.get("node_type") == "leaf"]
        child_branches = [c for c in children if c.get("node_type") in ("branch", "document")]

        # Nếu có lá, dùng LLM chọn nhanh các lá phù hợp nhất với objective
        candidate_leaves_to_read = []
        if child_leaves:
            if len(child_leaves) <= 2:
                candidate_leaves_to_read = child_leaves
            else:
                # Prompt nhẹ để chọn các lá liên quan
                leaf_options = [{"id": l["id"], "title": l["title"], "summary": l.get("summary", "")} for l in child_leaves]
                prompt = (
                    f"Objective: {objective}\n\n"
                    f"Available Leaves:\n{json.dumps(leaf_options, ensure_ascii=False)}\n\n"
                    "Select up to 3 leaf IDs that most likely contain direct evidence to answer this objective. "
                    "Return a JSON list of string IDs, e.g. [\"id1\", \"id2\"]."
                )
                try:
                    resp = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "You are a fast leaf selector. Reply strictly with a JSON list of IDs."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.0
                    )
                    raw_ids = json.loads(resp.choices[0].message.content.strip().replace("```json", "").replace("```", ""))
                    if isinstance(raw_ids, list):
                        candidate_leaves_to_read = [l for l in child_leaves if l["id"] in raw_ids]
                except Exception:
                    candidate_leaves_to_read = child_leaves[:2]

            # Đọc nội dung nguyên văn các lá được chọn
            for leaf in candidate_leaves_to_read:
                leaf_data = self.storage.read_leaf(leaf["id"])
                if "content" in leaf_data and leaf_data["content"]:
                    collected_evidences.append(leaf_data)
                    traversal_logs.append(f"[SubAgent: {branch_title}] Read leaf '{leaf['title']}' (Lines {leaf_data.get('start_line')}-{leaf_data.get('end_line')})")

        # Nếu có sub-branches con (ví dụ Document -> Branch -> Leaf), đệ quy đào sâu
        for s_branch in child_branches[:2]:
            sub_res = self.explore_branch(s_branch["id"], s_branch["title"], objective)
            collected_evidences.extend(sub_res.get("evidences", []))
            traversal_logs.extend(sub_res.get("traversal_logs", []))

        return {
            "branch_id": branch_id,
            "branch_title": branch_title,
            "evidences": collected_evidences,
            "traversal_logs": traversal_logs
        }


class ParallelTreeAgent:
    """
    Multi-Agent Parallel Tree Navigator.
    1. Master Dispatcher analyzes query and selects K candidate branches.
    2. Spawns BranchSubAgents in parallel (using ThreadPoolExecutor).
    3. Aggregates all evidence and synthesizes final answer with line-level citations.
    """

    def __init__(
        self,
        storage: BaseTreeStorage,
        model_name: str = "gpt-4o-mini",
        max_parallel_workers: int = 4,
        client: Optional[OpenAI] = None
    ):
        self.storage = storage
        self.model = model_name
        self.max_parallel_workers = max_parallel_workers
        self.client = client or OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def query(self, request: QueryRequest | str) -> QueryResponse:
        if isinstance(request, str):
            request = QueryRequest(query=request)

        start_time = time.time()
        traversal_path = []
        total_tokens = 0

        # ==============================================================
        # BƯỚC 1: MASTER DISPATCHER - AGENTIC QUERY EXPANSION & ROUTING
        # ==============================================================
        # 1.0 Agentic Query Expansion: Master Agent mở rộng từ đồng nghĩa trước khi truy vấn storage
        exp_prompt = """
        You are an Expert Semantic Query Expander for Hierarchical Document Intelligence.
        Analyze the user's query and generate 3 to 5 domain synonyms, technical keywords, 
        or legal terminology variations that capture the underlying semantic intent.
        """
        exp_resp = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": exp_prompt},
                {"role": "user", "content": f"User Query: {request.query}"}
            ],
            response_format=QueryExpansion,
            temperature=0.0
        )
        expanded: QueryExpansion = exp_resp.choices[0].message.parsed
        if exp_resp.usage:
            total_tokens += (exp_resp.usage.prompt_tokens + exp_resp.usage.completion_tokens)

        traversal_path.append(f"Master Agentic Expansion: {expanded.expanded_terms}")

        # 1.1 Tìm kiếm các nhánh ứng viên qua tập từ khóa mở rộng đa dạng (Multi-keyword retrieval)
        search_terms = [request.query] + (expanded.expanded_terms if expanded else [])
        keyword_matches = []
        for term in search_terms[:5]:
            m_list = self.storage.search_keyword(term, limit=4)
            keyword_matches.extend(m_list)
        
        # 1.2 Khảo sát các Cụm Gốc / Văn Bản
        root_nodes = self.storage.explore_node(None)

        # Gom danh sách các ứng viên nhánh tiềm năng để Master LLM lựa chọn
        branch_candidates_pool = []
        seen_ids = set()

        for m in keyword_matches:
            if m["id"] not in seen_ids:
                seen_ids.add(m["id"])
                branch_candidates_pool.append({
                    "id": m["id"],
                    "title": m["title"],
                    "type": m.get("node_type"),
                    "summary": (m.get("summary") or "")[:150]
                })

        for r in root_nodes:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                branch_candidates_pool.append({
                    "id": r["id"],
                    "title": r["title"],
                    "type": r.get("node_type"),
                    "summary": (r.get("summary") or "")[:150]
                })

        dispatcher_prompt = """
        You are the Master Tree Dispatcher for a Hierarchical Multi-Agent RAG System.
        Given the user query and candidate branches/documents from the tree, select 1 to 4 distinct branches 
        that should be explored SIMULTANEOUSLY by parallel Sub-Agents.

        Selection Rules:
        - If the query requires cross-chapter or cross-document comparison, pick branches from BOTH sides so sub-agents can run in parallel.
        - If the query targets a specific topic, pick the top 2 most promising candidate branches (to prevent cascade failure).
        - Assign a clear, specific focus_objective for each sub-agent.
        """

        dispatcher_user_content = (
            f"USER QUERY: {request.query}\n\n"
            f"AVAILABLE TREE BRANCH CANDIDATES:\n"
            f"{json.dumps(branch_candidates_pool, ensure_ascii=False, indent=2)}"
        )

        resp = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": dispatcher_prompt},
                {"role": "user", "content": dispatcher_user_content}
            ],
            response_format=DispatcherDecision,
            temperature=0.0
        )

        decision: DispatcherDecision = resp.choices[0].message.parsed
        if resp.usage:
            total_tokens += (resp.usage.prompt_tokens + resp.usage.completion_tokens)

        traversal_path.append(f"Master Dispatcher: {decision.reasoning}")
        traversal_path.append(f"Spawned {len(decision.selected_branches)} Parallel Sub-Agents: {[b.branch_title for b in decision.selected_branches]}")

        # ==============================================================
        # BƯỚC 2: CHẠY SONG SONG CÁC SUB-AGENTS (PARALLEL EXECUTION)
        # ==============================================================
        all_collected_evidences = []
        seen_evidence_keys = set()

        def _run_sub_agent(candidate: BranchCandidate):
            sub_agent = BranchSubAgent(storage=self.storage, client=self.client, model=self.model)
            return sub_agent.explore_branch(
                branch_id=candidate.branch_id,
                branch_title=candidate.branch_title,
                objective=candidate.focus_objective,
                rollup_full_branch=candidate.rollup_full_branch
            )

        workers_count = min(len(decision.selected_branches), self.max_parallel_workers)
        with ThreadPoolExecutor(max_workers=max(1, workers_count)) as executor:
            future_to_branch = {
                executor.submit(_run_sub_agent, b): b for b in decision.selected_branches
            }

            for future in as_completed(future_to_branch):
                b_info = future_to_branch[future]
                try:
                    res = future.result()
                    for log in res.get("traversal_logs", []):
                        traversal_path.append(log)

                    for ev in res.get("evidences", []):
                        ev_key = ev.get("leaf_id") or ev.get("title")
                        if ev_key not in seen_evidence_keys:
                            seen_evidence_keys.add(ev_key)
                            all_collected_evidences.append(ev)
                except Exception as e:
                    traversal_path.append(f"[SubAgent: {b_info.branch_title}] Error during parallel run: {str(e)}")

        # ==============================================================
        # BƯỚC 3: TỔNG HỢP BẰNG CHỨNG & TRÍCH DẪN SỐ DÒNG (SYNTHESIZER)
        # ==============================================================
        synth_res, s_inp, s_out = QuerySynthesizer.synthesize_answer(
            query=request.query,
            collected_evidences=all_collected_evidences,
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
