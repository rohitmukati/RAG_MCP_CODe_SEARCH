import json
import asyncio
import streamlit as st
from pathlib import Path
import zipfile
import shutil
from difflib import unified_diff
import concurrent.futures
import os

from client import MCPClientUI


UPLOADS_DIR = Path("src/uploads")
UPLOADS_DIR.mkdir(exist_ok=True)


def get_existing_folder():
    """Get the first folder from uploads directory"""
    folders = [f for f in UPLOADS_DIR.iterdir() if f.is_dir()]
    return folders[0] if folders else None


def extract_zip(zip_file, extract_to):
    """Extract zip file to specified directory"""
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(extract_to)


def remove_existing_folders():
    """Remove all folders from uploads directory"""
    for item in UPLOADS_DIR.iterdir():
        if item.is_dir():
            shutil.rmtree(item)


def run_reindex_thread(client):
    """
    Wrapper to run the async reindex_codebase inside a background thread.
    Uses asyncio.run to run the coroutine in a fresh event loop.
    Background thread cannot access st.session_state, so we just run the client
    which will log internally via the client's log method (which tries to append to session_state).
    """
    try:
        print("🔄 Starting reindex in background thread...")
        result = asyncio.run(client.reindex_codebase())
        if result.get("success"):
            print("✅ Background reindex completed successfully")
        else:
            print("❌ Background reindex failed")
    except Exception as e:
        print(f"❌ Thread error: {e}")
        import traceback
        print(traceback.format_exc())


def render_log_entry(log_entry):
    """Render a single log entry with appropriate styling"""
    timestamp = log_entry["timestamp"]
    message = log_entry["message"]
    level = log_entry["level"]
    
    colors = {
        "info": "#E8F4F8",
        "success": "#D4EDDA",
        "error": "#F8D7DA",
        "warning": "#FFF3CD",
        "header": "#CCE5FF",
        "separator": "#F0F0F0",
        "user": "#E7F3FF",
        "assistant": "#F5F5F5",
        "code": "#F8F9FA"
    }
    
    text_colors = {
        "info": "#004085",
        "success": "#155724",
        "error": "#721C24",
        "warning": "#856404",
        "header": "#004085",
        "separator": "#6C757D",
        "user": "#0056B3",
        "assistant": "#495057",
        "code": "#212529"
    }
    
    bg_color = colors.get(level, "#FFFFFF")
    text_color = text_colors.get(level, "#000000")
    
    if level == "separator":
        st.markdown(f"<div style='color: {text_color}; font-family: monospace; font-size: 0.85em;'>{message}</div>", unsafe_allow_html=True)
    elif level == "code":
        with st.expander("📄 View Details", expanded=False):
            st.code(message, language="python")
    elif level == "header":
        st.markdown(f"<div style='background-color: {bg_color}; padding: 8px 12px; border-radius: 5px; color: {text_color}; font-weight: bold; margin: 5px 0;'>[{timestamp}] {message}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='background-color: {bg_color}; padding: 6px 12px; border-radius: 5px; color: {text_color}; margin: 3px 0; font-family: monospace; font-size: 0.9em;'>[{timestamp}] {message}</div>", unsafe_allow_html=True)


def display_code_comparison(old_code: str, new_code: str):
    """Display side-by-side code comparison with diff"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔴 Current Code")
        st.code(old_code, language="python", line_numbers=True)
    
    with col2:
        st.markdown("#### 🟢 Proposed Code")
        st.code(new_code, language="python", line_numbers=True)
    
    with st.expander("🔍 View Detailed Diff", expanded=False):
        diff = list(unified_diff(
            old_code.splitlines(keepends=True),
            new_code.splitlines(keepends=True),
            lineterm='',
            fromfile='current',
            tofile='proposed'
        ))
        
        if diff:
            diff_text = ''.join(diff)
            st.code(diff_text, language="diff")
        else:
            st.info("No differences found")


async def main():
    st.set_page_config(
        page_title="MCP Code Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Auto-refresh when reindexing
    if st.session_state.get("reindex_in_progress"):
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=2000, limit=None, key="reindex_refresh")
        except Exception:
            pass
    
    st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "client" not in st.session_state:
        st.session_state.client = MCPClientUI(api_base_url=os.getenv("API_BASE_URL", "http://localhost:8000"))
        await st.session_state.client.start_mcp_server()
    if "waiting_approval" not in st.session_state:
        st.session_state.waiting_approval = False
    if "pending_changes" not in st.session_state:
        st.session_state.pending_changes = None
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "total_queries" not in st.session_state:
        st.session_state.total_queries = 0
    if "show_reindex_confirm" not in st.session_state:
        st.session_state.show_reindex_confirm = False
    if "reindex_in_progress" not in st.session_state:
        st.session_state.reindex_in_progress = False
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🤖 MCP Code Assistant")
        st.markdown("### Semantic Search & Intelligent Code Updates")
    with col2:
        if st.session_state.waiting_approval:
            st.error("⏳ APPROVAL REQUIRED")
        else:
            st.success("✅ READY")
    
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Statistics")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Queries", st.session_state.total_queries)
        with col_b:
            st.metric("Tool Calls", len(st.session_state.client.tool_executions))
        
        if st.session_state.client.tool_executions:
            total_time = sum(ex['execution_time'] for ex in st.session_state.client.tool_executions)
            st.metric("Total Exec Time", f"{total_time:.2f}s")
        
        st.markdown("---")
        st.header("🛠️ Available Tools")
        for tool in st.session_state.client.tools:
            with st.expander(f"🔧 {tool['name']}", expanded=False):
                st.caption(tool['description'])
        
        st.markdown("---")
        st.header("📁 Codebase Management")
        
        existing_folder = get_existing_folder()
        
        if existing_folder:
            st.success(f"✅ Folder Loaded")
            st.info(f"📂 **{existing_folder.name}**")
            
            # Replace folder section
            st.markdown("#### 🔄 Replace Codebase")
            uploaded_zip = st.file_uploader(
                "Upload new ZIP file",
                type=['zip'],
                key="reupload_zip",
                help="Upload a new ZIP file to replace the current codebase"
            )
            
            if uploaded_zip:
                if st.button("⚠️ Replace Folder", type="secondary", use_container_width=True):
                    with st.spinner("🔄 Replacing folder..."):
                        try:
                            remove_existing_folders()
            
                            temp_zip_path = UPLOADS_DIR / uploaded_zip.name
                            with open(temp_zip_path, "wb") as f:
                                f.write(uploaded_zip.getbuffer())
                            
                            extract_zip(temp_zip_path, UPLOADS_DIR)
                            temp_zip_path.unlink() 
                            
                            st.success("✅ Folder replaced successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
            
            # Reindex section
            st.markdown("#### 📡 Reindex / Upload All")
            if not st.session_state.get("confirm_reindex"):
                if st.button("🚀 Run Full Upload Pipeline", use_container_width=True):
                   st.session_state.confirm_reindex = True
                   st.warning("⚠️ This process may take several minutes.\n\nPlease confirm to continue — don't panic if it takes time.")

            if st.session_state.get("confirm_reindex"):
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Yes, Run Pipeline", use_container_width=True):
                        st.session_state.reindex_in_progress = True
                        st.session_state.confirm_reindex = False

                        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                        future = executor.submit(run_reindex_thread, st.session_state.client)

                        st.session_state.reindex_executor = executor
                        st.session_state.reindex_future = future

                        st.info("⏳ Reindex started in background. Check logs below. UI will auto-refresh while running.")
                        st.rerun()

                with col_no:
                    if st.button("❌ No, Cancel", use_container_width=True):
                        st.session_state.confirm_reindex = False
                        st.info("Operation cancelled.")
                        
            if st.session_state.get("reindex_in_progress"):
                st.markdown("---")
                st.info("🔄 Background reindex is running.")
                future = st.session_state.get("reindex_future")
                if future is not None:
                    if future.done():
                        st.success("✅ Background reindex task finished.")
                        executor = st.session_state.get("reindex_executor")
                        try:
                            if executor:
                                executor.shutdown(wait=False)
                        except Exception:
                            pass
                        st.session_state.reindex_future = None
                        st.session_state.reindex_executor = None
                        st.rerun()
                    else:
                        if st.button("⛔ Attempt to Cancel Reindex"):
                            cancelled = future.cancel()
                            if cancelled:
                                st.warning("⏹️ Cancelled (task had not yet started).")
                                st.session_state.reindex_in_progress = False
                                st.rerun()
                            else:
                                st.warning("Could not cancel — it has likely already started. Wait for it to finish.")
                else:
                    st.info("No background handle found — the task should still be running; logs will show progress.")

        else:
            st.warning("⚠️ No folder found")
            st.markdown("#### 📤 Upload Codebase")
            
            uploaded_zip = st.file_uploader(
                "Upload ZIP file",
                type=['zip'],
                key="initial_upload_zip",
                help="Upload a ZIP file containing your codebase"
            )
            
            if uploaded_zip:
                if st.button("📤 Upload & Extract", type="primary", use_container_width=True):
                    with st.spinner("📤 Uploading and extracting..."):
                        try:
                            temp_zip_path = UPLOADS_DIR / uploaded_zip.name
                            with open(temp_zip_path, "wb") as f:
                                f.write(uploaded_zip.getbuffer())
                            
                            extract_zip(temp_zip_path, UPLOADS_DIR)
                            temp_zip_path.unlink()  
                            
                            st.success("✅ Folder uploaded successfully!")
                            st.info("ℹ️ Now click 'Reindex to Database' to index your code")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
        
        st.markdown("---")
        if st.button("🗑️ Clear Logs", use_container_width=True):
            st.session_state.logs = []
            st.session_state.search_results = None
            st.session_state.client.tool_executions = []
            st.rerun()
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Tool Executions", "🔍 Search Results"])
    
    with tab1:
        st.subheader("💬 Enter Your Request")
        user_query = st.text_area(
            "What would you like to do?",
            placeholder="e.g., Update the login function to add error handling\ne.g., Find all authentication related code",
            height=100,
            key="user_query",
            disabled=st.session_state.waiting_approval
        )
        
        col_submit, col_status = st.columns([1, 3])
        with col_submit:
            if st.button("🚀 Submit", type="primary", disabled=st.session_state.waiting_approval):
                if user_query.strip():
                    st.session_state.logs = []
                    st.session_state.total_queries += 1
                    with st.spinner("⏳ Processing your request... Please wait..."):
                        await st.session_state.client.chat_with_tools(user_query)
                    
                    st.success("✅ Done!")
                    st.rerun()
                else:
                    st.warning("Please enter a query!")
        
        # Approval panel
        if st.session_state.waiting_approval and st.session_state.pending_changes:
            st.markdown("---")
            st.markdown("## 🔐 Code Update Approval Required")
            
            pending = st.session_state.pending_changes
            
            st.info(f"📄 **File:** {pending['file_path']}\n**Chunk ID:** {pending['chunk_id']}")
            
            display_code_comparison(pending['old_code'], pending['new_code'])
            
            st.warning("⚠️ **This will modify:**\n- Vector database embeddings\n- Your codebase")
            
            col_approve, col_reject = st.columns([1, 1])
            with col_approve:
                if st.button("✅ Approve & Execute", type="primary", use_container_width=True):
                    await st.session_state.client.execute_approved_update()
                    st.rerun()
            with col_reject:
                if st.button("❌ Reject Changes", use_container_width=True):
                    st.session_state.client.reject_changes()
                    st.rerun()
        
        # Logs
        st.markdown("---")
        st.subheader("📋 Execution Logs")
        
        log_container = st.container()
        with log_container:
            if st.session_state.logs:
                for log_entry in st.session_state.logs:
                    render_log_entry(log_entry)
            else:
                st.info("No logs yet. Submit a query to get started!")
    
    with tab2:
        st.subheader("📊 Tool Execution History")
        
        if st.session_state.client.tool_executions:
            for idx, exe in enumerate(reversed(st.session_state.client.tool_executions), 1):
                with st.expander(f"🔧 {exe['tool_name']} - {exe['timestamp']}", expanded=False):
                    col_metric1, col_metric2 = st.columns(2)
                    with col_metric1:
                        st.metric("Execution Time", f"{exe['execution_time']:.3f}s")
                    with col_metric2:
                        st.metric("Timestamp", exe['timestamp'])
                    
                    st.markdown("**Input:**")
                    st.json(exe['tool_input'])
                    
                    st.markdown("**Output:**")
                    if isinstance(exe['tool_output'], list):
                        for item in exe['tool_output']:
                            st.json(item)
                    else:
                        st.json(exe['tool_output'])
        else:
            st.info("No tool executions yet.")
    
    with tab3:
        st.subheader("🔍 Search Results")
        
        if st.session_state.search_results:
            results = st.session_state.search_results
            
            # Ensure results is a list
            if not isinstance(results, list):
                results = [results]
            
            for idx, result in enumerate(results, 1):
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except:
                        st.warning(f"Could not parse result #{idx}")
                        continue
                
                if isinstance(result, dict):
                    with st.expander(f"📄 Result #{idx}: {result.get('file_path', 'Unknown')}", expanded=idx == 1):
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Chunk ID", result.get('chunk_id', 'N/A'))
                        with col_b:
                            st.metric("Language", result.get('language', 'N/A'))
                        with col_c:
                            st.metric("Similarity", f"{result.get('similarity_score', 0):.4f}")
                        
                        st.markdown("**Code Snippet:**")
                        st.code(result.get('code_snippet', 'N/A'), language="python", line_numbers=True)
        else:
            st.info("No search results yet. Run a semantic search query!")


if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(main())
        else:
            asyncio.run(main())
    except RuntimeError:
        asyncio.run(main())