# 🤖 RAG_MCP_CODe_SEARCH

**RAG_MCP_CODe_SEARCH** is an intelligent **AI-driven code retrieval and modification system** that combines the power of **RAG (Retrieval-Augmented Generation)** with **MCP (Modular Code Processing)**.  
It enables seamless **code search, draft generation, and automatic updates** to both your **local workspace** and **Vector Database**.

---

## 🧠 Overview

This system allows you to:
- 📦 **Upload zipped code projects** and index them once into a Vector DB.  
- 🔍 **Query relevant code snippets** using natural language powered by **RAG**.  
- ✍️ **Automatically draft code modifications** via the **MCP toolchain**.  
- ✅ **Approve and update** modified code directly in your **local folder** and **Vector DB**.  
- ⚙️ **FastAPI + Streamlit architecture** for smooth backend-frontend integration.  

🎥 **Demo Video:** [Watch on Loom](https://www.loom.com/share/492fe76b6c9c410f921f5fdae06d4bfa)

---

## 🧩 Features

- 🔗 Combines **RAG + MCP** for context-aware intelligent code management.  
- 🧠 Uses **Vector Database (Zilliz)** for semantic code retrieval.  
- 💬 Natural language code search through RAG pipelines.  
- 🧾 Draft generation for code modifications before approval.  
- 🧰 Automatic synchronization between local folder and Vector DB.  
- ⚙️ Modular, extensible, and production-ready setup.

---

## 🏗️ Project Structure

RAG_MCP_CODe_SEARCH/
│
├── src/
│ ├── uploads/ # Folder for uploaded code zips & extracted files
│ └── files.py
│ └── uploads.py
├── server.py # FastAPI backend (API, VectorDB handling)
├── streamlit.py # Streamlit frontend for user interaction
├── requirements.txt # Project dependencies
├── .env # Environment variables (see below)
└── README.md


---

## 🔐 Environment Variables

Create a `.env` file in the root directory with the following content:

```bash
OPENAI_API_KEY="sk-prtBHgA"
CLUSTER_ENDPOINT="https.cloud.zilliz.com"
TOKEN="9cbf4b7035a590884"
COLLECTION_NAME="CodeBase"

ANTHROPIC_API_KEY="skj"
FOLDER_TO_UPDATE=""
FOLDER_TO_UPLOAD="src/uploads"
