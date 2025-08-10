#------------------------
# Summary of Features
#POST /blogs → Create new blog (authenticated)

#GET /blogs → List all blogs (public)

#GET /blogs/{id} → View single blog (public)

#PUT /blogs/{id} → Update blog (author only)

#DELETE /blogs/{id} → Delete blog (author only)
#------------------------           


# 📦 backend/routes/blogs.py
from fastapi import APIRouter, HTTPException, Depends
from models import BlogCreate, BlogInDB
from database import cms_blogs
from bson import ObjectId
from datetime import datetime, timezone
from auth import decode_access_token

router = APIRouter()

# ---------------------------
# CREATE BLOG
# ---------------------------
@router.post("/blogs", response_model=BlogInDB)
def create_blog(blog: BlogCreate, token: str=Depends(decode_access_token)):
    blog_dict = blog.dict()
    
    blog_dict.update({
        "author": user["email"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "media_files": []
    })
    result = cms_blogs.insert_one(blog_dict)
    blog_dict["id"] = str(result.inserted_id)
    return BlogInDB(**blog_dict)

# ---------------------------
# LIST BLOGS
# ---------------------------
@router.get("/blogs", response_model=list[BlogInDB])
def list_blogs():
    return [
        BlogInDB(
            id=str(blog["_id"]),
            title=blog["title"],
            tags=blog.get("tags", []),
            created_at=blog["created_at"],
            updated_at=blog.get("updated_at"),
            author=blog.get("author"),
            media_files=blog.get("media_files", [])
        )
        for blog in cms_blogs.find().sort("created_at", -1)
    ]

# ---------------------------
# GET SINGLE BLOG
# ---------------------------
@router.get("/blogs/{blog_id}", response_model=BlogInDB)
def get_blog(blog_id: str):
    blog = cms_blogs.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    blog["id"] = str(blog["_id"])
    return BlogInDB(**blog)

# ---------------------------
# UPDATE BLOG
# ---------------------------
@router.put("/blogs/{blog_id}", response_model=BlogInDB)
def update_blog(blog_id: str, blog_update: BlogCreate, user=Depends(decode_access_token)):
    blog = cms_blogs.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    if blog.get("author") != user["email"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this blog")
    
    update_data = blog_update.dict()
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    cms_blogs.update_one(
        {"_id": ObjectId(blog_id)},
        {"$set": update_data}
    )
    
    updated_blog = cms_blogs.find_one({"_id": ObjectId(blog_id)})
    updated_blog["id"] = str(updated_blog["_id"])
    return BlogInDB(**updated_blog)

# ---------------------------
# DELETE BLOG
# ---------------------------
@router.delete("/blogs/{blog_id}")
def delete_blog(blog_id: str, user=Depends(decode_access_token)):
    blog = cms_blogs.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    if blog.get("author") != user["email"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this blog")
    
    cms_blogs.delete_one({"_id": ObjectId(blog_id)})
    return {"message": "Blog deleted successfully"}
