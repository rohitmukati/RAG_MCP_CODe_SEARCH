# 🤖 RAG_MCP_CODE_SEARCH

**RAG_MCP_CODE_SEARCH** is an intelligent **AI-driven code retrieval and modification system** that combines the power of **RAG (Retrieval-Augmented Generation)** with **MCP (Modular Code Processing)**. It enables seamless **code search, draft generation, and automatic synchronization** between your **local workspace** and **Vector Database**.

---

## 🧠 Overview

This system provides an end-to-end solution for intelligent code management:

- 📦 **Upload and index** zipped code projects into a Vector Database (one-time setup)
- 🔍 **Query relevant code snippets** using natural language powered by RAG
- ✍️ **Generate code modifications** automatically via the MCP toolchain
- ✅ **Review and approve** changes before applying them to your local folder and Vector DB
- ⚙️ **FastAPI + Streamlit architecture** for robust backend-frontend integration

🎥 **Demo Video:** [Watch on Loom](https://www.loom.com/share/492fe76b6c9c410f921f5fdae06d4bfa)

---

## ✨ Key Features

- 🔗 **RAG + MCP Integration**: Context-aware intelligent code management
- 🧠 **Semantic Search**: Powered by Vector Database (Zilliz) for accurate code retrieval
- 💬 **Natural Language Interface**: Query your codebase using plain English
- 🧾 **Draft-Before-Apply**: Review generated modifications before committing changes
- 🔄 **Automatic Synchronization**: Keep your local folder and Vector DB in perfect sync
- ⚙️ **Modular Architecture**: Extensible and production-ready design
- 🚀 **Fast Processing**: Efficient indexing and retrieval mechanisms

---

## 🏗️ Project Structure

```
RAG_MCP_CODE_SEARCH/
│
├── src/
│   ├── uploads/           # Folder for uploaded code zips & extracted files
│   ├── files.py           # File handling utilities
│   └── uploads.py         # Upload processing logic
│
├── server.py              # FastAPI backend (API endpoints, VectorDB handling)
├── streamlit.py           # Streamlit frontend for user interaction
├── requirements.txt       # Project dependencies
├── .env                   # Environment variables (see configuration below)
└── README.md              # Project documentation
```

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
FOLDER_TO_UPDATE="path/to/your/project/folder"
FOLDER_TO_UPLOAD="src/uploads"
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

### Step 1: Start the FastAPI Server

```bash
uvicorn server:app --reload
```

The API server will be available at `http://localhost:8000`

### Step 2: Launch the Streamlit Interface

Open a new terminal window and run:

```bash
streamlit run streamlit.py
```

The Streamlit UI will open automatically in your default browser at `http://localhost:8501`

---

## 💡 How It Works

### Workflow Overview

1. **📤 Upload**: Upload a ZIP folder containing your project source files through the Streamlit interface

2. **⚡ Index**: The system extracts and indexes your code into the Vector Database
   - *Note: This process takes some time but only needs to be done once per project*

3. **🔍 Query**: Once indexing is complete, query your codebase using natural language
   - Example: *"Find all authentication functions"* or *"Show me database connection code"*

4. **✍️ Generate**: The MCP-based tool fetches relevant code snippets and generates draft modifications automatically

5. **👀 Review**: Examine the proposed changes in the draft view

6. **✅ Apply**: After approval, the code is updated in both your local folder and the Vector Database seamlessly

### Architecture Flow

```
User Query → Streamlit UI → FastAPI Backend → RAG Pipeline → Vector DB
                                              ↓
                                         Code Retrieval
                                              ↓
                                         MCP Processing
                                              ↓
                                    Draft Code Generation
                                              ↓
                                    User Review & Approval
                                              ↓
                              Local Folder Update + Vector DB Sync
```

---

## 🧠 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit |
| **Backend** | FastAPI |
| **Vector Store** | Zilliz Cloud |
| **Model APIs** | OpenAI, Anthropic |
| **Language Model** | RAG pipeline |
| **Integration** | MCP (Modular Code Processing) |
| **Deployment** | Uvicorn |

---

## 📋 Requirements

- Python 3.8+
- OpenAI API access
- Anthropic API access
- Zilliz Cloud account
- Sufficient storage for code indexing

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🐛 Troubleshooting

### Common Issues

**Issue**: Vector DB connection failed
- **Solution**: Verify your `CLUSTER_ENDPOINT` and `TOKEN` in the `.env` file

**Issue**: Indexing takes too long
- **Solution**: This is normal for large codebases. The indexing only needs to be done once.

**Issue**: API rate limits exceeded
- **Solution**: Check your OpenAI/Anthropic API usage limits and upgrade if necessary

---

## 📞 Support

For questions and support, please open an issue on GitHub or contact the maintainers.

---

**Built with ❤️ using RAG and MCP technologies**
