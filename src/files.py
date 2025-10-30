import os
import re
from langchain_openai import OpenAIEmbeddings
from pymilvus import MilvusClient
from dotenv import load_dotenv

load_dotenv()


CLUSTER_ENDPOINT = os.getenv("CLUSTER_ENDPOINT")
TOKEN = os.getenv("TOKEN")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "code_embeddings")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LOCAL_FOLDER = os.getenv("FOLDER_TO_UPDATE", ".")


class VectorDBService:
    def __init__(self):
        self.milvus_client = MilvusClient(uri=CLUSTER_ENDPOINT, token=TOKEN)
        self.embedder = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=OPENAI_API_KEY
        )
        self.collection_name = COLLECTION_NAME
        self.local_root_path = os.path.abspath(LOCAL_FOLDER)
        print(f"Local code root path: {self.local_root_path}")
        print(f"Path exists: {os.path.exists(self.local_root_path)}")
    
    def search_similar_code(self, query: str, top_k: int = 2):
        """Search for similar code snippets."""
        try:
            query_vector = self.embedder.embed_query(query)
            
            results = self.milvus_client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                limit=top_k,
                output_fields=["my_id", "file_path", "file_name", "language", 
                             "chunk_index", "code_snippet"]
            )
            
            formatted_results = []
            for hits in results:
                for hit in hits:
                    formatted_results.append({
                        "chunk_id": hit["entity"]["my_id"],
                        "file_path": hit["entity"]["file_path"],
                        "file_name": hit["entity"]["file_name"],
                        "language": hit["entity"]["language"],
                        "chunk_index": hit["entity"]["chunk_index"],
                        "code_snippet": hit["entity"]["code_snippet"],
                        "similarity_score": hit["distance"]
                    })
            
            return formatted_results
        except Exception as e:
            print(f"Error searching code: {e}")
            return []
    
    def get_full_local_path(self, relative_path: str):
        """
        Convert relative path from database to full local path.
        Handles both absolute and relative paths properly.
        """

        relative_path = relative_path.lstrip('/')
        full_path = os.path.join(self.local_root_path, relative_path)
        full_path = os.path.normpath(full_path)
        try:
            real_root = os.path.realpath(self.local_root_path)
            real_path = os.path.realpath(full_path)
            
            if not real_path.startswith(real_root):
                print(f"⚠ Warning: Path traversal detected. Using root instead.")
                return real_root
        except Exception as e:
            print(f"Warning during path validation: {e}")
        
        return full_path
    
    def simple_exact_replace(self, file_content: str, old_code: str, new_code: str):
        """
        Simple and direct replacement with multiple fallback strategies.
        Tries: exact match → normalized whitespace → JSON normalize → smart replacement
        """
        
        if old_code in file_content:
            print("✓ Strategy 1: Exact match found!")
            result = file_content.replace(old_code, new_code, 1)
            return result, True
        
        def normalize_ws(code):
            lines = []
            for line in code.split('\n'):
                stripped = line.rstrip()
                if stripped:
                    lines.append(stripped)
                else:
                    lines.append('')
            return '\n'.join(lines)
        
        normalized_file = normalize_ws(file_content)
        normalized_old = normalize_ws(old_code)
        normalized_new = normalize_ws(new_code)
        
        if normalized_old in normalized_file:
            print("✓ Strategy 2: Found with normalized whitespace")
            result = normalized_file.replace(normalized_old, normalized_new, 1)
            return result, True
        
        print("→ Trying Strategy 3: JSON normalization...")
        try:
            import json
            
            def normalize_json(code):
                try:
                    parsed = json.loads(code)
                    return json.dumps(parsed, separators=(',', ':'), sort_keys=True)
                except:
                    return code
            
            json_file = normalize_json(file_content)
            json_old = normalize_json(old_code)
            json_new = normalize_json(new_code)
            
            if json_old and json_old in json_file:
                print("✓ Strategy 3: Found with JSON normalization")
                result = json_file.replace(json_old, json_new, 1)
                return result, True
        except Exception as e:
            print(f"→ JSON normalization skipped: {e}")
        
        print("→ Trying Strategy 4: Line-by-line search...")
        old_lines = old_code.split('\n')
        file_lines = file_content.split('\n')
        
        if len(old_lines) > 0 and len(old_lines) <= len(file_lines):
            for i in range(len(file_lines) - len(old_lines) + 1):
                if file_lines[i:i+len(old_lines)] == old_lines:
                    print(f"✓ Strategy 4: Found at line {i}")
                    new_lines = new_code.split('\n')
                    result_lines = file_lines[:i] + new_lines + file_lines[i+len(old_lines):]
                    return '\n'.join(result_lines), True
        
        
        
        if len(old_code) > 50:  
            best_match_len = 0
            best_match_pos = -1
            
            for chunk_size in range(len(old_code), max(50, len(old_code)//2), -10):
                for start in range(0, len(old_code) - chunk_size, 10):
                    chunk = old_code[start:start+chunk_size]
                    if chunk in file_content:
                        print(f"✓ Strategy 5: Found partial match ({chunk_size} chars at offset {start})")
                        pos = file_content.find(chunk)
                        start_search = max(0, pos - len(old_code))
                        end_search = min(len(file_content), pos + len(old_code) * 2)
                        if old_code in file_content[start_search:end_search]:
                            return file_content.replace(old_code, new_code, 1), True
        
        return file_content, False
    
    def update_local_file(self, file_path: str, old_code: str, new_code: str):
        """
        Update local file - Vector DB ka code direct file mein replace karo.
        """
        try:
            full_path = self.get_full_local_path(file_path)
            print(f"Path: {full_path}")
            if not os.path.exists(full_path):
                print("File doesn't exist - creating new file")
                dir_path = os.path.dirname(full_path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_code)
                print("✓ New file created with updated code")
                return True
            
            
            with open(full_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            print(f"Current file: {len(current_content)} bytes") 
            updated_content, success = self.simple_exact_replace(
                current_content, 
                old_code, 
                new_code
            )
            
            if success:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                print(f"✓ File updated: {len(updated_content)} bytes")
                return True
            else:
                print("⚠ File NOT modified")
                return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_vector_database(self, chunk_id: int, new_code: str, old_data: dict):
        """Update vector database with new code."""
        try:
            
            print(f"\n=== Updating Vector Database ===")
            new_vector = self.embedder.embed_query(new_code)
            self.milvus_client.delete(
                collection_name=self.collection_name,
                filter=f"my_id == {chunk_id}"
            )
            
            updated_data = {
                "my_id": chunk_id,
                "my_vector": new_vector,
                "file_path": old_data["file_path"],
                "file_name": old_data["file_name"],
                "language": old_data["language"],
                "chunk_index": old_data["chunk_index"],
                "code_snippet": new_code[:65535]  
            }
            
            self.milvus_client.insert(
                collection_name=self.collection_name,
                data=[updated_data]
            )
            print(f"✓ Inserted updated chunk {chunk_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Database update error: {e}")
            return False
    
    def update_code_chunk(self, chunk_id: int, new_code: str):
        try:
            
            result = self.milvus_client.query(
                collection_name=self.collection_name,
                filter=f"my_id == {chunk_id}",
                output_fields=["file_path", "file_name", "language", 
                              "chunk_index", "code_snippet"]
            )
            
            if not result:
                print(f"✗ Chunk {chunk_id} not found in database")
                return {
                    "success": False,
                    "error": f"Chunk ID {chunk_id} not found",
                    "database_updated": False,
                    "file_updated": False
                }
            
            chunk_data = result[0]
            old_code = chunk_data["code_snippet"]
            file_path = chunk_data["file_path"]
            file_success = self.update_local_file(file_path, old_code, new_code)
            print(f"\n--- Step 2: Updating Vector Database ---")
            db_success = self.update_vector_database(chunk_id, new_code, chunk_data)
            
            return {
                "success": file_success and db_success,
                "database_updated": db_success,
                "file_updated": file_success,
                "chunk_id": chunk_id,
                "file_path": file_path,
                "full_local_path": self.get_full_local_path(file_path),
                "old_code_length": len(old_code),
                "new_code_length": len(new_code),
                "message": "✓ Code updated in both file and database" if (file_success and db_success)
                          else "✗ Update failed - check logs for details"
            }
            
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR ❌")
            import traceback
            error_trace = traceback.format_exc()
            print(error_trace)
            
            return {
                "success": False,
                "error": str(e),
                "traceback": error_trace,
                "database_updated": False,
                "file_updated": False
            }

_service_instance = None

def get_service():
    """Get or create the global service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = VectorDBService()
    return _service_instance

def search_similar_code(query: str, top_k: int = 2):
    """Search for similar code in vector database."""
    service = get_service()
    return service.search_similar_code(query, top_k)

def update_code_chunk(chunk_id: int, new_code: str):
    """
    Update code chunk in both vector DB and local file.
    
    Usage:
        result = update_code_chunk(123, "def new_function():\\n    pass")
        if result['success']:
            print("Updated successfully!")
    """
    service = get_service()
    return service.update_code_chunk(chunk_id, new_code)