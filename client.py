import json
import asyncio
import streamlit as st
import httpx
from anthropic import Anthropic
from dotenv import load_dotenv
from datetime import datetime
import time
import os

load_dotenv()


class MCPClientUI:
    def __init__(self, api_base_url: str = None):
        self.anthropic_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        if api_base_url is None:
            api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        
        self.api_base_url = api_base_url
        self.tools = []
        self.tool_executions = []
        
    def log(self, message, level="info", expandable=False, expanded=True):
        """Add log message to session state - safe to call from background threads"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = {
            "timestamp": timestamp,
            "message": message,
            "level": level,
            "expandable": expandable,
            "expanded": expanded
        }
    
        
        try:
            if hasattr(st, 'session_state') and st.session_state is not None:
                if "logs" in st.session_state:
                    st.session_state.logs.append(log_entry)
                else:
                    print(f"[{timestamp}] {message}")
            else:
                print(f"[{timestamp}] {message}")
        except Exception as e:
            print(f"[{timestamp}] {message}")
            if "error" in level or "warning" in level:
                print(f"  (Error: {e})")
        
    async def start_mcp_server(self):
        """Initialize MCP tools from FastAPI routes"""
        self.log("🚀 Initializing MCP Tools...", "info")
        
        try:
            async with httpx.AsyncClient() as client:
                health_response = await client.get(f"{self.api_base_url}/health", timeout=5.0)
                if health_response.status_code == 200:
                    self.log("✅ Connected to Vector DB Code Service", "success")
                else:
                    self.log("⚠️ Vector DB Service health check failed", "warning")
        except Exception as e:
            self.log(f"⚠️ Cannot connect to Vector DB Service: {e}", "warning")
        
        self.tools = [
            {
                "name": "semantic_search",
                "description": "Semantic search for similar code snippets. Extract the main target/component from user's query and search for that",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer", "default": 2}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "update_code",
                "description": "Update a code chunk in the codebase. Only use this if the user wants to modify/add/remove/update code. else dont use this tool. Make sure to get user's approval before making any changes.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "chunk_id": {
                            "type": "integer",
                            "description": "The chunk_id from semantic_search results"
                        },
                        "new_code": {
                            "type": "string",
                            "description": "The complete updated code"
                        }
                    },
                    "required": ["chunk_id", "new_code"]
                }
            }
        ]
        self.log("✅ MCP Tools initialized", "success")
        self.log(f"  • semantic_search - Search your codebase", "info")
        self.log(f"  • update_code - Update code chunks (with approval)", "info")
        return True
    
    async def call_mcp_tool(self, tool_name: str, tool_input: dict):
        """Call MCP tool via FastAPI endpoints"""
        try:
            start_time = time.time()
            self.log(f"🔧 Calling tool: {tool_name}", "info")
            self.log(f"📥 Input: {json.dumps(tool_input, indent=2)}", "code")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                if tool_name == "semantic_search":
                    response = await client.post(
                        f"{self.api_base_url}/api/search",
                        json={
                            "query": tool_input.get("query"),
                            "top_k": tool_input.get("top_k", 2)
                        }
                    )
                    result_data = response.json()
                    if response.status_code == 200:
                        search_results = result_data.get("results", [])
                        if isinstance(search_results, list) and len(search_results) > 0:
                            result = [r if isinstance(r, dict) else r.__dict__ if hasattr(r, '__dict__') else r for r in search_results]
                        else:
                            result = []
                    else:
                        result = {"error": result_data.get("detail", "Search failed")}
                
                elif tool_name == "update_code":
                    response = await client.post(
                        f"{self.api_base_url}/api/update",
                        json={
                            "chunk_id": tool_input.get("chunk_id"),
                            "new_code": tool_input.get("new_code")
                        }
                    )
                    result = response.json()
                    if response.status_code != 200:
                        result = {"error": result.get("detail", "Update failed")}
                
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
            
            execution_time = time.time() - start_time
            
            self.tool_executions.append({
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_output": result,
                "execution_time": execution_time,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            result_preview = str(result)[:300] + "..." if len(str(result)) > 300 else str(result)
            self.log(f"📤 Result preview: {result_preview}", "code")
            self.log(f"⏱️ Execution time: {execution_time:.3f}s", "success")
            return result
        except Exception as e:
            self.log(f"❌ Tool execution failed: {e}", "error")
            import traceback
            self.log(traceback.format_exc(), "error")
            return {"error": str(e)}
    
    async def chat_with_tools(self, user_message: str):
        """Main chat function with agentic loop"""
        self.log("=" * 70, "separator")
        self.log(f"💬 USER REQUEST", "header")
        self.log("=" * 70, "separator")
        self.log(f"{user_message}", "user")
        
        messages = [{"role": "user", "content": user_message}]
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            self.log("=" * 70, "separator")
            self.log(f"🔄 ITERATION {iteration}", "header")
            self.log("=" * 70, "separator")
            
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                tools=self.tools,
                messages=messages
            )
            
            for block in response.content:
                if hasattr(block, 'text'):
                    self.log(f"💭 Claude: {block.text}", "assistant")
            
            has_tool_use = False
            for block in response.content:
                if block.type == "tool_use":
                    has_tool_use = True
                    tool_name = block.name
                    tool_input = block.input
                    tool_id = block.id
                    
                    self.log(f"🛠️ Tool Request: {tool_name}", "header")
                    
                    if tool_name == "update_code":
                        chunk_id = tool_input.get("chunk_id")
                        new_code = tool_input.get("new_code")
                        
                        old_code = ""
                        file_path = ""
                        if st.session_state.search_results:
                            for result in st.session_state.search_results:
                                if result.get("chunk_id") == chunk_id:
                                    old_code = result.get("code_snippet", "")
                                    file_path = result.get("file_path", "")
                                    break
                        
                        st.session_state.pending_changes = {
                            "tool_name": tool_name,
                            "tool_input": tool_input,
                            "tool_id": tool_id,
                            "chunk_id": chunk_id,
                            "file_path": file_path,
                            "old_code": old_code,
                            "new_code": new_code,
                            "messages": messages.copy(),
                            "response_content": response.content
                        }
                        
                        self.log("=" * 70, "separator")
                        self.log(f"🔐 APPROVAL REQUIRED", "header")
                        self.log("=" * 70, "separator")
                        self.log(f"File: {file_path}", "warning")
                        self.log(f"Chunk ID: {chunk_id}", "warning")
                        self.log("⚠️  Please review the changes in the approval panel", "warning")
                        self.log("=" * 70, "separator")
                        
                        st.session_state.waiting_approval = True
                        return 
                    
                    else:
                        result = await self.call_mcp_tool(tool_name, tool_input)
                        
                        if tool_name == "semantic_search" and result:
                            st.session_state.search_results = result
                            
                            if isinstance(result, list) and len(result) > 0:
                                self.log("=" * 70, "separator")
                                self.log("🔍 SEMANTIC SEARCH RESULTS", "header")
                                self.log("=" * 70, "separator")
                                for idx, res in enumerate(result):
                                    self.log(f"📋 Result #{idx + 1}", "info")
                                    self.log(f"  • File: {res.get('file_path')}", "info")
                                    self.log(f"  • Chunk ID: {res.get('chunk_id')}", "info")
                                    self.log(f"  • Similarity: {res.get('similarity_score', 'N/A')}", "info")
                        
                        messages.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        messages.append({
                            "role": "user",
                            "content": [{
                                "type": "tool_result",
                                "tool_use_id": tool_id,
                                "content": json.dumps(result) if result else "No results"
                            }]
                        })
            
            if not has_tool_use or response.stop_reason == "end_turn":
                self.log("=" * 70, "separator")
                self.log("✅ CONVERSATION COMPLETE", "header")
                self.log("=" * 70, "separator")
                break
        
        if iteration >= max_iterations:
            self.log("⚠️ Maximum iterations reached", "warning")
        
        st.session_state.waiting_approval = False
    
    async def execute_approved_update(self):
        """Execute the approved update and continue conversation"""
        pending = st.session_state.pending_changes
        
        self.log("=" * 70, "separator")
        self.log(f"✅ USER APPROVED UPDATE", "header")
        self.log("=" * 70, "separator")
        
        result = await self.call_mcp_tool(
            pending["tool_name"],
            pending["tool_input"]
        )
        
        self.log("=" * 70, "separator")
        self.log(f"🎉 UPDATE COMPLETE", "header")
        self.log("=" * 70, "separator")
        if isinstance(result, dict) and result.get("success"):
            self.log(f"✓ Database updated: {result.get('database_updated')}", "success")
            self.log(f"✓ File updated: {result.get('file_updated')}", "success")
            self.log(f"✓ Path: {result.get('full_local_path')}", "success")
        else:
            self.log(f"✗ Update failed: {result.get('error', 'Unknown error')}", "error")
        self.log("=" * 70, "separator")
        
        messages = pending["messages"]
        messages.append({
            "role": "assistant",
            "content": pending["response_content"]
        })
        messages.append({
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": pending["tool_id"],
                "content": json.dumps(result)
            }]
        })
        
        final_response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=self.tools,
            messages=messages
        )
        
        for block in final_response.content:
            if hasattr(block, 'text'):
                self.log(f"💭 Claude: {block.text}", "assistant")
        
        st.session_state.waiting_approval = False
        st.session_state.pending_changes = None
    
    def reject_changes(self):
        """Reject the proposed changes"""
        self.log("=" * 70, "separator")
        self.log(f"❌ UPDATE REJECTED BY USER", "header")
        self.log("=" * 70, "separator")
        self.log(f"✓ No changes made to files or database", "success")
        self.log(f"✓ Your code is safe and unchanged", "success")
        self.log("=" * 70, "separator")
        
        st.session_state.waiting_approval = False
        st.session_state.pending_changes = None
    
    async def reindex_codebase(self):
        """Trigger the upload-all endpoint to reindex the codebase"""
        try:
            self.log("=" * 70, "separator")
            self.log("🔄 RUNNING FULL UPLOAD PIPELINE", "header")
            self.log("=" * 70, "separator")
            self.log("⏳ This may take a few minutes...", "warning")

            async with httpx.AsyncClient(timeout=600.0) as client:
                self.log("📡 Sending request to /api/upload-all...", "info")
                response = await client.post(f"{self.api_base_url}/api/upload-all")
                self.log(f"📥 Response status: {response.status_code}", "info")

            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("success"):
                        self.log(result.get("message", "✅ Upload pipeline completed successfully"), "success")
                        self.log("=" * 70, "separator")
                        return {"success": True}
                    else:
                        self.log(f"⚠️ Upload failed: {result.get('error', 'Unknown error')}", "warning")
                except Exception as e:
                    self.log(f"⚠️ Could not parse response: {e}", "warning")
            else:
                error_detail = response.text if response.text else f"HTTP {response.status_code}"
                self.log(f"❌ Upload pipeline failed: {error_detail}", "error")

            self.log("=" * 70, "separator")
            return {"success": False}

        except Exception as e:
            self.log(f"❌ Upload pipeline error: {e}", "error")
            import traceback
            self.log(traceback.format_exc(), "error")
            self.log("=" * 70, "separator")
            return {"success": False, "error": str(e)}
        finally:
            try:
                st.session_state.reindex_in_progress = False
            except Exception as e:
                print(f"Could not update session state in finally block (expected in background thread): {e}")