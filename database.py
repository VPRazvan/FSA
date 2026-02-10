import os
import bcrypt
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Lazy database connection - don't connect until needed
_engine = None
_SessionLocal = None
Base = declarative_base()

def get_engine():
    """Lazy initialization of database engine - reads DATABASE_URL at call time"""
    global _engine
    if _engine is None:
        # Read DATABASE_URL at call time, not import time, to handle late secret injection
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is not set")
        _engine = create_engine(
            database_url, 
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            connect_args={"connect_timeout": 10}
        )
    return _engine

def get_session_local():
    """Lazy initialization of SessionLocal"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String)
    location = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    insurance_provider = Column(String)
    insurance_number = Column(String)
    insurance_expiry = Column(String)
    fac_certificate = Column(String)
    fac_expiry = Column(String)
    shotgun_certificate = Column(String)
    shotgun_expiry = Column(String)
    vehicles = Column(JSON)
    gear = Column(Text)
    certifications = Column(JSON)
    membership_number = Column(String)
    membership_expiry = Column(String)
    is_compliant = Column(Boolean, default=True)  # User compliance - inactive if False
    
    bookings = relationship("Booking", back_populates="hunter", foreign_keys="Booking.hunter_id")
    fields = relationship("Field", back_populates="outfitter")
    hunt_sessions = relationship("HuntSession", back_populates="hunter")

class Field(Base):
    __tablename__ = "fields"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    outfitter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    location = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    type = Column(String, nullable=False)
    price_per_day = Column(Float, nullable=False)
    currency = Column(String, default="GBP")
    capacity = Column(Integer, nullable=False)
    description = Column(Text)
    amenities = Column(JSON)
    season = Column(String)
    image = Column(String)
    image_gallery = Column(JSON)  # Array of image URLs for carousel display
    blocked_dates = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    field_type = Column(String, default="subsidised")  # Options: 'diy-leased', 'subsidised', 'international'
    subsidy_percentage = Column(Float)
    guide_name = Column(String)
    guide_contact = Column(String)
    species_allowed = Column(JSON)
    rules_info = Column(Text)
    quarry_type = Column(String)
    quarry_total = Column(Integer)
    quarry_remaining = Column(Integer)
    quarry_species = Column(JSON)
    auto_approve_bookings = Column(Boolean, default=False)
    last_visit_date = Column(String)
    last_visit_had_harvest = Column(Boolean)
    special_mentions = Column(Text)
    ground_rules = Column(Text)
    directions = Column(Text)
    contact_name = Column(String)
    contact_phone = Column(String)
    contact_email = Column(String)
    
    # New fields for pricing structure
    outing_fee = Column(Float)  # Fee charged upfront for subsidised/international bookings
    price_list = Column(JSON)  # Array of {item: string, cost: float} for additional costs
    full_price = Column(Float)  # Original price (for showing discounts to UK members)
    
    # Wildlife survey report uploaded by admin
    wildlife_survey_report = Column(Text)  # Rich text/markdown content for wildlife survey data
    
    outfitter = relationship("User", back_populates="fields")
    bookings = relationship("Booking", back_populates="field")
    hunt_sessions = relationship("HuntSession", back_populates="field")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    hunter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String, nullable=False)
    num_hunters = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String, default="pending")
    payment_method = Column(String)
    payment_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    field = relationship("Field", back_populates="bookings")
    hunter = relationship("User", back_populates="bookings", foreign_keys=[hunter_id])

class PaymentToken(Base):
    __tablename__ = "payment_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String, unique=True, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="GBP")
    status = Column(String, default="succeeded")
    card_last4 = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class HuntSession(Base):
    __tablename__ = "hunt_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    hunter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    status = Column(String, default="not_started")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    booking = relationship("Booking")
    hunter = relationship("User", back_populates="hunt_sessions")
    field = relationship("Field", back_populates="hunt_sessions")
    hunt_report = relationship("HuntReport", back_populates="session", uselist=False)

class HuntReport(Base):
    __tablename__ = "hunt_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("hunt_sessions.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    hunter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    animals_harvested = Column(Integer, default=0)
    species_harvested = Column(JSON)
    animals_detail = Column(JSON)
    weather_conditions = Column(String)
    time_spent_hours = Column(Float)
    notes = Column(Text)
    ground_remarks = Column(Text)
    review_rating = Column(Integer)
    review_text = Column(Text)
    success = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("HuntSession", back_populates="hunt_report")
    field = relationship("Field")
    hunter = relationship("User")

class ForumCategory(Base):
    __tablename__ = "forum_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    icon = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    posts = relationship("ForumPost", back_populates="category")

class ForumPost(Base):
    __tablename__ = "forum_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("forum_categories.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    post_type = Column(String, default="discussion")  # Options: 'discussion', 'for_sale', 'wanted', 'advice'
    price = Column(Float)  # For classifieds (for_sale/wanted)
    location = Column(String)  # For classifieds
    contact_info = Column(String)  # For classifieds
    image_url = Column(String)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    category = relationship("ForumCategory", back_populates="posts")
    user = relationship("User")
    replies = relationship("ForumReply", back_populates="post")

class ForumReply(Base):
    __tablename__ = "forum_replies"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("forum_posts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    post = relationship("ForumPost", back_populates="replies")
    user = relationship("User")

class LandOwnerRequest(Base):
    __tablename__ = "landowner_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    land_name = Column(String, nullable=False)
    land_location = Column(String, nullable=False)
    land_size = Column(String)
    land_type = Column(String)  # e.g., "woodland", "moorland", "coastal"
    description = Column(Text, nullable=False)
    contact_details = Column(String)
    status = Column(String, default="pending")  # Options: 'pending', 'approved', 'rejected'
    admin_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime)
    
    user = relationship("User")

class AnimalTag(Base):
    __tablename__ = "animal_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    tag_number = Column(String, unique=True, nullable=False, index=True)  # UUID format
    hunt_report_id = Column(Integer, ForeignKey("hunt_reports.id"), nullable=False)
    hunter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    species = Column(String, nullable=False)
    condition = Column(String)  # e.g., "Excellent", "Good", "Fair"
    photo_path = Column(String)  # Path to animal photo
    qr_code_path = Column(String)  # Path to QR code image
    animal_tag = Column(String)  # Physical tag number (if different from QR tag)
    disease_type = Column(String)  # Disease info if applicable
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    hunt_report = relationship("HuntReport")
    hunter = relationship("User")
    field = relationship("Field")

def get_db():
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: Could not initialize database: {e}")
        # Don't raise - allow app to start even if DB is unavailable
    
def seed_initial_data():
    """Seed initial data - wrapped in try-except for safety"""
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        SessionLocal = get_session_local()
        db = SessionLocal()
    except Exception as e:
        print(f"Warning: Could not connect to database for seeding: {e}")
        return  # Exit gracefully if DB is unavailable
    try:
        if db.query(User).count() == 0:
            # Shooting Member (UK)
            shooting_member = User(
                email="hunter@example.com",
                password=hash_password("hunter123"),
                role="shooting_member",
                name="John Hunter",
                phone="+44 7700 900000",
                location="London, UK"
            )
            
            # Guide Member (manages subsidised/international lands)
            guide_member = User(
                email="outfitter@example.com",
                password=hash_password("outfitter123"),
                role="guide_member",
                name="Estate Management Ltd",
                phone="+44 7700 900001",
                location="Scottish Highlands"
            )
            
            # International Hunter
            international_hunter = User(
                email="international@example.com",
                password=hash_password("international123"),
                role="international_hunter",
                name="Hans Schmidt",
                phone="+49 151 12345678",
                location="Munich, Germany"
            )
            
            # Landowner Member
            landowner_member = User(
                email="landowner@example.com",
                password=hash_password("landowner123"),
                role="landowner_member",
                name="Highland Estates Ltd",
                phone="+44 7700 900003",
                location="Scottish Highlands"
            )
            
            # Admin
            admin = User(
                email="admin@example.com",
                password=hash_password("admin123"),
                role="admin",
                name="Platform Admin",
                phone="+44 7700 900002",
                location="London, UK"
            )
            
            db.add_all([shooting_member, guide_member, international_hunter, landowner_member, admin])
            db.commit()
            db.refresh(shooting_member)
            db.refresh(guide_member)
            db.refresh(international_hunter)
            db.refresh(landowner_member)
            db.refresh(admin)
            
            fields_data = [
                Field(
                    name="Highland Estate",
                    outfitter_id=guide_member.id,
                    location="Scottish Highlands",
                    lat=57.4778,
                    lon=-4.2247,
                    type="Red Deer Stalking",
                    price_per_day=450,
                    currency="GBP",
                    capacity=4,
                    description="Premium red deer stalking on 5,000 acres of highland estate with professional stalker.",
                    amenities=["Professional Stalker", "Larder Facilities", "Transport", "Accommodation Available"],
                    season="Jul-Oct",
                    image="https://images.unsplash.com/photo-1542273917363-3b1817f69a2d",
                    image_gallery=[
                        "https://images.unsplash.com/photo-1542273917363-3b1817f69a2d",
                        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4",
                        "https://images.unsplash.com/photo-1433838552652-f9a46b332c40"
                    ],
                    blocked_dates=[],
                    field_type="subsidised",
                    subsidy_percentage=30.0,
                    guide_name="Ian MacLeod",
                    guide_contact="+44 7700 900100",
                    species_allowed=["Red Deer", "Roe Deer"],
                    rules_info="Professional stalker must accompany all hunts. Maximum 2 deer per day. All shots must be approved by stalker."
                ),
                Field(
                    name="Cairngorms Sporting Estate",
                    outfitter_id=landowner_member.id,
                    location="Cairngorms National Park",
                    lat=57.0941,
                    lon=-3.6184,
                    type="Driven Grouse",
                    price_per_day=0,
                    currency="GBP",
                    capacity=8,
                    description="Member-access sporting estate with self-guided grouse shooting. Free to all syndicate members.",
                    amenities=["Parking", "Sign-in Lodge", "Basic Facilities"],
                    season="Aug-Dec",
                    image="https://images.unsplash.com/photo-1516466723877-e4ec1d736c8a",
                    image_gallery=[
                        "https://images.unsplash.com/photo-1516466723877-e4ec1d736c8a",
                        "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86",
                        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05"
                    ],
                    blocked_dates=[],
                    field_type="diy-leased",
                    quarry_species=[
                        {"species": "Red Grouse", "total": 300, "remaining": 300},
                        {"species": "Black Grouse", "total": 50, "remaining": 50}
                    ],
                    ground_rules="1. All members must sign in/out at the lodge\n2. Maximum bag limit: 20 birds per day\n3. No shooting before 9am or after 4pm\n4. Report all harvests before leaving\n5. Dogs must be under control at all times",
                    directions="From A9, take B970 towards Feshiebridge. After 3 miles, turn right onto estate road marked 'Sporting Estate'. Follow signs to Sign-in Lodge (2 miles). GPS: 57.0941, -3.6184",
                    contact_name="Estate Keeper",
                    contact_phone="+44 7700 900200",
                    contact_email="keeper@cairngorms-estate.co.uk",
                    special_mentions="IMPORTANT: Due to recent storms, the lower moor path is closed. Use upper access route only. Updated 20 Oct 2025."
                ),
                Field(
                    name="Yorkshire Moorland Shoot",
                    outfitter_id=guide_member.id,
                    location="North Yorkshire",
                    lat=54.2378,
                    lon=-1.4159,
                    type="Pheasant & Partridge",
                    price_per_day=380,
                    currency="GBP",
                    capacity=6,
                    description="Traditional driven pheasant and partridge shooting across beautiful moorland.",
                    amenities=["Beaters", "Gun Dogs", "Refreshments", "Game Processing"],
                    season="Oct-Feb",
                    image="https://images.unsplash.com/photo-1542273917363-3b1817f69a2d",
                    blocked_dates=[],
                    field_type="subsidised",
                    subsidy_percentage=25.0,
                    guide_name="Thomas Wright",
                    guide_contact="+44 7700 900101",
                    species_allowed=["Pheasant", "Partridge", "Woodcock"],
                    rules_info="Guided shoots only. Minimum 4 guns. All safety briefings mandatory."
                ),
                Field(
                    name="Lake District Wildfowling",
                    outfitter_id=landowner_member.id,
                    location="Cumbria",
                    lat=54.5970,
                    lon=-2.8212,
                    type="Duck & Goose",
                    price_per_day=0,
                    currency="GBP",
                    capacity=4,
                    description="Member-access wildfowling ground on coastal marshes. Self-guided hunts, free to all syndicate members.",
                    amenities=["Parking", "Basic Shelter", "Boat Launch"],
                    season="Sep-Jan",
                    image="https://images.unsplash.com/photo-1516466723877-e4ec1d736c8a",
                    blocked_dates=[],
                    field_type="diy-leased",
                    quarry_species=[
                        {"species": "Mallard", "total": 100, "remaining": 85},
                        {"species": "Teal", "total": 50, "remaining": 40},
                        {"species": "Greylag Goose", "total": 30, "remaining": 25},
                        {"species": "Pink-footed Goose", "total": 20, "remaining": 15}
                    ],
                    ground_rules="1. Steel shot ONLY - no lead ammunition\n2. Sign in/out at the hut\n3. High tide only (check tide tables)\n4. Maximum 10 birds per day per member\n5. All dogs must wear high-vis jackets\n6. No shooting within 100m of public footpaths",
                    directions="From M6 junction 36, take A590 west towards Barrow. After Ulverston, turn left on A5087 coastal road. Continue 5 miles, look for 'Wildfowlers Access' sign on left. Park in designated area. GPS: 54.5970, -2.8212",
                    contact_name="Marsh Warden",
                    contact_phone="+44 7700 900201",
                    contact_email="warden@lakedistrictwildfowl.org.uk",
                    special_mentions="TIDE WARNING: High spring tides forecasted 25-30 Oct. Access paths may flood. Check conditions before travelling. Contact warden for updates."
                )
            ]
            
            db.add_all(fields_data)
            db.commit()
            
            # Seed forum categories
            if db.query(ForumCategory).count() == 0:
                categories = [
                    ForumCategory(name="General Discussion", description="General fieldsport topics and conversation", icon="💬"),
                    ForumCategory(name="Equipment For Sale", description="Buy and sell hunting equipment", icon="🛒"),
                    ForumCategory(name="Wanted", description="Looking for specific items or services", icon="🔍"),
                    ForumCategory(name="Advice & Tips", description="Share and request hunting advice", icon="💡"),
                    ForumCategory(name="Trip Reports", description="Share your hunting experiences", icon="📝"),
                ]
                db.add_all(categories)
                db.commit()
            
            # Update subsidised fields with pricing
            highland_estate = db.query(Field).filter(Field.name == "Highland Estate").first()
            if highland_estate and not highland_estate.outing_fee:
                highland_estate.outing_fee = 450.0
                highland_estate.full_price = 650.0
                highland_estate.price_list = [
                    {"item": "Professional Stalker", "cost": 200.0},
                    {"item": "Larder Facilities", "cost": 50.0},
                    {"item": "Transport on Estate", "cost": 75.0},
                    {"item": "Accommodation (per night)", "cost": 150.0}
                ]
                db.commit()
            
            yorkshire_shoot = db.query(Field).filter(Field.name == "Yorkshire Moorland Shoot").first()
            if yorkshire_shoot and not yorkshire_shoot.outing_fee:
                yorkshire_shoot.outing_fee = 380.0
                yorkshire_shoot.full_price = 500.0
                yorkshire_shoot.price_list = [
                    {"item": "Beaters Team", "cost": 150.0},
                    {"item": "Gun Dogs", "cost": 75.0},
                    {"item": "Refreshments & Lunch", "cost": 50.0},
                    {"item": "Game Processing", "cost": 40.0}
                ]
                db.commit()
            
    finally:
        db.close()
