from fastapi import UploadFile, File, HTTPException, APIRouter, Depends
from fastapi.responses import JSONResponse
from database import cms_blogs
from models import BlogCreate, BlogInDB
from auth import decode_access_token
import os
import uuid

UPLOAD_DIR = "media"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter()

@router.post("/upload/image", response_model=dict)
async def upload_image(file: UploadFile = File(...), user=Depends(decode_access_token)):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed")

    # Validate file size
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:  # 5 MB limit
        raise HTTPException(status_code=400, detail="File too large")

    # Reset file pointer for writing
    file.file.seek(0)

    # Generate safe unique filename
    filename = f"{user['email']}_{uuid.uuid4().hex}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, filename)

    # Save file in chunks
    with open(path, "wb") as f:
        for chunk in iter(lambda: file.file.read(1024 * 1024), b""):
            f.write(chunk)

    return {"filename": filename, "url": f"/media/{filename}"}
