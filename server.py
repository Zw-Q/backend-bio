from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class BioProfileCreate(BaseModel):
    name: str
    description: str
    profile_image: str

class BioProfile(BaseModel):
    id: str
    name: str
    description: str
    profile_image: str
    created_at: datetime
    updated_at: datetime

class SocialLinkCreate(BaseModel):
    title: str
    url: str
    icon_type: str
    order: int

class SocialLinkUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    icon_type: Optional[str] = None
    order: Optional[int] = None

class SocialLink(BaseModel):
    id: str
    title: str
    url: str
    icon_type: str
    order: int
    created_at: datetime


# Helper function to convert ObjectId to string
def convert_object_id(doc):
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


# Initialize default data
async def init_default_data():
    # Check if profile exists
    profile_count = await db.bio_profiles.count_documents({})
    if profile_count == 0:
        # Create default profile
        default_profile = {
            "name": "ZwQ",
            "description": "Bio",
            "profile_image": "https://i.pinimg.com/736x/1b/a1/3f/1ba13f9e183fb869f3999b954b25d949.jpg",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = await db.bio_profiles.insert_one(default_profile)
        profile_id = result.inserted_id
        
        # Create default links
        default_links = [
            {
                "profile_id": profile_id,
                "title": "Facebook",
                "url": "https://facebook.com",
                "icon_type": "facebook",
                "order": 1,
                "created_at": datetime.utcnow()
            },
            {
                "profile_id": profile_id,
                "title": "Discord",
                "url": "https://discord.com",
                "icon_type": "discord",
                "order": 2,
                "created_at": datetime.utcnow()
            },
            {
                "profile_id": profile_id,
                "title": "Steam",
                "url": "https://steamcommunity.com",
                "icon_type": "steam",
                "order": 3,
                "created_at": datetime.utcnow()
            },
            {
                "profile_id": profile_id,
                "title": "GitHub",
                "url": "https://github.com",
                "icon_type": "github",
                "order": 4,
                "created_at": datetime.utcnow()
            },
            {
                "profile_id": profile_id,
                "title": "YouTube",
                "url": "https://youtube.com",
                "icon_type": "youtube",
                "order": 5,
                "created_at": datetime.utcnow()
            }
        ]
        await db.social_links.insert_many(default_links)
        logger.info("Default data initialized")


# Routes
@api_router.get("/")
async def root():
    return {"message": "ZwQ Bio API"}


@api_router.get("/profile", response_model=BioProfile)
async def get_profile():
    profile = await db.bio_profiles.find_one()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return convert_object_id(profile)


@api_router.put("/profile", response_model=BioProfile)
async def update_profile(profile_data: BioProfileCreate):
    profile = await db.bio_profiles.find_one()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_data = profile_data.dict()
    update_data["updated_at"] = datetime.utcnow()
    
    await db.bio_profiles.update_one(
        {"_id": profile["_id"]},
        {"$set": update_data}
    )
    
    updated_profile = await db.bio_profiles.find_one({"_id": profile["_id"]})
    return convert_object_id(updated_profile)


@api_router.get("/links", response_model=List[SocialLink])
async def get_links():
    links = await db.social_links.find().sort("order", 1).to_list(100)
    return [convert_object_id(link) for link in links]


@api_router.post("/links", response_model=SocialLink)
async def create_link(link_data: SocialLinkCreate):
    profile = await db.bio_profiles.find_one()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    new_link = link_data.dict()
    new_link["profile_id"] = profile["_id"]
    new_link["created_at"] = datetime.utcnow()
    
    result = await db.social_links.insert_one(new_link)
    created_link = await db.social_links.find_one({"_id": result.inserted_id})
    return convert_object_id(created_link)


@api_router.put("/links/{link_id}", response_model=SocialLink)
async def update_link(link_id: str, link_data: SocialLinkUpdate):
    try:
        obj_id = ObjectId(link_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid link ID")
    
    link = await db.social_links.find_one({"_id": obj_id})
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    update_data = {k: v for k, v in link_data.dict().items() if v is not None}
    
    if update_data:
        await db.social_links.update_one(
            {"_id": obj_id},
            {"$set": update_data}
        )
    
    updated_link = await db.social_links.find_one({"_id": obj_id})
    return convert_object_id(updated_link)


@api_router.delete("/links/{link_id}")
async def delete_link(link_id: str):
    try:
        obj_id = ObjectId(link_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid link ID")
    
    result = await db.social_links.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    
    return {"message": "Link deleted successfully"}


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    await init_default_data()


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()