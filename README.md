<div align="center">

# 🌳 HieraDoc

### Autonomous Hierarchical Tree-of-Thought RAG with Verifiable Line Citations

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Beta-orange.svg)]()
[![Grounding](https://img.shields.io/badge/Grounding-Exact_Line_Numbers-emerald.svg)]()

*An architecture-first alternative to flat chunking for structured documents: contracts, corporate policies, SLAs, and technical standards.*

</div>

---

## 🔍 Motivation & Architectural Trade-offs

Standard RAG architectures chop documents into arbitrary 300–500 token chunks and retrieve them via cosine vector similarity. While effective for simple semantic search, this approach faces well-documented failure modes on structured documents:

1. **Layout Fragmentation**: Arbitrary token boundaries split clauses away from their governing headings (e.g., a sub-clause losing the context of its parent "Exceptions" article).
2. **Imprecise Citations**: Returning an entire chunk ID makes human verification tedious compared to verifiable line numbers `[L0021 - L0024]`.

**HieraDoc** addresses this by modeling documents as a **Hierarchical Tree** (`Cluster` ➜ `Document` ➜ `Branch` ➜ `Leaf`), indexing every line with coordinate tags `[L0001]`, and employing an autonomous **Tree-Traversal Navigator Agent** to zoom down to exact clauses.

---

## ⚖️ Realistic Comparison & Trade-offs

No single retrieval architecture is optimal for all use cases. Here is an objective comparison based on technical realities:

| Metric / Dimension | Flat Vector RAG | Microsoft GraphRAG | **HieraDoc (Hierarchical Tree)** |
| :--- | :---: | :---: | :---: |
| **Primary Use Case** | Broad, unstructured semantic search across diverse docs | Global entity relationships & dataset-wide summarization | Structured & semi-structured docs (Legal, SLAs, Policies, Standards) |
| **Query Latency** | **Fast (~1 – 2s)** (1 vector lookup + 1 LLM call) | Moderate (~4 – 8s) | **Moderate (~5 – 8s)** (2–3 agentic navigation steps) |
| **Ingestion Cost** | **Very Low** (Embedding only) | **Very High** (Entity & relationship extraction per sentence) | **Low-to-Moderate** (Bottom-up chapter & root summarization) |
| **Query Token Cost** | Low (~1k – 2k tokens) | High (~5k – 15k tokens) | Moderate (~4k – 7k tokens for agent reasoning loop) |
| **Citation Precision** | Chunk level (300–500 words) | Entity / Community level | **Exact Line Numbers `[L0017 - L0022]`** |
| **Infrastructure Setup** | Vector DB (Pinecone, Qdrant, Chroma) | Graph DB / NetworkX / Parquet pipelines | **Zero-Setup (Local SQLite file, no servers)** |

### 🎯 When to Use HieraDoc:
* **Legal Agreements & NDAs**: Where missing a governing chapter header or exception invalidates the answer.
* **Service Level Agreements (SLAs) & Corporate Policies**: Where exact numbers, uptime thresholds, and penalties require line-level auditability.
* **Technical Standards & Manuals**: Where information is hierarchically nested (Part ➜ Section ➜ Article ➜ Subsection).

### ⚠️ When NOT to Use HieraDoc:
* **Real-time Chatbots requiring <1s Latency**: Standard flat vector RAG is significantly faster because it bypasses multi-step agent reasoning.
* **Global Entity Networks**: If your queries require connecting non-hierarchical entity webs across hundreds of disparate files (e.g., *"How is Person X linked to Company Y through 10 intermediaries?"*), **Microsoft GraphRAG** is the proper tool.
* **Unstructured Short Text**: Social media posts, single-paragraph emails, or customer reviews do not benefit from tree hierarchy.

---

## 📊 Measured Benchmark (Actual Run)

From our reference benchmark running on a bilingual enterprise dataset with `gpt-4o-mini`:

* **Test Case**: *"Thời hạn bảo mật thông tin được các bên cam kết duy trì trong bao lâu kể từ ngày chấm dứt thỏa thuận?"*
* **Traversal Path**: 2 steps (`search_keyword_index` ➜ `read_leaf_node`)
* **Execution Time**: **7.29 seconds**
* **Tokens Used**: **6,147 tokens**
* **Retrieved Citation**: 
  ```text
  [L0021 - L0024] THỎA THUẬN BẢO MẬT THÔNG TIN VÀ AN TOÀN DỮ LIỆU (NDA) > Chương II
  "Thời hạn bảo mật thông tin được các bên cam kết duy trì trong suốt thời gian 
   hợp tác và kéo dài 05 (năm) năm kể từ ngày thỏa thuận này chấm dứt hoặc hết hiệu lực..."
  ```

---

## 🛠️ Quickstart (in 60 Seconds)

### 1. Installation

```bash
git clone https://github.com/your-username/hieradoc.git
cd hieradoc
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
export OPENAI_API_KEY="sk-..."
# On Windows PowerShell:
# $env:OPENAI_API_KEY="sk-..."
```

### 3. Run Standalone Verification

```bash
python quickstart.py
```

---

## 💻 3-Line Pythonic Usage

```python
from hieradoc import HieraDoc

# 1. Initialize with Zero-Setup Local SQLite
engine = HieraDoc(storage="sqlite", db_path="my_vault.db")

# 2. Ingest & Auto-structure any contract or document
engine.index("examples/sample_nda.txt", doc_id="nda_2026")

# 3. Query with verifiable line-level citations
response = engine.query("Thời hạn bảo mật thông tin kéo dài bao lâu sau khi chấm dứt?")

print(response.answer)
# Output: Thời hạn bảo mật thông tin được cam kết duy trì trong suốt thời gian hợp tác
#         và kéo dài 05 (năm) năm kể từ ngày thỏa thuận chấm dứt.

for c in response.citations:
    print(f"Lines [{c.lines[0]}, {c.lines[-1]}]: \"{c.exact_quote}\"")
```

---

## ⚡ Multi-Agent Parallel Tree Traversal

For cross-document or multi-chapter queries (e.g., *"Compare data retention in Cloud SLA with confidentiality term in NDA"*), HieraDoc uses a **Master Dispatcher** to spawn lightweight **Parallel Sub-Agents**:

```python
# Enable parallel sub-agent exploration (Default: True)
response = engine.query(
    "Compare data retention in Cloud SLA with confidentiality term in NDA",
    parallel=True
)
```

1. **Master Dispatcher**: Evaluates query scope and assigns candidate subtrees to independent worker threads.
2. **Concurrent Workers**: Sub-Agents explore assigned branches simultaneously via `ThreadPoolExecutor` (reducing wall-clock latency by 50%+).
3. **Evidence Aggregation & Deduplication**: Merges leaf evidence before running strict zero-hallucination synthesis.

---

## 🧩 Pluggable Storage Architecture

HieraDoc decouples storage from agent reasoning via `BaseTreeStorage`:

* **`SQLiteTreeStorage` (Default)**: Zero-setup local `.db` file with tokenized n-gram ranking.
* **`SupabaseTreeStorage` (Optional Cloud)**: Multi-tenant PostgreSQL backend for cloud deployment.

---

## 📄 License

Distributed under the **Apache 2.0** License. See `LICENSE` for details.
