import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

from database import create_document, get_documents
from schemas import Credential, CredentialOut

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response

# ----------------------
# Credentials Endpoints
# ----------------------

class CreateResponse(BaseModel):
    id: str

@app.post("/api/credentials", response_model=CreateResponse)
def create_credential(credential: Credential):
    try:
        inserted_id = create_document("credential", credential)
        return {"id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/credentials", response_model=List[CredentialOut])
def list_credentials(q: Optional[str] = Query(None, description="Search text for title or username")):
    try:
        filter_query = {}
        if q:
            # Case-insensitive search on title or username
            filter_query = {
                "$or": [
                    {"title": {"$regex": q, "$options": "i"}},
                    {"username": {"$regex": q, "$options": "i"}},
                ]
            }
        docs = get_documents("credential", filter_query)

        def to_out(doc) -> CredentialOut:
            return CredentialOut(
                id=str(doc.get("_id")),
                title=doc.get("title", ""),
                username=doc.get("username", ""),
                password=doc.get("password", ""),
                url=doc.get("url"),
                note=doc.get("note"),
                created_at=(doc.get("created_at").isoformat() if doc.get("created_at") else None),
                updated_at=(doc.get("updated_at").isoformat() if doc.get("updated_at") else None),
            )
        return [to_out(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
