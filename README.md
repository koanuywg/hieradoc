<div align="center">

# 🌳 HieraDoc

### Autonomous Hierarchical Tree-of-Thought RAG with Zero-Hallucination Line Citations

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Beta-orange.svg)]()
[![Zero-Hallucination](https://img.shields.io/badge/Grounding-100%25_Verified-emerald.svg)]()

*Stop dumping long documents into flat vector chunks. Navigate them hierarchically like a human expert.*

</div>

---

## ⚡ The Problem: Why Traditional RAG Fails on Complex Docs

Standard RAG chops documents into arbitrary 500-token chunks and searches them using cosine vector similarity. On complex documents (legal contracts, corporate policies, enterprise SLAs, academic papers), this results in:

- ❌ **Lost in the Middle**: Vector embeddings miss high-level contextual hierarchy.
- ❌ **Hallucinated Citations**: Returning chunk IDs without exact line numbers or verifiable proof.
- ❌ **Expensive GraphRAG Overkill**: Knowledge graph approaches often require hundreds of thousands of LLM tokens per document just to extract entities.

## 🚀 The Solution: HieraDoc

**HieraDoc** indexes documents into a self-organizing **Hierarchical Document Tree** (Cluster ➜ Document ➜ Branch ➜ Leaf), indexes every line with zero-loss coordinates `[L0001]`, and deploys an autonomous **Tree-Traversal Navigator Agent** to zoom into exact clauses with 100% verifiable citations.

```
                      [ Root Cluster: Corporate Governance ]
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
     [ Document: Cloud Hosting SLA ]             [ Document: Confidentiality NDA ]
                 │                                               │
         ┌───────┴───────┐                               ┌───────┴───────┐
         ▼               ▼                               ▼               ▼
   [ Part I: SLA ] [ Part II: Security ]           [ Chap I: Scope ] [ Chap II: Obligations ]
         │                                                               │
   [ Article 1: 99.95% Uptime ]                                    [ Article 3: 5-Year Term ]
   (Lines L0005 - L0009)                                           (Lines L0021 - L0024)
```

---

## 📊 Comparison

| Capability | Flat Vector RAG | Microsoft GraphRAG | **HieraDoc (Ours)** |
| :--- | :---: | :---: | :---: |
| **Document Understanding** | Low (Isolated chunks) | High (Entity graphs) | **High (Document Hierarchy)** |
| **Token Cost** | $ | $$$$ (Very expensive) | **$$ (Optimal Zoom-in)** |
| **Citation Precision** | Chunk-level | Entity-level | **Exact Line Numbers `[L0017]`** |
| **Zero-Hallucination Guarantee** | ❌ None | ⚠️ Partial | **✅ 100% Grounded in Leaf Text** |
| **Setup Complexity** | Vector DB required | Neo4j / Huge pipeline | **Zero-Setup (Local SQLite)** |

---

## 🛠️ Quickstart (in 60 Seconds)

### 1. Installation

```bash
git clone https://github.com/your-username/hieradoc.git
cd hieradoc
pip install -r requirements.txt
```

### 2. Set your OpenAI Key

```bash
export OPENAI_API_KEY="sk-..."
# On Windows PowerShell:
# $env:OPENAI_API_KEY="sk-..."
```

### 3. Run the Demo

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
response = engine.query("What is the confidentiality duration after termination?")

print(response.answer)
# Output: The confidentiality obligation persists during cooperation and extends 
#         for 5 (five) years following agreement termination.

for c in response.citations:
    print(f"Lines {c.lines}: {c.exact_quote}")
    # Output: Lines [21, 24]: "Thời hạn bảo mật thông tin được các bên cam kết duy trì..."
```

---

## 🧩 Pluggable Architecture

HieraDoc is designed to be **storage-agnostic** and **model-agnostic**:

```python
# Use local SQLite file (Default, zero setup)
engine = HieraDoc(storage="sqlite", db_path="vault.db")

# Or connect to enterprise cloud PostgreSQL / Supabase
from hieradoc.storage.supabase import SupabaseTreeStorage
cloud_storage = SupabaseTreeStorage(url="...", key="...")
engine = HieraDoc(storage=cloud_storage)
```

---

## 📁 Repository Structure

```
hieradoc/
├── hieradoc/
│   ├── indexer.py              # Ingestion engine & hierarchical tree builder
│   ├── storage/                # Pluggable storage (SQLite, Supabase)
│   ├── agents/                 # Autonomous Navigator & Grounded Synthesizer
│   ├── tools/                  # Layout scanner, Text slicer, Universal tools
│   ├── core/                   # Text extractor & [L0001] line-number indexer
│   └── schemas/                # Clean Pydantic data models
├── examples/                   # Sample documents
├── quickstart.py               # Standalone 60-second verification script
├── pyproject.toml              # Pip package configuration
└── LICENSE                     # Apache 2.0
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **Apache 2.0** License. See `LICENSE` for more information.
