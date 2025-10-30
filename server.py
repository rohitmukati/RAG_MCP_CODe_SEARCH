from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from src.files import search_similar_code, update_code_chunk
from src import upload
import os
import sys
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown"""
    print("🚀 Vector DB Code Service starting...")
    yield
    print("🛑 Vector DB Code Service shutting down...")



app = FastAPI(
    title="Vector DB Code Service API",
    description="MCP-optimized API for semantic code search and updates",
    version="1.0.0",
    lifespan=lifespan
)



class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query for code snippets", min_length=1, max_length=500)
    top_k: int = Field(default=2, description="Number of results to return", ge=1, le=10)
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty or whitespace only')
        return v.strip()


class CodeResult(BaseModel):
    chunk_id: int
    file_path: str
    file_name: str
    language: str
    chunk_index: int
    code_snippet: str
    similarity_score: float


class SearchResponse(BaseModel):
    success: bool = Field(description="Whether search was successful")
    results: List[CodeResult] = Field(description="List of matching code snippets")
    count: int = Field(description="Number of results returned")
    query: str = Field(description="Original search query")


class UpdateRequest(BaseModel):
    chunk_id: int = Field(..., description="Chunk ID to update", ge=0)
    new_code: str = Field(..., description="New code content", min_length=1, max_length=10000)
    
    @field_validator('new_code')
    @classmethod
    def validate_code(cls, v):
        if not v.strip():
            raise ValueError('Code cannot be empty or whitespace only')
        return v.strip()


class UpdateResponse(BaseModel):
    success: bool = Field(description="Whether update was successful")
    database_updated: bool = Field(description="Whether database was updated")
    file_updated: bool = Field(description="Whether file was updated")
    chunk_id: Optional[int] = Field(default=None, description="Updated chunk ID")
    file_path: Optional[str] = Field(default=None, description="File path relative to project")
    full_local_path: Optional[str] = Field(default=None, description="Absolute file path")
    old_code_length: Optional[int] = Field(default=None, description="Length of old code")
    new_code_length: Optional[int] = Field(default=None, description="Length of new code")
    message: str = Field(description="Status message")
    error: Optional[str] = Field(default=None, description="Error details if any")



class HealthResponse(BaseModel):
    status: str = Field(description="Service status")
    service: str = Field(description="Service name")
    version: str = Field(description="API version")


@app.get("/", response_model=dict, tags=["Info"])
async def root():
    """Root endpoint - API health check and available endpoints"""
    return {
        "service": "Vector DB Code Service",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "search": "/api/search",
            "update": "/api/update",
            "health": "/health",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }


@app.post(
    "/api/search",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    tags=["Search"],
    summary="Search similar code snippets",
    responses={
        200: {"description": "Search successful"},
        400: {"description": "Invalid request"},
        500: {"description": "Server error"}
    }
)
async def search_code(request: SearchRequest):
    """
    Perform semantic search for similar code snippets using vector embeddings.
    
    The search uses semantic similarity to find relevant code chunks, not just keyword matching.
    
    **Example Request:**
    ```json
    {
        "query": "function to connect to database",
        "top_k": 2
    }
    ```
    
    **Example Response:**
    ```json
    {
        "success": true,
        "results": [
            {
                "chunk_id": 123,
                "file_path": "src/db/connection.py",
                "file_name": "connection.py",
                "language": "python",
                "chunk_index": 0,
                "code_snippet": "def connect_to_db()...",
                "similarity_score": 0.85
            }
        ],
        "count": 1,
        "query": "function to connect to database"
    }
    ```
    """
    try:
        results = search_similar_code(query=request.query, top_k=request.top_k)
        
        if not results:
            return SearchResponse(
                success=True,
                results=[],
                count=0,
                query=request.query
            )
        
        
        parsed_results = [CodeResult(**r) if isinstance(r, dict) else r for r in results]
        
        return SearchResponse(
            success=True,
            results=parsed_results,
            count=len(parsed_results),
            query=request.query
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid search query: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@app.post(
    "/api/update",
    response_model=UpdateResponse,
    status_code=status.HTTP_200_OK,
    tags=["Update"],
    summary="Update code chunk",
    responses={
        200: {"description": "Update processed"},
        400: {"description": "Invalid request"},
        500: {"description": "Server error"}
    }
)
async def update_code(request: UpdateRequest):
    """
    Update code chunk in both vector database and local file.
    
    This endpoint modifies a specific code chunk identified by chunk_id,
    updating both the local file and the vector database embeddings.
    
    **Example Request:**
    ```json
    {
        "chunk_id": 123,
        "new_code": "def improved_function():\\n    # Better implementation\\n    pass"
    }
    ```
    
    **Example Response:**
    ```json
    {
        "success": true,
        "database_updated": true,
        "file_updated": true,
        "chunk_id": 123,
        "file_path": "src/utils.py",
        "full_local_path": "/home/user/project/src/utils.py",
        "old_code_length": 150,
        "new_code_length": 180,
        "message": "✓ Code updated in both file and database"
    }
    ```
    """
    try:
        result = update_code_chunk(chunk_id=request.chunk_id, new_code=request.new_code)
        
        if not result.get("success", False):
            return UpdateResponse(
                success=False,
                database_updated=result.get("database_updated", False),
                file_updated=result.get("file_updated", False),
                chunk_id=request.chunk_id,
                message=result.get("message", "Update failed"),
                error=result.get("error", "Unknown error occurred")
            )
        
        return UpdateResponse(
            success=True,
            database_updated=result.get("database_updated", False),
            file_updated=result.get("file_updated", False),
            chunk_id=result.get("chunk_id"),
            file_path=result.get("file_path"),
            full_local_path=result.get("full_local_path"),
            old_code_length=result.get("old_code_length"),
            new_code_length=result.get("new_code_length"),
            message=result.get("message", "Success")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid update request: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Update failed: {str(e)}"
        )


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint"
)
async def health_check():
    """Check if the service is running and healthy"""
    return HealthResponse(
        status="healthy",
        service="vector-db-code-service",
        version="1.0.0"
    )



@app.post(
    "/api/upload-all",
    tags=["Upload"],
    summary="Run full upload pipeline",
    responses={
        200: {"description": "Upload pipeline completed successfully"},
        500: {"description": "Server error during upload process"}
    }
)
async def upload_all():
    try:
        from src.upload import main

        print("⚙️ Starting full upload pipeline...")
        main()
        print("✅ Upload pipeline completed successfully")

        return {
            "success": True,
            "message": "✅ Full upload pipeline completed successfully"
        }

    except Exception as e:
        print(f"❌ Upload pipeline failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload pipeline failed: {str(e)}"
        )



@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "path": str(request.url),
            "available_endpoints": ["/api/search", "/api/update", "/api/upload-all", "/health", "/docs"]
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )



if __name__ == "__main__":
    use_mcp = "--mcp" in sys.argv
    
    if use_mcp:
        try:
            from fastmcp import FastMCP
            mcp = FastMCP.from_fastapi(
                app=app,
                name="Vector DB Code Service MCP"
            )
            
            print("=" * 70)
            print("🚀 Starting MCP Server: Vector DB Code Service")
            print("=" * 70)
            print("📡 MCP Server running in stdio mode")
            print("📚 Available tools:")
            print("  • search_code - Search for similar code snippets")
            print("  • update_code - Update code chunks")
            print("  • health_check - Service health status")
            print("=" * 70)
            print()
            
            mcp.run()
            
        except ImportError:
            print("FastMCP not available. Falling back to HTTP mode...")
            use_mcp = False
    
    if not use_mcp:
        import uvicorn
        print("=" * 70)
        print("🚀 Starting FastAPI Server (HTTP Mode)")
        print("=" * 70)
        print("📝 API Documentation: http://localhost:8000/docs")
        print("📊 ReDoc: http://localhost:8000/redoc")
        print("💚 Health Check: http://localhost:8000/health")
        print("🔍 Search Endpoint: POST http://localhost:8000/api/search")
        print("✏️  Update Endpoint: POST http://localhost:8000/api/update")
        print("🔄 Reindex Endpoint: POST http://localhost:8000/api/upload-all")
        print("=" * 70)
        print()
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )