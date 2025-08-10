from fastapi import FastAPI, HTTPException, Depends
from database import user_collection, user_collection_profile, user_collection_audit
from models import UserCreate, UserLogin, TokenResponse, TokenData, UserProfile, AuditLog
from utils import hash_password, verify_password
from auth import create_access_token, decode_access_token
from bson.objectid import ObjectId
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from fastapi.middleware.cors import CORSMiddleware
from fastapi import File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from cryptography.fernet import Fernet
from datetime import datetime
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes import blogs, upload
# You can store this key in environment variable or a secure config
SECRET_KEY = b'u4sSBdkWjMxsx58gQqxoQGgMYVbRhrFuM1L0d64xov0='
''  # use Fernet.generate_key() once
fernet = Fernet(SECRET_KEY)

def encrypt_name(name: str) -> str:
      return fernet.encrypt(name.encode()).decode()

def decrypt_name(encrypted_name: str) -> str:
    return fernet.decrypt(encrypted_name.encode()).decode()

app = FastAPI()
app.include_router(blogs.router, prefix="/api", tags=["blogs"])
app.include_router(upload.router, prefix="/api", tags=["upload"])
app.mount("/media", StaticFiles(directory="media"), name="media")
app.mount("/profile_photos", StaticFiles(directory="profile_photos"), name="profile_photos")
# CORS Middleware
app.add_middleware(CORSMiddleware,
                   allow_origins=["http://localhost:3000"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])


# Signup Route
@app.post("/signup", response_model=dict)
def signup(user: UserCreate):

    if user_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    #encrypted_name = encrypt_name(user.name)
    hashed_pwd = hash_password(user.password)
    #user.name = encrypted_name  # Store encrypted name

    user_data = {"email": user.email, "password": hashed_pwd, "name": user.name,
                 "username": user.username, "gender":user.gender, "DateOfBirth": user.DateOfBirth}
    user_collection.insert_one(user_data)
    user_collection_audit.insert_one({
        "action": "User Created",
        "user_id": str(user_collection.find_one({"email": user.email})["_id"]),
        "timestamp": datetime.utcnow().isoformat(),
        "details": f"User {user.email} created successfully"    
    })
    return { "message": "User created successfully"}


@app.post("/login", response_model=TokenResponse)
def login(user: UserLogin):
    db_user = user_collection.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        # Log the failed login attempt
        user_collection_audit.insert_one({
            "action": "Failed Login Attempt",
            "user_id": str(db_user["_id"]) if db_user else "Unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "details": f"Failed login attempt for user {user.email}"
        })
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": str(db_user["_id"])})
    user_collection_audit.insert_one({
        "action": "User Logged In",
        "user_id": str(db_user["_id"]),
        "timestamp": datetime.utcnow().isoformat(),
        "details": f"User {db_user['email']} logged in successfully"
    })
    return TokenResponse(access_token=token)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")



# Get profile Route
@app.get("/profile")
def read_profile(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=403, detail="Invalid token")

    db_user = user_collection.find_one({"_id": ObjectId(user_id)})
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_profile = user_collection_profile.find_one({"email": db_user["email"]})

    profile_picture = None  # Set default
    if db_profile and "profile_picture" in db_profile:
        profile_picture = db_profile["profile_picture"]

    return {
        "name": db_user.get("name"),
        "email": db_user.get("email"),
        "gender": db_user.get("gender"),
        "DateOfBirth": db_user.get("DateOfBirth"),
        "contact_number": db_profile.get("contact_number") if db_profile else "",
        "address": db_profile.get("Address") if db_profile else "",
        "facebook": db_profile.get("facebook") if db_profile else "",
        "instagram": db_profile.get("Instagram") if db_profile else "",
        "profile_picture": profile_picture,
        "username": db_user.get("username")
    }

    


#profile update
@app.put("/profile", response_model=dict)
def update_profile(user: UserProfile, token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        db_user = user_collection.find_one({"_id": ObjectId(user_id)})
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        email = db_user["email"]

        # Ensure profile exists
        db_profile = user_collection_profile.find_one({"email": email})
        if not db_profile:
            user_collection_profile.insert_one({
                "email": email,
                "contact_number": user.contact_number,
                "Address": user.Address,
                "facebook": user.Facebook,
                "Instagram": user.Instagram,
                "profile_picture": None  # Default to None
            })

        else:
            # Update existing profile
            user_collection_profile.update_one(
                {"email": email},
                {"$set": {
                    "contact_number": user.contact_number,
                    "Address": user.Address,
                    "facebook": user.Facebook,
                    "Instagram": user.Instagram
                }}
            )
                

        # Update main user collection
        user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "email": user.email,
                "gender": user.gender,
                "DateOfBirth": user.DateOfBirth
            }}
        )
        user_collection_audit.insert_one({
            "action": "Profile Updated",
            "user_id": str(user_id),
            "timestamp": datetime.utcnow().isoformat(),
            "details": f"User {email} updated their profile successfully"
        })
        # Return success message

        return {"message": "Profile updated successfully"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


#profile photo upload option
from fastapi import UploadFile, File, HTTPException, Depends
from bson import ObjectId
import os

@app.post("/upload_profile_picture", response_model=dict)
def upload_profile_picture(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=403, detail="Invalid token")

        db_user = user_collection.find_one({"_id": ObjectId(user_id)})
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        email = db_user["email"]
        filename = f"profile_{user_id}.jpg"
        file_path = f"profile_photos/{filename}"

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(file.file.read())

        # Ensure profile record exists
        user_collection_profile.update_one(
            {"email": email},
            {"$setOnInsert": {"email": email}},  # insert if not exists
            upsert=True
        )

        # Update profile picture
        user_collection_profile.update_one(
            {"email": email},
            {"$set": {"profile_picture": filename}}
        )
        user_collection_audit.insert_one({
            "action": "Profile Picture Uploaded",
            "user_id": str(user_id),
            "timestamp": datetime.utcnow().isoformat(),
            "details": f"User {email} uploaded a new profile picture"
        })
        return {"message": "Profile picture uploaded", "filename": filename}

    except Exception as e:
        print(f"Upload error: {e}")  # Optional: Logging
        raise HTTPException(status_code=500, detail="Internal server error")


#fetch contact details
@app.get("/fetch_contact")
def fetch_contact(token: str = Depends(oauth2_scheme)):
    try: 
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        db_user = user_collection.find_one({"_id": ObjectId(user_id)})
        db_profile = user_collection_profile.find_one({"email": db_user["email"]})
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        if not db_profile:
            raise HTTPException(status_code=404, detail="Profile details not found") 
            # Assuming db_user contains the user's email, name, and username

        return {
            "email": db_user.get("email"),
            "contact_number": db_profile.get("contact_number"),
            "address": db_profile.get("Address")
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    

# Logout Route
@app.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=403, detail="Invalid token")
        close(token)
        # Log the logout action
        user_collection_audit.insert_one({
            "action": "User Logged Out",
            "user_id": str(user_id),
            "timestamp": datetime.utcnow().isoformat(),
            "details": f"User {user_collection.find_one({'_id': ObjectId(user_id)})['email']} logged out successfully"
        })
        return {"message": "Logged out successfully"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
