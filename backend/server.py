from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import requests
import json
from urllib.parse import quote
import jwt
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# API Keys
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', '1baf462ff9a6d4a3461ca615496ecf84')
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '267961051535-vfvp7i0d4hjgqvo365fm7jioca28fqaq.apps.googleusercontent.com')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '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')
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_orU2jCj3SKV5Xb')
RAZORPAY_SECRET = os.environ.get('RAZORPAY_SECRET', 'S8aUX5qSVDgtcf18sVnZiu8u')
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

# JWT Secret
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-here-change-in-production')

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

security = HTTPBearer()

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    is_premium: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    premium_expires_at: Optional[datetime] = None

class UserSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Movie(BaseModel):
    tmdb_id: int
    title: str
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    release_date: Optional[str] = None
    vote_average: Optional[float] = None
    genre_ids: List[int] = []
    adult: bool = False

class TVShow(BaseModel):
    tmdb_id: int
    name: str
    overview: Optional[str] = None
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    first_air_date: Optional[str] = None
    vote_average: Optional[float] = None
    genre_ids: List[int] = []

class WatchHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content_type: str  # movie, tv
    tmdb_id: int
    title: str
    poster_path: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0
    last_watched: datetime = Field(default_factory=datetime.utcnow)
    season: Optional[int] = None
    episode: Optional[int] = None

class Favorite(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content_type: str  # movie, tv
    tmdb_id: int
    title: str
    poster_path: Optional[str] = None
    added_at: datetime = Field(default_factory=datetime.utcnow)

class Comment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    user_name: str
    content_type: str
    tmdb_id: int
    text: str
    parent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    payment_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    payment_status: str = "pending"  # pending, paid, failed
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Authentication helpers
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get("user_id")
        
        user = await db.users.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Check if premium expired
        if user.get('premium_expires_at') and datetime.fromisoformat(user['premium_expires_at'].replace('Z', '+00:00')) < datetime.utcnow():
            await db.users.update_one({"id": user_id}, {"$set": {"is_premium": False, "premium_expires_at": None}})
            user['is_premium'] = False
            
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# TMDB API Integration
@api_router.get("/movies/popular")
async def get_popular_movies():
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
    response = requests.get(url)
    data = response.json()
    
    movies = []
    for item in data.get('results', []):
        movies.append(Movie(
            tmdb_id=item['id'],
            title=item['title'],
            overview=item.get('overview'),
            poster_path=item.get('poster_path'),
            backdrop_path=item.get('backdrop_path'),
            release_date=item.get('release_date'),
            vote_average=item.get('vote_average'),
            genre_ids=item.get('genre_ids', []),
            adult=item.get('adult', False)
        ))
    
    return {"results": movies}

@api_router.get("/tv/popular")
async def get_popular_tv():
    url = f"https://api.themoviedb.org/3/tv/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
    response = requests.get(url)
    data = response.json()
    
    shows = []
    for item in data.get('results', []):
        shows.append(TVShow(
            tmdb_id=item['id'],
            name=item['name'],
            overview=item.get('overview'),
            poster_path=item.get('poster_path'),
            backdrop_path=item.get('backdrop_path'),
            first_air_date=item.get('first_air_date'),
            vote_average=item.get('vote_average'),
            genre_ids=item.get('genre_ids', [])
        ))
    
    return {"results": shows}

@api_router.get("/search")
async def search_content(q: str):
    encoded_query = quote(q)
    url = f"https://api.themoviedb.org/3/search/multi?api_key={TMDB_API_KEY}&language=en-US&query={encoded_query}&page=1"
    response = requests.get(url)
    data = response.json()
    
    results = []
    for item in data.get('results', []):
        if item['media_type'] == 'movie':
            results.append({
                "type": "movie",
                "data": Movie(
                    tmdb_id=item['id'],
                    title=item['title'],
                    overview=item.get('overview'),
                    poster_path=item.get('poster_path'),
                    backdrop_path=item.get('backdrop_path'),
                    release_date=item.get('release_date'),
                    vote_average=item.get('vote_average'),
                    genre_ids=item.get('genre_ids', []),
                    adult=item.get('adult', False)
                )
            })
        elif item['media_type'] == 'tv':
            results.append({
                "type": "tv",
                "data": TVShow(
                    tmdb_id=item['id'],
                    name=item['name'],
                    overview=item.get('overview'),
                    poster_path=item.get('poster_path'),
                    backdrop_path=item.get('backdrop_path'),
                    first_air_date=item.get('first_air_date'),
                    vote_average=item.get('vote_average'),
                    genre_ids=item.get('genre_ids', [])
                )
            })
    
    return {"results": results}

# Google OAuth
@api_router.post("/auth/google")
async def google_auth(request: Dict[str, str]):
    # Verify Google token
    token = request.get('token')
    
    try:
        # Verify the token with Google
        google_response = requests.get(f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}")
        if google_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Invalid Google token")
            
        # Get user info from Google
        user_info_response = requests.get(f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={token}")
        if user_info_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
            
        user_data = user_info_response.json()
        
        # Check if user exists
        existing_user = await db.users.find_one({"email": user_data['email']})
        
        if existing_user:
            user = User(**existing_user)
        else:
            # Create new user
            user = User(
                email=user_data['email'],
                name=user_data['name'],
                picture=user_data.get('picture')
            )
            await db.users.insert_one(user.dict())
        
        # Create JWT token
        jwt_payload = {
            "user_id": user.id,
            "email": user.email,
            "exp": datetime.utcnow() + timedelta(days=7)
        }
        jwt_token = jwt.encode(jwt_payload, JWT_SECRET, algorithm="HS256")
        
        return {
            "token": jwt_token,
            "user": user
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Video streaming endpoints
@api_router.get("/stream/{content_type}/{tmdb_id}")
async def get_stream_url(content_type: str, tmdb_id: int, season: Optional[int] = None, episode: Optional[int] = None):
    if content_type == "movie":
        return {
            "embed_url": f"https://rivestream.org/embed?type=movie&id={tmdb_id}",
            "torrent_url": f"https://rivestream.org/embed/torrent?type=movie&id={tmdb_id}",
            "agg_url": f"https://rivestream.org/embed/agg?type=movie&id={tmdb_id}",
            "download_url": f"https://rivestream.org/download?type=movie&id={tmdb_id}"
        }
    elif content_type == "tv":
        if season is None or episode is None:
            raise HTTPException(status_code=400, detail="Season and episode required for TV shows")
        return {
            "embed_url": f"https://rivestream.org/embed?type=tv&id={tmdb_id}&season={season}&episode={episode}",
            "torrent_url": f"https://rivestream.org/embed/torrent?type=tv&id={tmdb_id}&season={season}&episode={episode}",
            "agg_url": f"https://rivestream.org/embed/agg?type=tv&id={tmdb_id}&season={season}&episode={episode}",
            "download_url": f"https://rivestream.org/download?type=tv&id={tmdb_id}&season={season}&episode={episode}"
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid content type")

# User features
@api_router.post("/watchhistory")
async def add_to_watch_history(
    request: Dict[str, Any],
    user: User = Depends(get_current_user)
):
    watch_item = WatchHistory(
        user_id=user.id,
        content_type=request['content_type'],
        tmdb_id=request['tmdb_id'],
        title=request['title'],
        poster_path=request.get('poster_path'),
        progress=request.get('progress', 0.0),
        season=request.get('season'),
        episode=request.get('episode')
    )
    
    # Update existing or create new
    await db.watch_history.replace_one(
        {"user_id": user.id, "content_type": request['content_type'], "tmdb_id": request['tmdb_id']},
        watch_item.dict(),
        upsert=True
    )
    
    return watch_item

@api_router.get("/watchhistory")
async def get_watch_history(user: User = Depends(get_current_user)):
    history = await db.watch_history.find({"user_id": user.id}).sort("last_watched", -1).to_list(100)
    return [WatchHistory(**item) for item in history]

@api_router.post("/favorites")
async def add_to_favorites(
    request: Dict[str, Any],
    user: User = Depends(get_current_user)
):
    favorite = Favorite(
        user_id=user.id,
        content_type=request['content_type'],
        tmdb_id=request['tmdb_id'],
        title=request['title'],
        poster_path=request.get('poster_path')
    )
    
    # Check if already favorited
    existing = await db.favorites.find_one({
        "user_id": user.id,
        "content_type": request['content_type'],
        "tmdb_id": request['tmdb_id']
    })
    
    if existing:
        return {"message": "Already in favorites"}
    
    await db.favorites.insert_one(favorite.dict())
    return favorite

@api_router.get("/favorites")
async def get_favorites(user: User = Depends(get_current_user)):
    favorites = await db.favorites.find({"user_id": user.id}).sort("added_at", -1).to_list(100)
    return [Favorite(**item) for item in favorites]

@api_router.delete("/favorites/{content_type}/{tmdb_id}")
async def remove_from_favorites(
    content_type: str,
    tmdb_id: int,
    user: User = Depends(get_current_user)
):
    result = await db.favorites.delete_one({
        "user_id": user.id,
        "content_type": content_type,
        "tmdb_id": tmdb_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")
    
    return {"message": "Removed from favorites"}

# Premium payments with Stripe
PACKAGES = {
    "premium_monthly": {"amount": 200.0, "currency": "INR", "duration_days": 30}
}

@api_router.post("/payments/create-checkout")
async def create_payment_checkout(
    request: Dict[str, Any],
    user: User = Depends(get_current_user)
):
    package_id = request.get('package_id', 'premium_monthly')
    origin_url = request.get('origin_url')
    
    if not origin_url:
        raise HTTPException(status_code=400, detail="Origin URL required")
    
    if package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    package = PACKAGES[package_id]
    
    # Initialize Stripe checkout
    host_url = origin_url
    webhook_url = f"{origin_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Create checkout session
    success_url = f"{origin_url}/premium/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/premium/cancel"
    
    checkout_request = CheckoutSessionRequest(
        amount=package['amount'],
        currency=package['currency'],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user.id,
            "package_id": package_id,
            "email": user.email
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    transaction = PaymentTransaction(
        user_id=user.id,
        session_id=session.session_id,
        amount=package['amount'],
        currency=package['currency'],
        payment_status="pending",
        metadata=checkout_request.metadata
    )
    
    await db.payment_transactions.insert_one(transaction.dict())
    
    return {"checkout_url": session.url, "session_id": session.session_id}

@api_router.get("/payments/status/{session_id}")
async def check_payment_status(session_id: str):
    # Get transaction from DB
    transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Check with Stripe
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
    checkout_status = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction status
    if checkout_status.payment_status == "paid" and transaction['payment_status'] != "paid":
        # Update user to premium
        user_id = transaction['user_id']
        premium_expires = datetime.utcnow() + timedelta(days=30)
        
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "is_premium": True,
                    "premium_expires_at": premium_expires
                }
            }
        )
        
        # Update transaction
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "payment_status": "paid",
                    "updated_at": datetime.utcnow()
                }
            }
        )
    
    return {
        "status": checkout_status.status,
        "payment_status": checkout_status.payment_status,
        "amount": checkout_status.amount_total,
        "currency": checkout_status.currency
    }

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url="")
    webhook_response = await stripe_checkout.handle_webhook(body, signature)
    
    if webhook_response.event_type == "checkout.session.completed":
        session_id = webhook_response.session_id
        
        # Update transaction and user
        transaction = await db.payment_transactions.find_one({"session_id": session_id})
        if transaction and transaction['payment_status'] != "paid":
            user_id = transaction['user_id']
            premium_expires = datetime.utcnow() + timedelta(days=30)
            
            await db.users.update_one(
                {"id": user_id},
                {
                    "$set": {
                        "is_premium": True,
                        "premium_expires_at": premium_expires
                    }
                }
            )
            
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "payment_status": "paid",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
    
    return {"status": "success"}

# Comments (Premium only)
@api_router.post("/comments")
async def add_comment(
    request: Dict[str, Any],
    user: User = Depends(get_current_user)
):
    if not user.is_premium:
        raise HTTPException(status_code=403, detail="Premium membership required for comments")
    
    comment = Comment(
        user_id=user.id,
        user_name=user.name,
        content_type=request['content_type'],
        tmdb_id=request['tmdb_id'],
        text=request['text'],
        parent_id=request.get('parent_id')
    )
    
    await db.comments.insert_one(comment.dict())
    return comment

@api_router.get("/comments/{content_type}/{tmdb_id}")
async def get_comments(content_type: str, tmdb_id: int):
    comments = await db.comments.find({
        "content_type": content_type,
        "tmdb_id": tmdb_id
    }).sort("created_at", -1).to_list(1000)
    
    return [Comment(**comment) for comment in comments]

# User profile
@api_router.get("/profile")
async def get_profile(user: User = Depends(get_current_user)):
    return user

# Include the router
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()