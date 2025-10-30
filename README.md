# 🤖 RAG_MCP_CODE_SEARCH

**RAG_MCP_CODE_SEARCH** is an intelligent **AI-driven code retrieval and modification system** that leverages **RAG (Retrieval-Augmented Generation)** with **MCP (Model Context Protocol)**. It enables seamless **code search, draft generation, and automatic synchronization** between your **local workspace** and **Vector Database**.

---

## 🧠 Overview

This system provides an end-to-end solution for intelligent code management using the Model Context Protocol:

- 📦 **Upload and index** zipped code projects into a Vector Database (one-time setup)
- 🔍 **Query relevant code snippets** using natural language powered by RAG
- ✍️ **Generate code modifications** automatically via MCP tools
- ✅ **Review and approve** changes before applying them to your local folder and Vector DB
- 🔌 **MCP Server**: Streamable HTTP server exposing two custom MCP tools
- 🤖 **Anthropic Client**: Communicates with MCP tools for intelligent code operations
- ⚙️ **FastAPI + Streamlit architecture** for robust backend-frontend integration

🎥 **Demo Video:** [Watch on Loom](https://www.loom.com/share/492fe76b6c9c410f921f5fdae06d4bfa)

---

## ✨ Key Features

- 🔗 **MCP Integration**: Implements Model Context Protocol for tool-based AI interactions
- 🧠 **Semantic Search**: Powered by Vector Database (Zilliz) for accurate code retrieval
- 💬 **Natural Language Interface**: Query your codebase using plain English
- 🧾 **Draft-Before-Apply**: Review generated modifications before committing changes
- 🔄 **Automatic Synchronization**: Keep your local folder and Vector DB in perfect sync
- 🛠️ **Two Custom MCP Tools**:
  - **RAG Search Tool**: Semantic code search and retrieval
  - **Code Update Tool**: Updates code in local folder and vector embeddings upon approval
- 🌐 **MCP Streamable HTTP Server**: Exposes tools via HTTP for flexible integration
- 🤖 **Anthropic Client**: Built-in client for seamless communication with MCP tools
- ⚙️ **Modular Architecture**: Extensible and production-ready design

---

## 🏗️ Project Structure

```
RAG_MCP_CODE_SEARCH/
│
├── src/
│   ├── uploads/              # Folder for uploaded code zips & extracted files
│   ├── files.py              # File handling utilities
│   └── uploads.py            # Upload processing logic
│
├── mcp/
│   ├── server.py             # MCP Streamable HTTP Server
│   ├── tools/
│   │   ├── rag_search.py     # RAG Search MCP Tool
│   │   └── code_update.py    # Code Update MCP Tool
│   └── client.py             # Anthropic Client for MCP communication
│
├── server.py                 # FastAPI backend (API endpoints, VectorDB handling)
├── streamlit.py              # Streamlit frontend for user interaction
├── requirements.txt          # Project dependencies
├── .env                      # Environment variables (see configuration below)
└── README.md                 # Project documentation
```

---

## 🔧 MCP Architecture

### Model Context Protocol Implementation

This project implements the **Model Context Protocol (MCP)**, which enables structured communication between AI models and external tools.

```
┌─────────────────┐
│  Anthropic      │
│  Claude Client  │
└────────┬────────┘
         │ MCP Protocol
         ↓
┌─────────────────────┐
│  MCP HTTP Server    │
│  (Streamable)       │
└────────┬────────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌────────┐ ┌────────────┐
│  RAG   │ │   Code     │
│ Search │ │   Update   │
│  Tool  │ │    Tool    │
└────┬───┘ └─────┬──────┘
     │           │
     ↓           ↓
┌─────────────────────┐
│   Vector Database   │
│   Local File System │
└─────────────────────┘
```

### MCP Tools

#### 1. **RAG Search Tool** (`rag_search`)
- **Purpose**: Semantic search through your codebase
- **Input**: Natural language query
- **Output**: Relevant code snippets with context
- **Process**: 
  - Converts query to embeddings
  - Searches Vector DB for similar code
  - Returns ranked results with file paths

#### 2. **Code Update Tool** (`code_update`)
- **Purpose**: Updates code after user approval
- **Input**: File path, new code content, approval status
- **Output**: Confirmation of updates
- **Process**:
  - Updates local file system
  - Regenerates embeddings
  - Updates Vector DB
  - Maintains sync between both stores

---

## 🔐 Environment Configuration

Create a `.env` file in the root directory with the following configuration:

```bash
# OpenAI API Configuration
OPENAI_API_KEY="your-openai-api-key"

# Zilliz Cloud Configuration
CLUSTER_ENDPOINT="your-zilliz-cluster-endpoint"
TOKEN="your-zilliz-token"
COLLECTION_NAME="CodeBase"

# Anthropic API Configuration
ANTHROPIC_API_KEY="your-anthropic-api-key"

# Folder Paths
FOLDER_TO_UPDATE="" ## keep it blank
FOLDER_TO_UPLOAD="src/uploads"

# MCP Server Configuration
MCP_SERVER_HOST="localhost"
MCP_SERVER_PORT="8001"
```

### Configuration Parameters

| Parameter | Description |
|-----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key for embeddings and LLM operations |
| `CLUSTER_ENDPOINT` | Zilliz Cloud cluster endpoint URL |
| `TOKEN` | Authentication token for Zilliz Cloud |
| `COLLECTION_NAME` | Name of the collection in Zilliz (default: "CodeBase") |
| `ANTHROPIC_API_KEY` | Your Anthropic API key for Claude integration |
| `FOLDER_TO_UPDATE` | Local folder path where code updates will be applied |
| `FOLDER_TO_UPLOAD` | Folder for storing uploaded ZIP files and extracted code |
| `MCP_SERVER_HOST` | Host for MCP HTTP server (default: "localhost") |
| `MCP_SERVER_PORT` | Port for MCP HTTP server (default: "8001") |

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/<your-username>/RAG_MCP_CODE_SEARCH.git
cd RAG_MCP_CODE_SEARCH
```

### 2️⃣ Create and Activate Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Configure Environment Variables

Create a `.env` file in the root directory and add your API keys and configuration as shown in the [Environment Configuration](#-environment-configuration) section above.

---

## ▶️ Running the Project

### Step 1: Start the FastAPI Backend

In a new terminal:

```bash
uvicorn server:app --reload
```

The API server will be available at `http://localhost:8000`

### Step 2: Launch the Streamlit Interface

Open another terminal and run:

```bash
streamlit run streamlit.py
```


---n

### MCP Communication Flow

```
User Query → Streamlit UI → Anthropic Client → MCP HTTP Server
                                                      ↓
                                              [Tool Selection]
                                                      ↓
                                    ┌─────────────────┴─────────────────┐
                                    ↓                                   ↓
                            RAG Search Tool                     Code Update Tool
                                    ↓                                   ↓
                            Vector DB Query                   Local FS + Vector DB
                                    ↓                                   ↓
                            Return Results              Return Confirmation
                                    ↓                                   ↓
                                    └─────────────────┬─────────────────┘
                                                      ↓
                                          MCP HTTP Server Response
                                                      ↓
                                            Anthropic Client
                                                      ↓
                                              User Interface
```

---


### Direct MCP Server API

**RAG Search Endpoint:**
```bash
POST http://localhost:8001/tools/rag_search
Content-Type: application/json

{
  "query": "database connection code"
}
```

**Code Update Endpoint:**
```bash
POST http://localhost:8001/tools/code_update
Content-Type: application/json

{
  "file_path": "src/db.py",
  "content": "updated code content",
  "approved": true
}
```

---

## 🧠 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit |
| **Backend** | FastAPI |
| **Vector Store** | Zilliz Cloud |
| **Model APIs** | OpenAI, Anthropic |
| **Protocol** | Model Context Protocol (MCP) |
| **MCP Server** | Custom Streamable HTTP Server |
| **Language Model** | Claude (via Anthropic API) |
| **RAG Pipeline** | Custom implementation |
| **Deployment** | Uvicorn |

---

## 📋 Requirements

- Python 3.8+
- OpenAI API access
- Anthropic API access (Claude)
- Zilliz Cloud account
- Sufficient storage for code indexing
- Network access for MCP server communication

---

## 🔍 MCP Protocol Benefits

### Why Model Context Protocol?

1. **🔌 Standardized Tool Communication**: Consistent interface for AI-tool interactions
2. **🔄 Stateless Operations**: Each tool call is independent and reproducible
3. **📡 HTTP Streamable**: Real-time streaming responses for large operations
4. **🧩 Modular Design**: Easy to add new tools without changing core architecture
5. **🤖 AI-Native**: Designed specifically for LLM-tool interactions
6. **🔒 Secure**: Controlled access to file system and database operations

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Adding New MCP Tools

1. Create a new tool in `mcp/tools/`
2. Implement the tool interface
3. Register the tool in `mcp/server.py`
4. Update the Anthropic client if needed

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🐛 Troubleshooting

### Common Issues

**Issue**: MCP Server connection failed
- **Solution**: Ensure MCP server is running on the correct port and check firewall settings

**Issue**: Vector DB connection failed
- **Solution**: Verify your `CLUSTER_ENDPOINT` and `TOKEN` in the `.env` file

**Issue**: Indexing takes too long
- **Solution**: This is normal for large codebases. The indexing only needs to be done once.

**Issue**: API rate limits exceeded
- **Solution**: Check your OpenAI/Anthropic API usage limits and upgrade if necessary

**Issue**: MCP tools not responding
- **Solution**: Check MCP server logs and ensure all dependencies are installed correctly

---

## 📚 Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Anthropic Claude API Documentation](https://docs.anthropic.com/)
- [Zilliz Cloud Documentation](https://docs.zilliz.com/)


---

**Built with ❤️ using RAG, MCP, and Claude AI*
