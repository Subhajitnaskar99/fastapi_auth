from pymongo import MongoClient

from pymongo import MongoClient, ASCENDING

# MongoDB configuration
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "fastapi_auth"

# Collections
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Access collections
user_collection = db["users"]
user_collection_profile = db["profile_details"]
user_collection_audit = db["AuditTrail"]
cms_blogs = db["cms_blogs"]

# Ensure indexes
user_collection.create_index("email", unique=True)
user_collection_profile.create_index("email", unique=True)
user_collection_audit.create_index("user_id")
cms_blogs.create_index([("title", ASCENDING)])
cms_blogs.create_index([("tags", ASCENDING)])
# Dependency functions
def get_db():
    return db

def get_profile_db():
    return db
def get_audit_db():
    return db
def get_cms_db():
    return db