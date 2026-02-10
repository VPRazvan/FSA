from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_session_local, User, Field, Booking, PaymentToken, HuntSession, HuntReport, AnimalTag
from typing import List, Optional, Dict, Tuple
import hashlib
import time
import re
import bcrypt
from datetime import datetime
import uuid
import qrcode
from io import BytesIO
from PIL import Image
import base64
import os

def save_field_images(uploaded_files, field_name: str) -> List[str]:
    """Save uploaded field images and return list of file paths"""
    if not uploaded_files:
        return []
    
    # Create directory if it doesn't exist
    images_dir = "field_images"
    os.makedirs(images_dir, exist_ok=True)
    
    saved_paths = []
    timestamp = int(datetime.now().timestamp())
    
    for idx, uploaded_file in enumerate(uploaded_files):
        # Clean field name for filename
        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', field_name.lower())
        # Create unique filename
        file_extension = uploaded_file.name.split('.')[-1]
        filename = f"{clean_name}_{timestamp}_{idx}.{file_extension}"
        filepath = os.path.join(images_dir, filename)
        
        # Save the file
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        saved_paths.append(filepath)
    
    return saved_paths

def get_db_session():
    """Get database session with lazy initialization"""
    try:
        SessionLocal = get_session_local()
        return SessionLocal()
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def authenticate_user(email: str, password: str) -> Optional[User]:
    try:
        db = get_db_session()
        try:
            user = db.query(User).filter(User.email == email).first()
            if user and verify_password(password, user.password):
                # Check user compliance - non-compliant users cannot log in
                if hasattr(user, 'is_compliant') and user.is_compliant == False:
                    return None  # Block login for non-compliant users
                return user
            return None
        finally:
            db.close()
    except Exception as e:
        print(f"Database error during authentication: {e}")
        return None

def get_user_by_email(email: str) -> Optional[User]:
    try:
        db = get_db_session()
        try:
            return db.query(User).filter(User.email == email).first()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error fetching user by email: {e}")
        return None

def get_all_users() -> List[User]:
    try:
        db = get_db_session()
        try:
            return db.query(User).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error fetching all users: {e}")
        return []

def create_user(email: str, password: str, role: str, name: str, phone: str, location: str) -> Optional[User]:
    try:
        db = get_db_session()
        try:
            user = User(
                email=email,
                password=hash_password(password),
                role=role,
                name=name,
                phone=phone,
                location=location
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()
    except Exception as e:
        print(f"Database error creating user: {e}")
        return None

def admin_update_user(user_id: int, update_data: Dict) -> Optional[User]:
    """Admin function to update any user field including membership and compliance"""
    try:
        db = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Update basic fields
            if 'name' in update_data:
                user.name = update_data['name']
            if 'email' in update_data:
                user.email = update_data['email']
            if 'phone' in update_data:
                user.phone = update_data['phone']
            if 'location' in update_data:
                user.location = update_data['location']
            if 'role' in update_data:
                user.role = update_data['role']
            
            # Update membership fields
            if 'membership_number' in update_data:
                user.membership_number = update_data['membership_number']
            if 'membership_expiry' in update_data:
                user.membership_expiry = update_data['membership_expiry']
            
            # Update compliance status
            if 'is_compliant' in update_data:
                user.is_compliant = update_data['is_compliant']
            
            # Update password if provided
            if 'password' in update_data and update_data['password']:
                user.password = hash_password(update_data['password'])
            
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()
    except Exception as e:
        print(f"Database error updating user: {e}")
        return None

def get_all_fields() -> List[Field]:
    try:
        db = get_db_session()
        try:
            return db.query(Field).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error fetching all fields: {e}")
        return []

def get_fields_within_radius(lat: float, lon: float, radius_miles: float = 50) -> List[Tuple[Field, float]]:
    """
    Find all fields within a given radius (in miles) of a location.
    Returns list of tuples: (Field, distance_in_miles)
    Note: PostGIS ST_MakePoint uses (longitude, latitude) order, not (latitude, longitude)
    """
    try:
        db = get_db_session()
        try:
            radius_meters = radius_miles * 1609.34
            
            # Use ORM query with PostGIS extension for efficient single-query fetch
            # ST_MakePoint uses (lon, lat) order
            query = text("""
                SELECT *,
                       ST_Distance(location_point, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography) / 1609.34 as distance_miles
                FROM fields
                WHERE ST_DWithin(location_point, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_meters)
                ORDER BY distance_miles
            """)
            
            result = db.execute(query, {'lat': lat, 'lon': lon, 'radius_meters': radius_meters}).mappings()
            fields_with_distance = []
            
            for row in result:
                # Create Field object from row data (avoiding N+1 queries)
                field = Field(
                    id=row['id'],
                    name=row['name'],
                    outfitter_id=row['outfitter_id'],
                    location=row['location'],
                    lat=row['lat'],
                    lon=row['lon'],
                    type=row['type'],
                    price_per_day=row['price_per_day'],
                    currency=row['currency'],
                    capacity=row['capacity'],
                    description=row['description'],
                    amenities=row['amenities'],
                    season=row['season'],
                    image=row['image'],
                    blocked_dates=row['blocked_dates'] or [],
                    created_at=row['created_at']
                )
                distance = float(row['distance_miles'])
                fields_with_distance.append((field, distance))
            
            return fields_with_distance
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_fields_within_radius: {e}")
        return []

def geocode_uk_location(location_name: str) -> Optional[Tuple[float, float]]:
    """
    Simple geocoding for major UK cities and regions.
    Returns (lat, lon) tuple or None if location not found.
    """
    uk_locations = {
        'london': (51.5074, -0.1278),
        'birmingham': (52.4862, -1.8904),
        'manchester': (53.4808, -2.2426),
        'edinburgh': (55.9533, -3.1883),
        'glasgow': (55.8642, -4.2518),
        'liverpool': (53.4084, -2.9916),
        'leeds': (53.8008, -1.5491),
        'sheffield': (53.3811, -1.4701),
        'bristol': (51.4545, -2.5879),
        'newcastle': (54.9783, -1.6178),
        'cardiff': (51.4816, -3.1791),
        'belfast': (54.5973, -5.9301),
        'york': (53.9600, -1.0873),
        'bath': (51.3758, -2.3599),
        'oxford': (51.7520, -1.2577),
        'cambridge': (52.2053, 0.1218),
        'norwich': (52.6309, 1.2974),
        'plymouth': (50.3755, -4.1427),
        'exeter': (50.7184, -3.5339),
        'inverness': (57.4778, -4.2247),
        'aberdeen': (57.1497, -2.0943),
        'dundee': (56.4620, -2.9707),
        'stirling': (56.1165, -3.9369),
        'perth': (56.3960, -3.4370),
        'fort william': (56.8198, -5.1052),
        'scottish highlands': (57.4778, -4.2247),
        'cairngorms': (57.0941, -3.6184),
        'north yorkshire': (54.2378, -1.4159),
        'yorkshire': (53.9600, -1.0873),
        'cumbria': (54.5970, -2.8212),
        'lake district': (54.5970, -2.8212),
        'peak district': (53.3500, -1.8300),
        'cotswolds': (51.8330, -1.8433),
        'cornwall': (50.2660, -5.0527),
        'devon': (50.7156, -3.5309),
        'norfolk': (52.6286, 1.2929),
        'suffolk': (52.1872, 0.9708),
        'kent': (51.2787, 0.5217),
        'sussex': (50.9214, -0.1420),
        'hampshire': (51.0577, -1.3081),
        'dorset': (50.7488, -2.3448),
        'somerset': (51.1051, -2.9260),
        'worcestershire': (52.1923, -2.2220),
        'warwickshire': (52.2819, -1.5849),
        'northumberland': (55.2083, -2.0784),
        'durham': (54.7761, -1.5733),
    }
    
    location_lower = location_name.lower().strip()
    return uk_locations.get(location_lower)

def get_field_by_id(field_id: int) -> Optional[Field]:
    try:
        db = get_db_session()
        try:
            return db.query(Field).filter(Field.id == field_id).first()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_field_by_id: {e}")
        return None

def get_fields_by_outfitter(outfitter_id: int) -> List[Field]:
    try:
        db = get_db_session()
        try:
            return db.query(Field).filter(Field.outfitter_id == outfitter_id).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_fields_by_outfitter: {e}")
        return []

def create_field(outfitter_id: int, name: str, location: str, lat: float, lon: float,
                field_type: str, price: float, capacity: int, description: str, season: str) -> Optional[Field]:
    try:
        db = get_db_session()
        try:
            field = Field(
                name=name,
                outfitter_id=outfitter_id,
                location=location,
                lat=lat,
                lon=lon,
                type=field_type,
                price_per_day=price,
                capacity=capacity,
                description=description,
                season=season,
                amenities=[],
                blocked_dates=[],
                image='https://images.unsplash.com/photo-1542273917363-3b1817f69a2d'
            )
            db.add(field)
            db.commit()
            db.refresh(field)
            return field
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_field: {e}")
        return None

def create_subsidised_field(outfitter_id: int, name: str, location: str, lat: float, lon: float,
                           hunting_type: str, price: float, capacity: int, description: str, season: str,
                           guide_name: str, guide_contact: str, subsidy_percentage: float,
                           species_allowed: List[str], rules_info: str, auto_approve: bool, 
                           image_gallery: List[str] = None) -> Optional[Field]:
    """Create a new subsidised field with guide information"""
    try:
        db = get_db_session()
        try:
            field = Field(
                name=name,
                outfitter_id=outfitter_id,
                location=location,
                lat=lat,
                lon=lon,
                type=hunting_type,
                price_per_day=price,
                capacity=capacity,
                description=description,
                season=season,
                amenities=[],
                blocked_dates=[],
                image='https://images.unsplash.com/photo-1542273917363-3b1817f69a2d',
                image_gallery=image_gallery if image_gallery else [],
                field_type='subsidised',
                guide_name=guide_name,
                guide_contact=guide_contact,
                subsidy_percentage=subsidy_percentage,
                species_allowed=species_allowed,
                rules_info=rules_info,
                auto_approve_bookings=auto_approve
            )
            db.add(field)
            db.commit()
            db.refresh(field)
            return field
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_subsidised_field: {e}")
        return None

def create_diy_leased_field(outfitter_id: int, name: str, location: str, lat: float, lon: float,
                           hunting_type: str, price: float, capacity: int, description: str, season: str,
                           quarry_species: List[Dict], rules_info: str, auto_approve: bool,
                           image_gallery: List[str] = None) -> Optional[Field]:
    """Create a new DIY-leased field with quarry species quotas"""
    try:
        db = get_db_session()
        try:
            field = Field(
                name=name,
                outfitter_id=outfitter_id,
                location=location,
                lat=lat,
                lon=lon,
                type=hunting_type,
                price_per_day=price,
                capacity=capacity,
                description=description,
                season=season,
                amenities=[],
                blocked_dates=[],
                image='https://images.unsplash.com/photo-1542273917363-3b1817f69a2d',
                image_gallery=image_gallery if image_gallery else [],
                field_type='diy-leased',
                quarry_species=quarry_species,
                rules_info=rules_info,
                auto_approve_bookings=auto_approve
            )
            db.add(field)
            db.commit()
            db.refresh(field)
            return field
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_diy_leased_field: {e}")
        return None

def update_field_blocked_dates(field_id: int, blocked_dates: List[str]):
    try:
        db = get_db_session()
        try:
            field = db.query(Field).filter(Field.id == field_id).first()
            if field:
                field.blocked_dates = blocked_dates
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in update_field_blocked_dates: {e}")

def update_diy_field_info(field_id: int, special_mentions: str = None, ground_rules: str = None,
                         directions: str = None, contact_name: str = None, contact_phone: str = None,
                         contact_email: str = None):
    """Update DIY field specific information (special mentions, ground rules, directions, contact info)"""
    try:
        db = get_db_session()
        try:
            field = db.query(Field).filter(Field.id == field_id).first()
            if field:
                if special_mentions is not None:
                    field.special_mentions = special_mentions
                if ground_rules is not None:
                    field.ground_rules = ground_rules
                if directions is not None:
                    field.directions = directions
                if contact_name is not None:
                    field.contact_name = contact_name
                if contact_phone is not None:
                    field.contact_phone = contact_phone
                if contact_email is not None:
                    field.contact_email = contact_email
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in update_diy_field_info: {e}")

def update_field_survey_report(field_id: int, survey_report: str):
    """Update wildlife survey report for a field (admin only)"""
    try:
        db = get_db_session()
        try:
            field = db.query(Field).filter(Field.id == field_id).first()
            if field:
                field.wildlife_survey_report = survey_report
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in update_field_survey_report: {e}")

def delete_field(field_id: int) -> bool:
    """Delete a field and all associated data (admin only)"""
    try:
        db = get_db_session()
        try:
            field = db.query(Field).filter(Field.id == field_id).first()
            if field:
                # Delete associated bookings first
                db.query(Booking).filter(Booking.field_id == field_id).delete()
                
                # Delete associated hunt sessions and reports
                sessions = db.query(HuntSession).filter(HuntSession.field_id == field_id).all()
                for session in sessions:
                    # Delete hunt reports for this session
                    db.query(HuntReport).filter(HuntReport.session_id == session.id).delete()
                    # Delete the session
                    db.query(HuntSession).filter(HuntSession.id == session.id).delete()
                
                # Delete the field itself
                db.delete(field)
                db.commit()
                return True
            return False
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in delete_field: {e}")
        return False

def get_all_bookings() -> List[Booking]:
    try:
        db = get_db_session()
        try:
            return db.query(Booking).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_all_bookings: {e}")
        return []

def get_bookings_by_hunter(hunter_id: int) -> List[Booking]:
    try:
        db = get_db_session()
        try:
            return db.query(Booking).filter(Booking.hunter_id == hunter_id).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_bookings_by_hunter: {e}")
        return []

def get_booking_by_id(booking_id: int) -> Optional[Booking]:
    """Get a booking by ID"""
    try:
        db = get_db_session()
        try:
            return db.query(Booking).filter(Booking.id == booking_id).first()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_booking_by_id: {e}")
        return None

def get_bookings_by_field(field_id: int) -> List[Booking]:
    try:
        db = get_db_session()
        try:
            return db.query(Booking).filter(Booking.field_id == field_id).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_bookings_by_field: {e}")
        return []

def get_user_by_id(user_id: int) -> Optional[User]:
    try:
        db = get_db_session()
        try:
            return db.query(User).filter(User.id == user_id).first()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_user_by_id: {e}")
        return None

def get_bookings_for_outfitter_fields(outfitter_id: int) -> List[Booking]:
    try:
        db = get_db_session()
        try:
            return db.query(Booking).join(Field).filter(Field.outfitter_id == outfitter_id).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_bookings_for_outfitter_fields: {e}")
        return []

def check_hunter_has_booking_on_date(hunter_id: int, date: str) -> Tuple[bool, Optional[Booking]]:
    """Check if a hunter already has a booking on a specific date across all sites"""
    try:
        db = get_db_session()
        try:
            existing_booking = db.query(Booking).filter(
                Booking.hunter_id == hunter_id,
                Booking.date == date,
                Booking.status.in_(['confirmed', 'pending'])
            ).first()
            return (existing_booking is not None, existing_booking)
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in check_hunter_has_booking_on_date: {e}")
        return (False, None)

def create_booking(field_id: int, hunter_id: int, date: str, num_hunters: int,
                  total_price: float, payment_id: str, admin_override: bool = False) -> Tuple[Optional[Booking], str]:
    """Create a booking. Returns (booking, message) tuple. Booking is None if creation fails."""
    try:
        db = get_db_session()
        try:
            if not admin_override:
                has_booking, existing_booking = check_hunter_has_booking_on_date(hunter_id, date)
                if has_booking:
                    field_name = "Unknown"
                    if existing_booking:
                        existing_field = db.query(Field).filter(Field.id == existing_booking.field_id).first()
                        if existing_field:
                            field_name = existing_field.name
                    return None, f"Double booking prevented: You already have a booking on {date} at {field_name}"
            
            field = db.query(Field).filter(Field.id == field_id).first()
            
            initial_status = 'confirmed' if (field and field.auto_approve_bookings) else 'pending'
            
            booking = Booking(
                field_id=field_id,
                hunter_id=hunter_id,
                date=date,
                num_hunters=num_hunters,
                total_price=total_price,
                status=initial_status,
                payment_method='card',
                payment_id=payment_id
            )
            db.add(booking)
            db.commit()
            db.refresh(booking)
            
            override_msg = " (Admin Override)" if admin_override else ""
            return booking, f"Booking created successfully{override_msg}"
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_booking: {e}")
        return None, f"Database error: {e}"

def update_booking_status(booking_id: int, status: str):
    try:
        db = get_db_session()
        try:
            booking = db.query(Booking).filter(Booking.id == booking_id).first()
            if booking:
                booking.status = status
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in update_booking_status: {e}")

def check_availability(field_id: int, date: str, num_hunters: int) -> tuple[bool, str]:
    try:
        db = get_db_session()
        try:
            field = db.query(Field).filter(Field.id == field_id).first()
            if not field:
                return False, "Field not found"
            
            if date in (field.blocked_dates or []):
                return False, "Date is blocked by outfitter"
            
            bookings_on_date = db.query(Booking).filter(
                Booking.field_id == field_id,
                Booking.date == date,
                Booking.status.in_(['confirmed', 'pending'])
            ).all()
            
            total_hunters_booked = sum(b.num_hunters for b in bookings_on_date)
            
            if total_hunters_booked + num_hunters > field.capacity:
                return False, f"Insufficient capacity. Only {field.capacity - total_hunters_booked} spots available"
            
            return True, "Available"
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in check_availability: {e}")
        return False, f"Database error: {e}"

def simulate_stripe_payment(amount: float, card_details: Dict) -> tuple[bool, str, Optional[str]]:
    if not card_details.get('card_number') or len(card_details['card_number'].replace(' ', '')) < 15:
        return False, "Invalid card number (must be 15-16 digits)", None
    
    if not card_details.get('cvv') or len(card_details['cvv']) != 3:
        return False, "Invalid CVV (must be 3 digits)", None
    
    expiry = card_details.get('expiry', '')
    if not expiry:
        return False, "Invalid expiry date", None
    
    expiry_pattern = re.match(r'^(\d{2})/(\d{2})$', expiry)
    if not expiry_pattern:
        return False, "Invalid expiry format (use MM/YY)", None
    
    month, year = int(expiry_pattern.group(1)), int(expiry_pattern.group(2))
    if month < 1 or month > 12:
        return False, "Invalid expiry month", None
    
    current_year = datetime.now().year % 100
    current_month = datetime.now().month
    
    if year < current_year or (year == current_year and month < current_month):
        return False, "Card has expired", None
    
    if not card_details.get('name') or len(card_details['name']) < 3:
        return False, "Invalid cardholder name", None
    
    token = hashlib.sha256(f"{card_details['card_number']}{time.time()}".encode()).hexdigest()[:16]
    payment_id = f"pm_{token}"
    
    try:
        db = get_db_session()
        try:
            payment_token = PaymentToken(
                payment_id=payment_id,
                amount=amount,
                currency='GBP',
                status='succeeded',
                card_last4=card_details['card_number'].replace(' ', '')[-4:]
            )
            db.add(payment_token)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in simulate_stripe_payment: {e}")
        return False, f"Database error: {e}", None
    
    return True, "Payment successful", payment_id

def update_user_profile(user_id: int, profile_data: Dict) -> Optional[User]:
    """Update user profile with insurance, certificates, vehicles, and gear"""
    try:
        db = get_db_session()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            if 'insurance_provider' in profile_data:
                user.insurance_provider = profile_data['insurance_provider']
            if 'insurance_number' in profile_data:
                user.insurance_number = profile_data['insurance_number']
            if 'insurance_expiry' in profile_data:
                user.insurance_expiry = profile_data['insurance_expiry']
            if 'fac_certificate' in profile_data:
                user.fac_certificate = profile_data['fac_certificate']
            if 'shotgun_certificate' in profile_data:
                user.shotgun_certificate = profile_data['shotgun_certificate']
            if 'shotgun_expiry' in profile_data:
                user.shotgun_expiry = profile_data['shotgun_expiry']
            if 'vehicles' in profile_data:
                user.vehicles = profile_data['vehicles']
            if 'gear' in profile_data:
                user.gear = profile_data['gear']
            if 'certifications' in profile_data:
                user.certifications = profile_data['certifications']
            if 'membership_number' in profile_data:
                user.membership_number = profile_data['membership_number']
            if 'membership_expiry' in profile_data:
                user.membership_expiry = profile_data['membership_expiry']
            if 'name' in profile_data:
                user.name = profile_data['name']
            if 'phone' in profile_data:
                user.phone = profile_data['phone']
            if 'location' in profile_data:
                user.location = profile_data['location']
            
            db.commit()
            db.refresh(user)
            return user
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in update_user_profile: {e}")
        return None

def create_hunt_session(booking_id: int, hunter_id: int, field_id: int) -> Optional[HuntSession]:
    """Create a new hunt session for a booking"""
    try:
        db = get_db_session()
        try:
            session = HuntSession(
                booking_id=booking_id,
                hunter_id=hunter_id,
                field_id=field_id,
                status='not_started'
            )
            db.add(session)
            db.commit()
            db.refresh(session)
            return session
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_hunt_session: {e}")
        return None

def get_hunt_session_by_booking(booking_id: int) -> Optional[HuntSession]:
    """Get hunt session for a booking"""
    try:
        db = get_db_session()
        try:
            return db.query(HuntSession).filter(HuntSession.booking_id == booking_id).first()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_hunt_session_by_booking: {e}")
        return None

def start_hunt_session(session_id: int) -> Optional[HuntSession]:
    """Start a hunt session"""
    try:
        db = get_db_session()
        try:
            session = db.query(HuntSession).filter(HuntSession.id == session_id).first()
            if session:
                session.start_time = datetime.utcnow()
                session.status = 'active'
                db.commit()
                db.refresh(session)
            return session
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in start_hunt_session: {e}")
        return None

def end_hunt_session(session_id: int) -> Optional[HuntSession]:
    """End a hunt session"""
    try:
        db = get_db_session()
        try:
            session = db.query(HuntSession).filter(HuntSession.id == session_id).first()
            if session:
                session.end_time = datetime.utcnow()
                session.status = 'completed'
                db.commit()
                db.refresh(session)
            return session
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in end_hunt_session: {e}")
        return None

def create_hunt_report(session_id: int, field_id: int, hunter_id: int, report_data: Dict) -> Optional[HuntReport]:
    """Create a hunt report and update field quarry"""
    try:
        db = get_db_session()
        try:
            report = HuntReport(
                session_id=session_id,
                field_id=field_id,
                hunter_id=hunter_id,
                animals_harvested=report_data.get('animals_harvested', 0),
                species_harvested=report_data.get('species_harvested', []),
                animals_detail=report_data.get('animals_detail', []),
                weather_conditions=report_data.get('weather_conditions', ''),
                time_spent_hours=report_data.get('time_spent_hours', 0),
                notes=report_data.get('notes', ''),
                ground_remarks=report_data.get('ground_remarks', ''),
                review_rating=report_data.get('review_rating', None),
                review_text=report_data.get('review_text', ''),
                success=report_data.get('success', False)
            )
            db.add(report)
            
            field = db.query(Field).filter(Field.id == field_id).first()
            if field:
                animals_harvested = report_data.get('animals_harvested', 0)
                species_harvested = report_data.get('species_harvested', [])
                
                field.last_visit_date = datetime.now().strftime('%Y-%m-%d')
                field.last_visit_had_harvest = animals_harvested > 0
                
                if field.field_type == 'diy-leased':
                    if field.quarry_species:
                        for harvested in species_harvested:
                            species_name = harvested.get('species', harvested.get(' species', ''))
                            quantity = harvested.get('quantity', 0)
                            
                            for quarry in field.quarry_species:
                                if quarry.get('species') == species_name:
                                    quarry['remaining'] = max(0, quarry.get('remaining', 0) - quantity)
                                    break
                        
                        from sqlalchemy import update
                        db.execute(
                            update(Field).where(Field.id == field_id).values(quarry_species=field.quarry_species)
                        )
                    elif field.quarry_remaining is not None:
                        field.quarry_remaining = max(0, field.quarry_remaining - animals_harvested)
            
            db.commit()
            db.refresh(report)
            return report
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_hunt_report: {e}")
        return None

def get_todays_bookings_for_hunter(hunter_id: int) -> List[Booking]:
    """Get today's confirmed bookings for a hunter"""
    try:
        db = get_db_session()
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            return db.query(Booking).filter(
                Booking.hunter_id == hunter_id,
                Booking.date == today,
                Booking.status == 'confirmed'
            ).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_todays_bookings_for_hunter: {e}")
        return []

def get_all_hunt_sessions() -> List[HuntSession]:
    """Get all hunt sessions (for admin analytics)"""
    try:
        db = get_db_session()
        try:
            return db.query(HuntSession).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_all_hunt_sessions: {e}")
        return []

def get_hunt_sessions_by_hunter(hunter_id: int) -> List[HuntSession]:
    """Get all hunt sessions for a specific hunter"""
    try:
        db = get_db_session()
        try:
            return db.query(HuntSession).filter(HuntSession.hunter_id == hunter_id).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_hunt_sessions_by_hunter: {e}")
        return []

def get_hunt_sessions_by_field(field_id: int) -> List[HuntSession]:
    """Get all hunt sessions for a specific field"""
    try:
        db = get_db_session()
        try:
            return db.query(HuntSession).filter(HuntSession.field_id == field_id).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_hunt_sessions_by_field: {e}")
        return []

def get_all_hunt_reports() -> List[HuntReport]:
    """Get all hunt reports (for admin analytics)"""
    try:
        db = get_db_session()
        try:
            return db.query(HuntReport).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_all_hunt_reports: {e}")
        return []

def get_hunt_reports_by_field(field_id: int) -> List[HuntReport]:
    """Get all hunt reports for a specific field"""
    try:
        db = get_db_session()
        try:
            return db.query(HuntReport).filter(HuntReport.field_id == field_id).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_hunt_reports_by_field: {e}")
        return []

def get_hunt_report_by_session(session_id: int) -> Optional[HuntReport]:
    """Get hunt report for a specific hunt session"""
    try:
        db = get_db_session()
        try:
            return db.query(HuntReport).filter(HuntReport.session_id == session_id).first()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_hunt_report_by_session: {e}")
        return None

def update_hunt_report(report_id: int, review_rating: int = None, review_text: str = None) -> Optional[HuntReport]:
    """Update review portion of a hunt report"""
    try:
        db = get_db_session()
        try:
            report = db.query(HuntReport).filter(HuntReport.id == report_id).first()
            if report:
                if review_rating is not None:
                    report.review_rating = review_rating
                if review_text is not None:
                    report.review_text = review_text
                db.commit()
                db.refresh(report)
                return report
            return None
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in update_hunt_report: {e}")
        return None

def get_total_quota_remaining(field: Field) -> int:
    """Calculate total remaining quota across all species for a field"""
    if field.field_type != 'diy-leased':
        return None
    
    if field.quarry_species:
        return sum(q.get('remaining', 0) for q in field.quarry_species)
    elif field.quarry_remaining is not None:
        return field.quarry_remaining
    return None

def get_total_quota(field: Field) -> int:
    """Calculate total quota across all species for a field"""
    if field.field_type != 'diy-leased':
        return None
    
    if field.quarry_species:
        return sum(q.get('total', 0) for q in field.quarry_species)
    elif field.quarry_total is not None:
        return field.quarry_total
    return None

def is_quota_exhausted(field: Field) -> bool:
    """Check if all quotas are exhausted for a DIY-leased field"""
    if field.field_type != 'diy-leased':
        return False
    
    if field.quarry_species:
        return all(q.get('remaining', 0) <= 0 for q in field.quarry_species)
    elif field.quarry_remaining is not None:
        return field.quarry_remaining <= 0
    return False

def get_quota_color(remaining: int, total: int) -> str:
    """Get color indicator for quota status"""
    if total == 0:
        return "🔴"
    percentage = (remaining / total) * 100
    if percentage > 50:
        return "🟢"
    elif percentage > 20:
        return "🟡"
    else:
        return "🔴"

# ============================================================================
# FORUM FUNCTIONS
# ============================================================================

def get_all_forum_categories():
    """Get all forum categories"""
    from database import ForumCategory
    try:
        db = get_db_session()
        try:
            return db.query(ForumCategory).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_all_forum_categories: {e}")
        return []

def create_forum_category(name: str, description: str = None, icon: str = None):
    """Create a new forum category"""
    from database import ForumCategory
    try:
        db = get_db_session()
        try:
            category = ForumCategory(name=name, description=description, icon=icon)
            db.add(category)
            db.commit()
            db.refresh(category)
            return category
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_forum_category: {e}")
        return None

def get_forum_posts_by_category(category_id: int):
    """Get all posts in a specific category"""
    from database import ForumPost
    try:
        db = get_db_session()
        try:
            return db.query(ForumPost).filter(ForumPost.category_id == category_id).order_by(ForumPost.created_at.desc()).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_forum_posts_by_category: {e}")
        return []

def get_all_forum_posts():
    """Get all forum posts"""
    from database import ForumPost
    try:
        db = get_db_session()
        try:
            return db.query(ForumPost).order_by(ForumPost.created_at.desc()).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_all_forum_posts: {e}")
        return []

def create_forum_post(category_id: int, user_id: int, title: str, content: str, 
                      post_type: str = "discussion", price: float = None, 
                      location: str = None, contact_info: str = None, image_url: str = None):
    """Create a new forum post"""
    from database import ForumPost
    try:
        db = get_db_session()
        try:
            post = ForumPost(
                category_id=category_id,
                user_id=user_id,
                title=title,
                content=content,
                post_type=post_type,
                price=price,
                location=location,
                contact_info=contact_info,
                image_url=image_url
            )
            db.add(post)
            db.commit()
            db.refresh(post)
            return post
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_forum_post: {e}")
        return None

def get_forum_post_by_id(post_id: int):
    """Get a specific forum post"""
    from database import ForumPost
    try:
        db = get_db_session()
        try:
            return db.query(ForumPost).filter(ForumPost.id == post_id).first()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_forum_post_by_id: {e}")
        return None

def increment_post_views(post_id: int):
    """Increment view count for a post"""
    from database import ForumPost
    try:
        db = get_db_session()
        try:
            post = db.query(ForumPost).filter(ForumPost.id == post_id).first()
            if post:
                post.views = (post.views or 0) + 1
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in increment_post_views: {e}")

def get_forum_replies_by_post(post_id: int):
    """Get all replies for a specific post"""
    from database import ForumReply
    try:
        db = get_db_session()
        try:
            return db.query(ForumReply).filter(ForumReply.post_id == post_id).order_by(ForumReply.created_at.asc()).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_forum_replies_by_post: {e}")
        return []

def create_forum_reply(post_id: int, user_id: int, content: str):
    """Create a reply to a forum post"""
    from database import ForumReply
    try:
        db = get_db_session()
        try:
            reply = ForumReply(post_id=post_id, user_id=user_id, content=content)
            db.add(reply)
            db.commit()
            db.refresh(reply)
            return reply
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_forum_reply: {e}")
        return None

# ============================================================================
# LANDOWNER REQUEST FUNCTIONS
# ============================================================================

def create_landowner_request(user_id: int, land_name: str, land_location: str, 
                             description: str, land_size: str = None, 
                             land_type: str = None, contact_details: str = None):
    """Create a new landowner request"""
    from database import LandOwnerRequest
    try:
        db = get_db_session()
        try:
            request = LandOwnerRequest(
                user_id=user_id,
                land_name=land_name,
                land_location=land_location,
                description=description,
                land_size=land_size,
                land_type=land_type,
                contact_details=contact_details,
                status="pending"
            )
            db.add(request)
            db.commit()
            db.refresh(request)
            return request
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_landowner_request: {e}")
        return None

def get_all_landowner_requests():
    """Get all landowner requests"""
    from database import LandOwnerRequest
    try:
        db = get_db_session()
        try:
            return db.query(LandOwnerRequest).order_by(LandOwnerRequest.created_at.desc()).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_all_landowner_requests: {e}")
        return []

def get_landowner_requests_by_user(user_id: int):
    """Get all requests from a specific user"""
    from database import LandOwnerRequest
    try:
        db = get_db_session()
        try:
            return db.query(LandOwnerRequest).filter(LandOwnerRequest.user_id == user_id).order_by(LandOwnerRequest.created_at.desc()).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_landowner_requests_by_user: {e}")
        return []

def get_pending_landowner_requests():
    """Get all pending landowner requests"""
    from database import LandOwnerRequest
    try:
        db = get_db_session()
        try:
            return db.query(LandOwnerRequest).filter(LandOwnerRequest.status == "pending").order_by(LandOwnerRequest.created_at.asc()).all()
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_pending_landowner_requests: {e}")
        return []

def update_landowner_request_status(request_id: int, status: str, admin_notes: str = None):
    """Update the status of a landowner request"""
    from database import LandOwnerRequest
    from datetime import datetime
    try:
        db = get_db_session()
        try:
            request = db.query(LandOwnerRequest).filter(LandOwnerRequest.id == request_id).first()
            if request:
                request.status = status
                if admin_notes:
                    request.admin_notes = admin_notes
                request.reviewed_at = datetime.utcnow()
                db.commit()
                db.refresh(request)
                return request
            return None
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in update_landowner_request_status: {e}")
        return None

# ============================================================================
# PRICING & PRICE LIST FUNCTIONS
# ============================================================================

def update_field_pricing(field_id: int, outing_fee: float = None, 
                        price_list: list = None, full_price: float = None):
    """Update pricing information for a field"""
    try:
        db = get_db_session()
        try:
            field = db.query(Field).filter(Field.id == field_id).first()
            if field:
                if outing_fee is not None:
                    field.outing_fee = outing_fee
                if price_list is not None:
                    field.price_list = price_list
                if full_price is not None:
                    field.full_price = full_price
                db.commit()
                db.refresh(field)
                return field
            return None
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in update_field_pricing: {e}")
        return None

def add_price_list_item(field_id: int, item_name: str, cost: float):
    """Add an item to a field's price list"""
    try:
        db = get_db_session()
        try:
            field = db.query(Field).filter(Field.id == field_id).first()
            if field:
                price_list = field.price_list or []
                price_list.append({"item": item_name, "cost": cost})
                field.price_list = price_list
                db.commit()
                db.refresh(field)
                return field
            return None
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in add_price_list_item: {e}")
        return None

def remove_price_list_item(field_id: int, item_name: str):
    """Remove an item from a field's price list"""
    try:
        db = get_db_session()
        try:
            field = db.query(Field).filter(Field.id == field_id).first()
            if field and field.price_list:
                field.price_list = [item for item in field.price_list if item.get('item') != item_name]
                db.commit()
                db.refresh(field)
                return field
            return None
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in remove_price_list_item: {e}")
        return None

def generate_unique_tag_number():
    """Generate unique UUID-based tag number"""
    return str(uuid.uuid4())

def generate_qr_code(tag_number: str):
    """Generate QR code image for a tag number
    Returns: path to saved QR code image
    """
    verification_url = f"https://fieldsports-alliance.replit.app/verify?tag={tag_number}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(verification_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    qr_path = f"qr_codes/{tag_number}.png"
    img.save(qr_path)
    
    return qr_path

def save_animal_photo(photo_bytes, tag_number: str):
    """Save animal photo to filesystem
    Args:
        photo_bytes: Image bytes from st.camera_input or st.file_uploader
        tag_number: Unique tag number
    Returns: path to saved photo
    """
    img = Image.open(BytesIO(photo_bytes))
    
    photo_path = f"animal_photos/{tag_number}.jpg"
    img.save(photo_path, "JPEG", quality=90)
    
    return photo_path

def create_animal_tag(
    hunt_report_id: int,
    hunter_id: int,
    field_id: int,
    species: str,
    condition: str,
    photo_bytes=None,
    animal_tag: str = None,
    disease_type: str = None,
    notes: str = None
):
    """Create a new animal tag with QR code and photo"""
    try:
        db = get_db_session()
        try:
            tag_number = generate_unique_tag_number()
            
            qr_code_path = generate_qr_code(tag_number)
            
            photo_path = None
            if photo_bytes:
                photo_path = save_animal_photo(photo_bytes, tag_number)
            
            new_tag = AnimalTag(
                tag_number=tag_number,
                hunt_report_id=hunt_report_id,
                hunter_id=hunter_id,
                field_id=field_id,
                species=species,
                condition=condition,
                photo_path=photo_path,
                qr_code_path=qr_code_path,
                animal_tag=animal_tag,
                disease_type=disease_type,
                notes=notes
            )
            
            db.add(new_tag)
            db.commit()
            db.refresh(new_tag)
            
            return new_tag
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in create_animal_tag: {e}")
        return None

def get_animal_tag_by_tag_number(tag_number: str):
    """Retrieve animal tag by tag number (for public verification)"""
    try:
        db = get_db_session()
        try:
            tag = db.query(AnimalTag).filter(AnimalTag.tag_number == tag_number).first()
            return tag
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_animal_tag_by_tag_number: {e}")
        return None

def get_animal_tags_by_hunt_report(hunt_report_id: int):
    """Get all animal tags for a hunt report"""
    try:
        db = get_db_session()
        try:
            tags = db.query(AnimalTag).filter(AnimalTag.hunt_report_id == hunt_report_id).all()
            return tags
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_animal_tags_by_hunt_report: {e}")
        return []

def get_all_animal_tags_by_hunter(hunter_id: int):
    """Get all animal tags created by a hunter"""
    try:
        db = get_db_session()
        try:
            tags = db.query(AnimalTag).filter(AnimalTag.hunter_id == hunter_id).order_by(AnimalTag.created_at.desc()).all()
            return tags
        finally:
            db.close()
    except Exception as e:
        print(f"Database error in get_all_animal_tags_by_hunter: {e}")
        return []
