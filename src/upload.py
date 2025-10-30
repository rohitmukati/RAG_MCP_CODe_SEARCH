import os
import json
import re
import importlib
from dataclasses import dataclass
from tree_sitter import Language, Parser
from langchain_openai import OpenAIEmbeddings
from pymilvus import MilvusClient, DataType
from dotenv import load_dotenv


load_dotenv()



CLUSTER_ENDPOINT = os.getenv("CLUSTER_ENDPOINT")
TOKEN = os.getenv("TOKEN")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "code_embeddings")
ROOT_FOLDER = os.getenv("FOLDER_TO_UPLOAD")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

LANGUAGE_MAPPING = {
    ".js": "tree_sitter_javascript",
    ".html": "tree_sitter_html",
    ".css": "tree_sitter_css",
    ".json": None,
    ".vue": None,  
}


@dataclass
class CodeChunk:
    chunk_id: int
    chunk_index: int
    file_path: str
    file_name: str
    language: str
    code_snippet: str
    extra_context: str = ""



def get_all_files(root_folder, exts=None):
    """Recursively collect all file paths under root_folder."""
    all_files = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for f in filenames:
            if exts is None or os.path.splitext(f)[1] in exts:
                all_files.append(os.path.join(dirpath, f))
    return all_files


def init_parsers(language_mapping):
    """Initialize Tree-sitter parsers for supported languages."""
    parsers = {}
    for ext, module_name in language_mapping.items():
        if module_name is None:  # Skip JSON and Vue
            continue
        lang_module = importlib.import_module(module_name)
        lang = Language(lang_module.language())
        parser = Parser(lang)
        parsers[ext] = parser
    return parsers


def chunk_json_content(json_data, max_items=5):
    
    chunks = []
    if isinstance(json_data, dict):
        keys = list(json_data.keys())
        if len(keys) <= 5:
            chunks.append(json.dumps(json_data, indent=2))
            
        else:
            for i in range(0, len(keys), 5):
                chunk_keys = keys[i:i+5]
                chunk_data = {k: json_data[k] for k in chunk_keys}
                chunks.append(json.dumps(chunk_data, indent=2))
    
    elif isinstance(json_data, list):
        if len(json_data) <= max_items:
            chunks.append(json.dumps(json_data, indent=2))
        else:
            for i in range(0, len(json_data), max_items):
                chunk_data = json_data[i:i+max_items]
                chunks.append(json.dumps(chunk_data, indent=2))
    else:
        chunks.append(json.dumps(json_data, indent=2))
    
    return chunks


def extract_json_chunks(file_path, chunk_counter, chunk_index_start=0):
    """Extract chunks from JSON files."""
    chunks = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        json_chunks = chunk_json_content(json_data)
        
        for i, snippet in enumerate(json_chunks):
            chunks.append(CodeChunk(
                chunk_id=chunk_counter,
                chunk_index=chunk_index_start + i,
                file_path=file_path,
                file_name=os.path.basename(file_path),
                language="json",
                code_snippet=snippet,
                extra_context=f"Folder: {os.path.basename(os.path.dirname(file_path))}"
            ))
            chunk_counter += 1
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in {file_path}: {e}")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return chunks, chunk_counter


def extract_vue_chunks(file_path, chunk_counter, chunk_index_start=0):
    """Extract template, script, and style chunks from Vue files using regex."""
    chunks = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunk_index = chunk_index_start
        template_pattern = r'<template[^>]*>(.*?)</template>'
        template_match = re.search(template_pattern, content, re.DOTALL | re.IGNORECASE)
        if template_match:
            template_content = template_match.group(0)
            if len(template_content.strip()) > 50:
                chunks.append(CodeChunk(
                    chunk_id=chunk_counter,
                    chunk_index=chunk_index,
                    file_path=file_path,
                    file_name=os.path.basename(file_path),
                    language="vue-template",
                    code_snippet=template_content,
                    extra_context=f"Folder: {os.path.basename(os.path.dirname(file_path))}, Section: template"
                ))
                chunk_counter += 1
                chunk_index += 1
        
        
        script_pattern = r'<script[^>]*>(.*?)</script>'
        script_matches = re.finditer(script_pattern, content, re.DOTALL | re.IGNORECASE)
        for script_match in script_matches:
            script_content = script_match.group(0)
            if len(script_content.strip()) > 20:
                chunks.append(CodeChunk(
                    chunk_id=chunk_counter,
                    chunk_index=chunk_index,
                    file_path=file_path,
                    file_name=os.path.basename(file_path),
                    language="vue-script",
                    code_snippet=script_content,
                    extra_context=f"Folder: {os.path.basename(os.path.dirname(file_path))}, Section: script"
                ))
                chunk_counter += 1
                chunk_index += 1
        
        
        style_pattern = r'<style[^>]*>(.*?)</style>'
        style_matches = re.finditer(style_pattern, content, re.DOTALL | re.IGNORECASE)
        for style_match in style_matches:
            style_content = style_match.group(0)
            if len(style_content.strip()) > 20:
                chunks.append(CodeChunk(
                    chunk_id=chunk_counter,
                    chunk_index=chunk_index,
                    file_path=file_path,
                    file_name=os.path.basename(file_path),
                    language="vue-style",
                    code_snippet=style_content,
                    extra_context=f"Folder: {os.path.basename(os.path.dirname(file_path))}, Section: style"
                ))
                chunk_counter += 1
                chunk_index += 1
        
    except Exception as e:
        print(f"Error reading Vue file {file_path}: {e}")
    
    return chunks, chunk_counter


def extract_chunks(file_paths, parsers):
    """Parse files and extract code chunks with metadata."""
    chunks = []
    chunk_counter = 0

    for file_path in file_paths:
        ext = os.path.splitext(file_path)[1]
        
        
        if ext == ".json":
            json_chunks, chunk_counter = extract_json_chunks(file_path, chunk_counter)
            chunks.extend(json_chunks)
            continue
        
        
        if ext == ".vue":
            vue_chunks, chunk_counter = extract_vue_chunks(file_path, chunk_counter)
            chunks.extend(vue_chunks)
            continue
        
        parser = parsers.get(ext)
        if not parser:
            continue

        try:
            with open(file_path, "rb") as f:
                code_bytes = f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

        tree = parser.parse(code_bytes)
        root_node = tree.root_node
        chunk_index = 0

        if ext == ".js":
            for child in root_node.children:
                if child.type in ("function_declaration", "lexical_declaration", "class_declaration", 
                                "expression_statement", "export_statement"):
                    snippet = code_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore")
                    chunks.append(CodeChunk(
                        chunk_id=chunk_counter,
                        chunk_index=chunk_index,
                        file_path=file_path,
                        file_name=os.path.basename(file_path),
                        language="javascript",
                        code_snippet=snippet,
                        extra_context=f"Folder: {os.path.basename(os.path.dirname(file_path))}"
                    ))
                    chunk_counter += 1
                    chunk_index += 1

        elif ext == ".html":
            for child in root_node.children:
                if child.type == "script_element":
                    snippet = code_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore")
                    chunks.append(CodeChunk(
                        chunk_id=chunk_counter,
                        chunk_index=chunk_index,
                        file_path=file_path,
                        file_name=os.path.basename(file_path),
                        language="javascript",
                        code_snippet=snippet,
                        extra_context=f"Folder: {os.path.basename(os.path.dirname(file_path))}"
                    ))
                    chunk_counter += 1
                    chunk_index += 1
                elif child.type == "style_element":
                    snippet = code_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore")
                    chunks.append(CodeChunk(
                        chunk_id=chunk_counter,
                        chunk_index=chunk_index,
                        file_path=file_path,
                        file_name=os.path.basename(file_path),
                        language="css",
                        code_snippet=snippet,
                        extra_context=f"Folder: {os.path.basename(os.path.dirname(file_path))}"
                    ))
                    chunk_counter += 1
                    chunk_index += 1
                elif child.type == "element":
                    snippet = code_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore")
                    if len(snippet.strip()) > 50:  
                        chunks.append(CodeChunk(
                            chunk_id=chunk_counter,
                            chunk_index=chunk_index,
                            file_path=file_path,
                            file_name=os.path.basename(file_path),
                            language="html",
                            code_snippet=snippet,
                            extra_context=f"Folder: {os.path.basename(os.path.dirname(file_path))}"
                        ))
                        chunk_counter += 1
                        chunk_index += 1

        elif ext == ".css":
            for child in root_node.children:
                if child.type == "rule_set":
                    snippet = code_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore")
                    chunks.append(CodeChunk(
                        chunk_id=chunk_counter,
                        chunk_index=chunk_index,
                        file_path=file_path,
                        file_name=os.path.basename(file_path),
                        language="css",
                        code_snippet=snippet,
                        extra_context=f"Folder: {os.path.basename(os.path.dirname(file_path))}"
                    ))
                    chunk_counter += 1
                    chunk_index += 1

    print(f"Total code chunks extracted: {len(chunks)}")
    return chunks


def truncate_text(text, max_chars=30000):
    """Truncate text to a maximum number of characters to prevent token limit errors."""
    if len(text) > max_chars:
        return text[:max_chars] + "\n... [truncated]"
    return text


def generate_embeddings(chunks, batch_size=50):
    """Generate embeddings for code chunks using OpenAI with batching and smart chunking."""
    embedder = OpenAIEmbeddings(model="text-embedding-3-large", openai_api_key=OPENAI_API_KEY)
    vectors = []
    
    print(f"Generating embeddings for {len(chunks)} chunks...")
    
    
    for i, chunk in enumerate(chunks):
        try:
            
            truncated_snippet = truncate_text(chunk.code_snippet, max_chars=30000)
            vector = embedder.embed_query(truncated_snippet)
            vectors.append(vector)
            
            if (i + 1) % 50 == 0 or (i + 1) == len(chunks):
                print(f"Processed {i + 1}/{len(chunks)} chunks")
        except Exception as e:
            print(f"Error embedding chunk {i} from {chunk.file_name}: {e}")
            vectors.append([0.0] * 3072)  
    
    return vectors


def upload_to_zilliz(chunks, vectors):
    """Create Milvus collection if not exists and upload code vectors."""
    client = MilvusClient(uri=CLUSTER_ENDPOINT, token=TOKEN)


    if client.has_collection(collection_name=COLLECTION_NAME):
        client.drop_collection(collection_name=COLLECTION_NAME)
        print(f"Dropped existing collection: {COLLECTION_NAME}")


    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field(field_name="my_id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="my_vector", datatype=DataType.FLOAT_VECTOR, dim=len(vectors[0]))
    schema.add_field(field_name="file_path", datatype=DataType.VARCHAR, max_length=512)
    schema.add_field(field_name="file_name", datatype=DataType.VARCHAR, max_length=256)
    schema.add_field(field_name="language", datatype=DataType.VARCHAR, max_length=50)
    schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
    schema.add_field(field_name="code_snippet", datatype=DataType.VARCHAR, max_length=65535)

    index_params = client.prepare_index_params()
    index_params.add_index(field_name="my_id")
    index_params.add_index(field_name="my_vector", index_type="AUTOINDEX", metric_type="IP")

    client.create_collection(collection_name=COLLECTION_NAME, schema=schema, index_params=index_params)
    print(f"Created collection: {COLLECTION_NAME}")


    data = [
        {
            "my_id": c.chunk_id,
            "my_vector": vectors[i],
            "file_path": c.file_path,
            "file_name": c.file_name,
            "language": c.language,
            "chunk_index": c.chunk_index,
            "code_snippet": c.code_snippet[:65535] 
        }
        for i, c in enumerate(chunks)
    ]

    
    client.insert(collection_name=COLLECTION_NAME, data=data)
    print("All chunks uploaded successfully to Zilliz/Milvus!")



def main():
    if not os.path.exists(ROOT_FOLDER):
        print(f"Error: ROOT_FOLDER '{ROOT_FOLDER}' does not exist!")
        return

    files = get_all_files(ROOT_FOLDER, exts=list(LANGUAGE_MAPPING.keys()))
    print(f"Found {len(files)} files to process")
    
    if not files:
        print("No files found to process!")
        return


    file_counts = {}
    for file in files:
        ext = os.path.splitext(file)[1]
        file_counts[ext] = file_counts.get(ext, 0) + 1
    
    print("Files by type:")
    for ext, count in file_counts.items():
        print(f"  {ext}: {count} files")

    parsers = init_parsers(LANGUAGE_MAPPING)
    chunks = extract_chunks(files, parsers)
    
    if not chunks:
        print("No chunks extracted!")
        return

    
    chunk_counts = {}
    for chunk in chunks:
        chunk_counts[chunk.language] = chunk_counts.get(chunk.language, 0) + 1
    
    print("\nChunks by language:")
    for lang, count in chunk_counts.items():
        print(f"  {lang}: {count} chunks")

    vectors = generate_embeddings(chunks)
    upload_to_zilliz(chunks, vectors)


if __name__ == "__main__":
    main()