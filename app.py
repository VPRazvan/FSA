import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
from db_helpers import *
from database import User, Field, Booking, AnimalTag
from notifications import email_service
import os
import uuid
import html

st.set_page_config(
    page_title="Fieldsports Alliance",
    page_icon="🦌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Health check endpoint for deployment
query_params = st.query_params
if "health" in query_params:
    st.write("OK")
    st.stop()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user_id = None
    st.session_state.user_role = None

def send_booking_notification(booking_id: int, event_type: str):
    """Placeholder for booking notification system"""
    pass

def format_relative_time(dt):
    """Format datetime as relative time (e.g., '2 hours ago')"""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt
    
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"

def login_page():
    st.title("🦌 Fieldsports Alliance")
    st.markdown("### Welcome to the UK's Premier Fieldsport Booking System")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        tab1, tab2, tab3 = st.tabs(["Login", "Sign Up", "Demo Accounts"])
        
        with tab1:
            st.markdown("#### Login to Your Account")
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", use_container_width=True, type="primary"):
                # First check if user exists and verify password
                existing_user = get_user_by_email(email)
                if existing_user and verify_password(password, existing_user.password):
                    # Password is correct - check compliance
                    if hasattr(existing_user, 'is_compliant') and existing_user.is_compliant == False:
                        st.error("🚫 Your account has been deactivated due to non-compliance. Please contact admin to reactivate your account.")
                    else:
                        # User is compliant - proceed with login
                        st.session_state.logged_in = True
                        st.session_state.current_user_id = existing_user.id
                        st.session_state.user_role = existing_user.role
                        st.rerun()
                else:
                    st.error("Invalid credentials")
        
        with tab2:
            st.markdown("#### Create Your Account")
            
            st.markdown("**I am a:**")
            user_type = st.radio(
                "Select your account type",
                ["Shooting Member - I want to book UK fieldsport experiences", 
                 "International Hunter - I want to book international opportunities",
                 "Landowner Member - I want to request my DIY land be added",
                 "Guide Member - I want to offer guided hunting experiences"],
                label_visibility="collapsed"
            )
            
            if "Shooting Member" in user_type:
                role = "shooting_member"
            elif "International Hunter" in user_type:
                role = "international_hunter"
            elif "Landowner Member" in user_type:
                role = "landowner_member"
            else:
                role = "guide_member"
            
            st.markdown("---")
            
            with st.form("registration_form"):
                st.markdown("**Account Details**")
                col1, col2 = st.columns(2)
                with col1:
                    reg_name = st.text_input("Full Name*", placeholder="John Smith")
                    reg_email = st.text_input("Email*", placeholder="john@example.com")
                with col2:
                    reg_phone = st.text_input("Phone Number*", placeholder="+44 7700 900000")
                    reg_location = st.text_input("Location*", placeholder="London, Edinburgh, etc.")
                
                reg_password = st.text_input("Password*", type="password", placeholder="Min 6 characters")
                reg_password_confirm = st.text_input("Confirm Password*", type="password")
                
                if role in ["landowner_member", "guide_member"]:
                    st.markdown("---")
                    land_type_label = "Landowner Information" if role == "landowner_member" else "Guide Information"
                    st.markdown(f"**{land_type_label}**")
                    st.caption("Admin will review your request and add your land/experience to the platform")
                    land_description = st.text_area(
                        "Briefly describe your offering",
                        placeholder="e.g., 500 acres in Scottish Highlands, ideal for red deer stalking" if role == "landowner_member" else "e.g., Professional guided stalking with 20 years experience",
                        help="This will be included in your land addition request"
                    )
                
                st.markdown("---")
                terms_accepted = st.checkbox(
                    "I agree to the Terms of Service and Privacy Policy",
                    help="By checking this box, you agree to our platform's terms and conditions"
                )
                
                submit_button = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                
                if submit_button:
                    if not all([reg_name, reg_email, reg_phone, reg_location, reg_password, reg_password_confirm]):
                        st.error("Please fill in all required fields marked with *")
                    elif reg_password != reg_password_confirm:
                        st.error("Passwords do not match")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters long")
                    elif not terms_accepted:
                        st.error("You must accept the Terms of Service to create an account")
                    elif get_user_by_email(reg_email):
                        st.error("An account with this email already exists. Please login instead.")
                    else:
                        new_user = create_user(
                            email=reg_email,
                            password=reg_password,
                            role=role,
                            name=reg_name,
                            phone=reg_phone,
                            location=reg_location
                        )
                        
                        if new_user:
                            st.success(f"✅ Account created successfully! Welcome, {reg_name}!")
                            st.info("You can now login with your credentials.")
                            
                            if role == "landowner_member":
                                st.success("🏞️ As a Landowner Member, you can submit a DIY land addition request once you login. Admin will review and add your land to the platform!")
                            elif role == "guide_member":
                                st.success("🌟 As a Guide Member, you can submit a request to offer subsidised or international hunting experiences. Admin will review and add your offering to the platform!")
                            elif role == "shooting_member":
                                st.success("🎯 As a Shooting Member, you can now browse and book DIY grounds (free) and subsidised experiences!")
                            elif role == "international_hunter":
                                st.success("🌍 As an International Hunter, you can now browse and book subsidised and international opportunities!")
                            
                            st.balloons()
                        else:
                            st.error("Failed to create account. Please try again.")
        
        with tab3:
            st.markdown("**Test Accounts (all 5 user types):**")
            st.code("Shooting Member: hunter@example.com / hunter123")
            st.code("International Hunter: international@example.com / international123")
            st.code("Landowner Member: landowner@example.com / landowner123")
            st.code("Guide Member: outfitter@example.com / outfitter123")
            st.code("Admin: admin@example.com / admin123")

def logout():
    st.session_state.logged_in = False
    st.session_state.current_user_id = None
    st.session_state.user_role = None
    st.rerun()

def show_diy_field_details(field, user):
    """Show comprehensive DIY field detail page"""
    st.title(f"🏞️ {field.name}")
    
    if st.button("⬅️ Back to Browse", type="secondary"):
        st.session_state.viewing_diy_field_id = None
        st.rerun()
    
    st.markdown("---")
    
    if field.special_mentions:
        st.warning(f"⚠️ **SPECIAL NOTICE**\n\n{field.special_mentions}")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 Calendar & Booking", "📊 Booking History", "🗺️ Location & Info", "⭐ Reviews", "📋 Ground Details"])
    
    with tab1:
        st.header("Book Your Hunt")
        st.markdown(f"### 🆓 FREE for All Members")
        st.info("This is a DIY self-guided hunting ground. No payment required - simply book your preferred date!")
        
        st.markdown("---")
        st.subheader("📅 Select Your Date")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_date = st.date_input("Choose hunt date", datetime.now(), key="diy_date_picker")
        
        with col2:
            st.markdown("**Season:** " + (field.season or "All Year"))
        
        blocked_dates = field.blocked_dates or []
        existing_bookings = get_bookings_by_field(field.id)
        booked_dates = [b.date for b in existing_bookings if b.status in ['confirmed', 'pending']]
        
        selected_date_str = selected_date.strftime("%Y-%m-%d")
        
        st.markdown("---")
        st.subheader("📆 Availability Calendar")
        st.markdown("View all bookings for this ground:")
        
        if booked_dates:
            st.markdown("**Already Booked Dates:**")
            for date_str in sorted(booked_dates):
                booking_hunter = next((b for b in existing_bookings if b.date == date_str), None)
                if booking_hunter:
                    hunter_name = get_user_by_id(booking_hunter.hunter_id)
                    if hunter_name:
                        st.markdown(f"- 🔴 {date_str} - Booked by {hunter_name.name if hunter_name.id == user.id else 'Another Member'}")
        else:
            st.success("✅ No bookings yet - be the first!")
        
        st.markdown("---")
        
        date_available = selected_date_str not in blocked_dates and selected_date_str not in booked_dates
        hunter_has_booking, _ = check_hunter_has_booking_on_date(user.id, selected_date_str)
        quota_ok = not is_quota_exhausted(field)
        
        if not date_available:
            st.error(f"❌ {selected_date_str} is not available (already booked or blocked)")
        elif hunter_has_booking:
            st.error(f"❌ You already have a booking on {selected_date_str} at another location")
        elif not quota_ok:
            st.error("❌ Quota exhausted for this ground")
        else:
            st.success(f"✅ {selected_date_str} is available!")
            
            if st.button("📝 Confirm Booking", type="primary", key="confirm_diy_booking"):
                new_booking, booking_message = create_booking(
                    field_id=field.id,
                    hunter_id=user.id,
                    date=selected_date_str,
                    num_hunters=1,
                    total_price=0,
                    payment_id=f"FREE_{datetime.now().timestamp()}"
                )
                
                if new_booking:
                    send_booking_notification(new_booking.id, "created")
                    if field.auto_approve_bookings:
                        st.success("🎉 Booking confirmed! No payment required.")
                        st.balloons()
                    else:
                        st.success("📝 Booking request submitted! Awaiting landowner approval. No payment required.")
                    st.rerun()
                else:
                    st.error(f"Failed to create booking: {booking_message}")
    
    with tab2:
        st.header("📊 Booking History & Success Rates")
        st.markdown("See how other members have fared at this ground")
        
        all_bookings = get_bookings_by_field(field.id)
        confirmed_bookings = [b for b in all_bookings if b.status == 'confirmed']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Visits", len(confirmed_bookings))
        with col2:
            completed_hunts = get_hunt_sessions_by_field(field.id)
            st.metric("Completed Hunts", len([h for h in completed_hunts if h.status == 'completed']))
        with col3:
            hunt_reports = [get_hunt_report_by_session(h.id) for h in completed_hunts if h.status == 'completed']
            successful_hunts = len([r for r in hunt_reports if r and r.animals_harvested > 0])
            success_rate = (successful_hunts / len(hunt_reports) * 100) if hunt_reports else 0
            st.metric("Success Rate", f"{success_rate:.0f}%")
        
        st.markdown("---")
        st.subheader("Recent Visits")
        
        recent_bookings = sorted(confirmed_bookings, key=lambda b: b.date, reverse=True)[:10]
        
        if recent_bookings:
            for booking in recent_bookings:
                hunter = get_user_by_id(booking.hunter_id)
                session = next((s for s in completed_hunts if s.booking_id == booking.id), None)
                
                if session and session.status == 'completed':
                    report = get_hunt_report_by_session(session.id)
                    if report:
                        success_icon = "✅" if report.animals_harvested > 0 else "❌"
                        st.markdown(f"**{booking.date}** - {hunter.name if hunter.id == user.id else 'Member'} {success_icon} ({report.animals_harvested} animals)")
                    else:
                        st.markdown(f"**{booking.date}** - {hunter.name if hunter.id == user.id else 'Member'} (No report)")
                else:
                    st.markdown(f"**{booking.date}** - {hunter.name if hunter.id == user.id else 'Member'} (Upcoming)")
        else:
            st.info("No booking history yet for this ground")
    
    with tab3:
        st.header("🗺️ Location & Getting There")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Map")
            m = folium.Map(location=[field.lat, field.lon], zoom_start=13)
            folium.Marker(
                [field.lat, field.lon],
                popup=field.name,
                tooltip=field.name,
                icon=folium.Icon(color='green', icon='tree', prefix='fa')
            ).add_to(m)
            st_folium(m, width=700, height=400)
        
        with col2:
            st.subheader("Quick Info")
            st.markdown(f"**Location:** {field.location}")
            st.markdown(f"**Type:** {field.type}")
            st.markdown(f"**Season:** {field.season}")
            st.markdown(f"**GPS:** {field.lat}, {field.lon}")
        
        st.markdown("---")
        
        if field.directions:
            st.subheader("📍 Directions")
            st.markdown(field.directions)
        
        st.markdown("---")
        
        st.subheader("📞 Contact Information")
        if field.contact_name:
            st.markdown(f"**Contact:** {field.contact_name}")
        if field.contact_phone:
            st.markdown(f"**Phone:** {field.contact_phone}")
        if field.contact_email:
            st.markdown(f"**Email:** {field.contact_email}")
        
        if not any([field.contact_name, field.contact_phone, field.contact_email]):
            st.info("Contact details not yet available")
    
    with tab4:
        st.header("⭐ Member Reviews")
        
        completed_hunts = get_hunt_sessions_by_field(field.id)
        hunt_reports = []
        for session in completed_hunts:
            if session.status == 'completed':
                report = get_hunt_report_by_session(session.id)
                if report and report.review_rating:
                    hunt_reports.append(report)
        
        if hunt_reports:
            avg_rating = sum(r.review_rating for r in hunt_reports) / len(hunt_reports)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Average Rating", f"{'⭐' * int(avg_rating)} ({avg_rating:.1f}/5)")
                st.metric("Total Reviews", len(hunt_reports))
            
            st.markdown("---")
            st.subheader("Recent Reviews")
            
            for report in sorted(hunt_reports, key=lambda r: r.created_at, reverse=True)[:10]:
                hunter = get_user_by_id(report.hunter_id)
                stars = "⭐" * report.review_rating
                
                with st.expander(f"{stars} - {hunter.name if hunter else 'Member'} ({report.created_at.strftime('%Y-%m-%d')})", expanded=True):
                    st.markdown("✅ **Verified Hunt** - Review from actual hunt session")
                    st.markdown("---")
                    if report.review_text:
                        st.markdown(f"*\"{report.review_text}\"*")
                    
                    if report.animals_harvested > 0:
                        st.success(f"✅ Successful hunt - {report.animals_harvested} animals harvested")
                    else:
                        st.info("❌ No harvest on this visit")
        else:
            st.info("No reviews yet. Be the first to review this ground after your hunt!")
    
    with tab5:
        st.header("📋 Ground Rules & Information")
        
        st.subheader("Description")
        st.markdown(field.description)
        
        st.markdown("---")
        
        if field.ground_rules:
            st.subheader("🔰 Ground Rules")
            st.markdown(field.ground_rules)
        
        st.markdown("---")
        
        st.subheader("🎯 Quarry Species & Quotas")
        if field.quarry_species:
            for q in field.quarry_species:
                total = q.get('total', 0)
                remaining = q.get('remaining', 0)
                percentage = (remaining / total * 100) if total > 0 else 0
                color = get_quota_color(remaining, total)
                
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**{q['species']}**")
                with col2:
                    st.markdown(f"{color} {remaining} / {total}")
                with col3:
                    st.progress(percentage / 100)
        
        st.markdown("---")
        
        if field.amenities:
            st.subheader("🏕️ Amenities")
            cols = st.columns(2)
            for i, amenity in enumerate(field.amenities):
                with cols[i % 2]:
                    st.markdown(f"✓ {amenity}")

def show_subsidised_field_details(field, user):
    """Show comprehensive subsidised/international field detail page"""
    st.title(f"🌟 {field.name}")
    
    if st.button("⬅️ Back to Browse", type="secondary"):
        st.session_state.viewing_subsidised_field_id = None
        st.rerun()
    
    st.markdown("---")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📅 Calendar & Booking", "📊 Booking History", "🗺️ Location & Info", "⭐ Reviews", "💰 Price List"])
    
    with tab1:
        st.header("Book Your Hunt")
        
        # Display pricing based on user role
        if user.role in ['shooting_member', 'hunter']:
            # UK members get subsidised pricing
            outing_fee = field.outing_fee or 0
            full_price = field.full_price or field.price_per_day
            st.markdown(f"### Subsidised Pricing for UK Members")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Outing Fee (Your Price)", f"£{outing_fee}")
            with col2:
                st.metric("Full Price", f"~~£{full_price}~~")
            st.success(f"💰 You save £{full_price - outing_fee} with your membership!")
            booking_price = outing_fee
        else:
            # International hunters pay full price
            full_price = field.full_price or field.price_per_day
            st.markdown(f"### International Pricing")
            st.metric("Price", f"£{full_price}")
            booking_price = full_price
        
        st.markdown("---")
        st.subheader("📅 Select Your Date")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_date = st.date_input("Choose hunt date", datetime.now(), key="subsidised_date_picker")
        
        with col2:
            st.markdown("**Season:** " + (field.season or "All Year"))
        
        blocked_dates = field.blocked_dates or []
        existing_bookings = get_bookings_by_field(field.id)
        booked_dates = [b.date for b in existing_bookings if b.status in ['confirmed', 'pending']]
        
        selected_date_str = selected_date.strftime("%Y-%m-%d")
        
        st.markdown("---")
        st.subheader("📆 Availability Calendar")
        st.markdown("View all bookings for this ground:")
        
        if booked_dates:
            st.markdown("**Already Booked Dates:**")
            for date_str in sorted(booked_dates):
                booking_hunter = next((b for b in existing_bookings if b.date == date_str), None)
                if booking_hunter:
                    hunter_name = get_user_by_id(booking_hunter.hunter_id)
                    if hunter_name:
                        st.markdown(f"- 🔴 {date_str} - Booked by {hunter_name.name if hunter_name.id == user.id else 'Another Member'}")
        else:
            st.success("✅ No bookings yet - be the first!")
        
        st.markdown("---")
        
        date_available = selected_date_str not in blocked_dates and selected_date_str not in booked_dates
        hunter_has_booking, _ = check_hunter_has_booking_on_date(user.id, selected_date_str)
        
        if not date_available:
            st.error(f"❌ {selected_date_str} is not available (already booked or blocked)")
        elif hunter_has_booking:
            st.error(f"❌ You already have a booking on {selected_date_str} at another location")
        else:
            st.success(f"✅ {selected_date_str} is available!")
            
            if st.button("📝 Confirm Booking", type="primary", key="confirm_subsidised_booking"):
                new_booking, booking_message = create_booking(
                    field_id=field.id,
                    hunter_id=user.id,
                    date=selected_date_str,
                    num_hunters=1,
                    total_price=booking_price,
                    payment_id=f"CARD_{datetime.now().timestamp()}"
                )
                
                if new_booking:
                    send_booking_notification(new_booking.id, "created")
                    if field.auto_approve_bookings:
                        st.success(f"🎉 Booking confirmed! Total: £{booking_price}")
                        st.balloons()
                    else:
                        st.success(f"📝 Booking request submitted! Awaiting guide approval. Total: £{booking_price}")
                    st.rerun()
                else:
                    st.error(f"Failed to create booking: {booking_message}")
    
    with tab2:
        st.header("📊 Booking History & Success Rates")
        st.markdown("See how other hunters have fared at this field")
        
        all_bookings = get_bookings_by_field(field.id)
        confirmed_bookings = [b for b in all_bookings if b.status == 'confirmed']
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Visits", len(confirmed_bookings))
        with col2:
            completed_hunts = get_hunt_sessions_by_field(field.id)
            st.metric("Completed Hunts", len([h for h in completed_hunts if h.status == 'completed']))
        with col3:
            hunt_reports = [get_hunt_report_by_session(h.id) for h in completed_hunts if h.status == 'completed']
            successful_hunts = len([r for r in hunt_reports if r and r.animals_harvested > 0])
            success_rate = (successful_hunts / len(hunt_reports) * 100) if hunt_reports else 0
            st.metric("Success Rate", f"{success_rate:.0f}%")
        
        st.markdown("---")
        st.subheader("Recent Visits")
        
        recent_bookings = sorted(confirmed_bookings, key=lambda b: b.date, reverse=True)[:10]
        
        if recent_bookings:
            for booking in recent_bookings:
                hunter = get_user_by_id(booking.hunter_id)
                session = next((s for s in completed_hunts if s.booking_id == booking.id), None)
                
                if session and session.status == 'completed':
                    report = get_hunt_report_by_session(session.id)
                    if report:
                        success_icon = "✅" if report.animals_harvested > 0 else "❌"
                        st.markdown(f"**{booking.date}** - {hunter.name if hunter and hunter.id == user.id else 'Member'} {success_icon} ({report.animals_harvested} animals)")
                    else:
                        st.markdown(f"**{booking.date}** - {hunter.name if hunter and hunter.id == user.id else 'Member'} (No report)")
                else:
                    st.markdown(f"**{booking.date}** - {hunter.name if hunter and hunter.id == user.id else 'Member'} (Upcoming)")
        else:
            st.info("No booking history yet for this field")
    
    with tab3:
        st.header("🗺️ Location & Getting There")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Map")
            m = folium.Map(location=[field.lat, field.lon], zoom_start=13)
            folium.Marker(
                [field.lat, field.lon],
                popup=field.name,
                tooltip=field.name,
                icon=folium.Icon(color='green', icon='tree', prefix='fa')
            ).add_to(m)
            st_folium(m, width=700, height=400)
        
        with col2:
            st.subheader("Quick Info")
            st.markdown(f"**Location:** {field.location}")
            st.markdown(f"**Type:** {field.type}")
            st.markdown(f"**Season:** {field.season}")
            st.markdown(f"**GPS:** {field.lat}, {field.lon}")
            
            st.markdown("---")
            st.subheader("📞 Guide Contact")
            if field.guide_name:
                st.markdown(f"**Guide:** {field.guide_name}")
            if field.guide_contact:
                st.markdown(f"**Contact:** {field.guide_contact}")
        
        st.markdown("---")
        
        if field.species_allowed:
            st.subheader("🎯 Species Allowed")
            cols = st.columns(2)
            for i, species in enumerate(field.species_allowed):
                with cols[i % 2]:
                    st.markdown(f"✓ {species}")
        
        st.markdown("---")
        
        if field.rules_info:
            st.subheader("📋 Rules & Information")
            st.markdown(field.rules_info)
    
    with tab4:
        st.header("⭐ Hunter Reviews")
        
        hunt_reports = get_hunt_reports_by_field(field.id)
        hunt_reports_with_rating = [r for r in hunt_reports if r.review_rating]
        
        if hunt_reports_with_rating:
            avg_rating = sum(r.review_rating for r in hunt_reports_with_rating) / len(hunt_reports_with_rating)
            
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Average Rating", f"{'⭐' * int(avg_rating)} ({avg_rating:.1f}/5)")
                st.metric("Total Reviews", len(hunt_reports_with_rating))
            
            st.markdown("---")
            st.subheader("Recent Reviews")
            
            for report in sorted(hunt_reports_with_rating, key=lambda r: r.created_at, reverse=True)[:10]:
                hunter = get_user_by_id(report.hunter_id)
                stars = "⭐" * report.review_rating
                
                with st.expander(f"{stars} - {hunter.name if hunter else 'Hunter'} ({report.created_at.strftime('%Y-%m-%d')})", expanded=True):
                    st.markdown("✅ **Verified Hunt** - Review from actual hunt session")
                    st.markdown("---")
                    if report.review_text:
                        st.markdown(f"*\"{report.review_text}\"*")
                    
                    if report.animals_harvested > 0:
                        st.success(f"✅ Successful hunt - {report.animals_harvested} animals harvested")
                    else:
                        st.info("❌ No harvest on this visit")
        else:
            st.info("No reviews yet")
    
    with tab5:
        st.header("💰 Price List")
        st.markdown("Additional costs and services available")
        
        if field.price_list and len(field.price_list) > 0:
            st.markdown("---")
            
            # Display price list items as a table
            for item_data in field.price_list:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{item_data.get('item', 'Unknown')}**")
                with col2:
                    st.markdown(f"£{item_data.get('cost', 0)}")
            
            st.markdown("---")
            
            # Calculate and show total
            total = sum(item.get('cost', 0) for item in field.price_list)
            st.markdown(f"### Total Additional Services: £{total}")
        else:
            st.info("Price list not available")

def hunter_dashboard(user: User):
    # Check if viewing DIY field details
    if hasattr(st.session_state, 'viewing_diy_field_id') and st.session_state.viewing_diy_field_id:
        field = get_field_by_id(st.session_state.viewing_diy_field_id)
        if field:
            show_diy_field_details(field, user)
            return
    
    # Check if viewing subsidised field details
    if hasattr(st.session_state, 'viewing_subsidised_field_id') and st.session_state.viewing_subsidised_field_id:
        field = get_field_by_id(st.session_state.viewing_subsidised_field_id)
        if field:
            show_subsidised_field_details(field, user)
            return
    
    st.title("🎯 Hunter Dashboard")
    
    tab1, tab2, tab3, tab_tags, tab4, tab5, tab_forum = st.tabs(["Browse Land", "My Bookings", "My Active Hunts", "My Animal Tags", "Profile", "Notifications", "Forum"])
    
    with tab1:
        st.header("Browse Land")
        
        # Add CSS for larger carousel images
        st.markdown("""
            <style>
            [data-testid="stImage"] img {
                min-height: 350px !important;
                object-fit: cover !important;
                border-radius: 8px !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔍 Search Filters")
        
        search_mode = st.radio("Search by:", ["All Fields", "Near Me"], horizontal=True)
        
        st.markdown("---")
        
        if search_mode == "Near Me":
            col1, col2 = st.columns(2)
            with col1:
                location_input = st.text_input("Enter city or region", placeholder="e.g., London, Edinburgh, Yorkshire", key="location_search_input")
            with col2:
                radius = st.slider("Search radius (miles)", 10, 200, 100, step=10, key="search_radius_slider")
            
            fields_with_distance = []
            all_fields = []
            
            if location_input:
                coords = geocode_uk_location(location_input)
                if coords:
                    lat, lon = coords
                    st.success(f"📍 Searching within {radius} miles of {location_input.title()}")
                    fields_with_distance = get_fields_within_radius(lat, lon, radius)
                    all_fields = [field for field, distance in fields_with_distance]
                else:
                    st.warning(f"Location '{location_input}' not found. Try: London, Edinburgh, Manchester, Scottish Highlands, Yorkshire, etc.")
                    all_fields = []
            else:
                st.info("Enter a location above to find nearby fields")
                all_fields = []
        else:
            all_fields = get_all_fields()
            fields_with_distance = []
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            search_type = st.selectbox("Hunting Type", ["All Types", "Red Deer Stalking", "Driven Grouse", "Pheasant & Partridge", "Duck & Goose"])
        with col2:
            search_location = st.selectbox("Location", ["All Locations", "Scottish Highlands", "Cairngorms National Park", "North Yorkshire", "Cumbria"])
        with col3:
            max_price = st.slider("Max Price (£)", 0, 1000, 1000)
        with col4:
            search_date = st.date_input("Preferred Date", datetime.now())
        
        st.markdown("#### 🎯 Advanced Filters")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            all_species = set()
            for field in all_fields:
                if field.field_type == 'subsidised' and field.species_allowed:
                    all_species.update(field.species_allowed)
                elif field.quarry_species:
                    all_species.update([q['species'] for q in field.quarry_species])
            species_list = ["All Species"] + sorted(list(all_species))
            search_species = st.selectbox("Species", species_list)
        
        with col2:
            field_type_filter = st.selectbox("Field Type", ["All Types", "DIY-Leased", "Subsidised"])
        
        with col3:
            opportunity_filter = st.selectbox("Availability", [
                "All Fields",
                "High Quota Available (>50%)",
                "Limited Quota (20-50%)",
                "Low Quota (<20%)",
                "Most Popular (by visits)",
                "Hidden Gems (least hunted)"
            ])
        
        filtered_fields = all_fields
        if search_type != "All Types":
            filtered_fields = [f for f in filtered_fields if f.type == search_type]
        if search_location != "All Locations" and search_mode != "Near Me":
            filtered_fields = [f for f in filtered_fields if f.location == search_location]
        filtered_fields = [f for f in filtered_fields if f.price_per_day <= max_price]
        
        if search_species != "All Species":
            def has_species(field):
                if field.field_type == 'subsidised' and field.species_allowed:
                    return search_species in field.species_allowed
                elif field.quarry_species:
                    return any(q['species'] == search_species for q in field.quarry_species)
                return False
            filtered_fields = [f for f in filtered_fields if has_species(f)]
        
        if field_type_filter == "DIY-Leased":
            filtered_fields = [f for f in filtered_fields if f.field_type == 'diy-leased']
        elif field_type_filter == "Subsidised":
            filtered_fields = [f for f in filtered_fields if f.field_type == 'subsidised']
        
        if opportunity_filter == "High Quota Available (>50%)":
            def has_high_quota(field):
                if field.field_type != 'diy-leased':
                    return True
                total_quota = get_total_quota(field)
                remaining_quota = get_total_quota_remaining(field)
                if total_quota and total_quota > 0:
                    return (remaining_quota / total_quota) > 0.5
                return False
            filtered_fields = [f for f in filtered_fields if has_high_quota(f)]
        
        elif opportunity_filter == "Limited Quota (20-50%)":
            def has_limited_quota(field):
                if field.field_type != 'diy-leased':
                    return False
                total_quota = get_total_quota(field)
                remaining_quota = get_total_quota_remaining(field)
                if total_quota and total_quota > 0:
                    percentage = remaining_quota / total_quota
                    return 0.2 <= percentage <= 0.5
                return False
            filtered_fields = [f for f in filtered_fields if has_limited_quota(f)]
        
        elif opportunity_filter == "Low Quota (<20%)":
            def has_low_quota(field):
                if field.field_type != 'diy-leased':
                    return False
                total_quota = get_total_quota(field)
                remaining_quota = get_total_quota_remaining(field)
                if total_quota and total_quota > 0:
                    return (remaining_quota / total_quota) < 0.2
                return False
            filtered_fields = [f for f in filtered_fields if has_low_quota(f)]
        
        elif opportunity_filter == "Most Popular (by visits)":
            all_bookings = get_all_bookings()
            field_visit_counts = {}
            for booking in all_bookings:
                if booking.status == 'confirmed':
                    field_visit_counts[booking.field_id] = field_visit_counts.get(booking.field_id, 0) + 1
            
            filtered_fields = sorted(filtered_fields, key=lambda f: field_visit_counts.get(f.id, 0), reverse=True)
        
        elif opportunity_filter == "Hidden Gems (least hunted)":
            all_bookings = get_all_bookings()
            field_visit_counts = {}
            for booking in all_bookings:
                if booking.status == 'confirmed':
                    field_visit_counts[booking.field_id] = field_visit_counts.get(booking.field_id, 0) + 1
            
            filtered_fields = sorted(filtered_fields, key=lambda f: field_visit_counts.get(f.id, 0))
        
        # Apply role-based filtering
        if user.role in ['shooting_member', 'hunter']:
            # UK members see DIY + Subsidised only
            filtered_fields = [f for f in filtered_fields if f.field_type in ['diy-leased', 'subsidised']]
        elif user.role == 'international_hunter':
            # International hunters see Subsidised + International only
            filtered_fields = [f for f in filtered_fields if f.field_type in ['subsidised', 'international']]
        # Admin and other roles (guide_member, landowner_member, outfitter, admin) see all fields
        
        if search_mode == "Near Me" and fields_with_distance:
            filtered_with_distance = [(f, d) for f, d in fields_with_distance if f in filtered_fields]
        else:
            filtered_with_distance = []
        
        st.markdown("---")
        
        if filtered_fields:
            m = folium.Map(location=[55.3781, -3.4360], zoom_start=6)
            for field in filtered_fields:
                folium.Marker(
                    [field.lat, field.lon],
                    popup=f"{field.name}<br>£{field.price_per_day}/day",
                    tooltip=field.name,
                    icon=folium.Icon(color='green', icon='tree', prefix='fa')
                ).add_to(m)
            
            st_folium(m, width=1200, height=400)
            
            st.markdown("---")
            
            # Inject CSS for Browse Land carousel images
            st.markdown("""
                <style>
                .field-carousel-container {
                    width: 100%;
                    height: 280px;
                    overflow: hidden;
                    border-radius: 10px;
                    background: #f0f0f0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin-bottom: 10px;
                }
                .field-carousel-container img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    object-position: center;
                }
                </style>
            """, unsafe_allow_html=True)
            
            fields_to_display = []
            if search_mode == "Near Me" and filtered_with_distance:
                fields_to_display = [(field, distance) for field, distance in filtered_with_distance]
            else:
                fields_to_display = [(field, None) for field in filtered_fields]
            
            for i in range(0, len(fields_to_display), 2):
                cols = st.columns(2)
                for col_idx, col in enumerate(cols):
                    if i + col_idx < len(fields_to_display):
                        field, distance = fields_to_display[i + col_idx]
                        
                        with col:
                            with st.container():
                                # Picture carousel implementation
                                carousel_key = f"carousel_{field.id}"
                                if carousel_key not in st.session_state:
                                    st.session_state[carousel_key] = 0
                                
                                # Use image_gallery from database, fallback to single image
                                if field.image_gallery and len(field.image_gallery) > 0:
                                    field_images = field.image_gallery
                                elif field.image:
                                    field_images = [field.image]
                                else:
                                    field_images = []
                                
                                if field_images:
                                    # Normalize index to valid range
                                    current_idx = st.session_state[carousel_key] % len(field_images)
                                    
                                    # Display current image with wrapper for consistent sizing
                                    st.markdown(f"""
                                        <div class="field-carousel-container">
                                            <img src="{field_images[current_idx]}" alt="{field.name}">
                                        </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Carousel controls (only show if multiple images)
                                    if len(field_images) > 1:
                                        col_prev, col_indicator, col_next = st.columns([1, 2, 1])
                                        with col_prev:
                                            if st.button("◀", key=f"prev_{field.id}"):
                                                new_idx = (st.session_state[carousel_key] - 1) % len(field_images)
                                                st.session_state[carousel_key] = new_idx
                                                st.rerun()
                                        with col_indicator:
                                            st.caption(f"{current_idx + 1} / {len(field_images)}", help="Click arrows to view more photos")
                                        with col_next:
                                            if st.button("▶", key=f"next_{field.id}"):
                                                new_idx = (st.session_state[carousel_key] + 1) % len(field_images)
                                                st.session_state[carousel_key] = new_idx
                                                st.rerun()
                                else:
                                    # Fallback placeholder
                                    st.markdown(f"<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 150px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: white; font-size: 48px;'>🏞️</div>", unsafe_allow_html=True)
                                
                                field_type_badge = "🌟 SUBSIDISED" if field.field_type == 'subsidised' else "🎯 DIY"
                                st.markdown(f"**{field_type_badge}**")
                                
                                st.markdown(f"### {field.name}")
                                st.markdown(f"📍 {field.location}")
                                if distance:
                                    st.markdown(f"🚗 {distance:.1f} miles away")
                                
                                if field.field_type == 'subsidised':
                                    if field.outing_fee:
                                        st.markdown(f"💰 **£{field.outing_fee}**")
                                    else:
                                        st.markdown(f"💰 **£{field.price_per_day}**")
                                else:
                                    st.markdown("💰 **FREE**")
                                
                                quota_exhausted = is_quota_exhausted(field) if field.field_type != 'subsidised' else False
                                
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    st.caption(f"👥 {field.capacity}")
                                with col_b:
                                    st.caption(f"📅 {field.season or 'All Year'}")
                                
                                if quota_exhausted:
                                    st.warning("⚠️ Quota exhausted", icon="⚠️")
                                
                                if field.field_type == 'subsidised':
                                    if st.button("View Details", key=f"view_subsidised_{field.id}", use_container_width=True, type="primary"):
                                        st.session_state.viewing_subsidised_field_id = field.id
                                        st.rerun()
                                else:
                                    if not quota_exhausted:
                                        if st.button("View Details", key=f"view_diy_{field.id}", use_container_width=True, type="primary"):
                                            st.session_state.viewing_diy_field_id = field.id
                                            st.rerun()
                                    else:
                                        st.button("View Details", key=f"view_diy_{field.id}", use_container_width=True, disabled=True)
                                
                                st.markdown("---")
            
            if 'booking_step' in st.session_state and st.session_state.booking_step == 'details':
                show_booking_modal(st.session_state.selected_field_id, user.id)
    
    with tab2:
        st.header("My Bookings")
        
        user_bookings = get_bookings_by_hunter(user.id)
        
        if user_bookings:
            for booking in user_bookings:
                field = get_field_by_id(booking.field_id)
                status_color = {
                    'confirmed': '🟢',
                    'pending': '🟡',
                    'cancelled': '🔴',
                    'rejected': '🔴'
                }
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        st.markdown(f"**{field.name}**")
                        st.markdown(f"{field.location}")
                    with col2:
                        st.markdown(f"**Date:** {booking.date}")
                        st.markdown(f"**Hunters:** {booking.num_hunters}")
                    with col3:
                        st.markdown(f"**Total:** £{booking.total_price}")
                        st.markdown(f"**Status:** {status_color.get(booking.status, '⚪')} {booking.status.title()}")
                    with col4:
                        if booking.status == 'confirmed':
                            if st.button("Cancel", key=f"cancel_{booking.id}"):
                                update_booking_status(booking.id, 'cancelled')
                                
                                hunter = get_user_by_id(booking.hunter_id)
                                if field and hunter:
                                    outfitter = get_user_by_id(field.outfitter_id)
                                    if outfitter:
                                        email_service.send_booking_cancelled_to_outfitter(hunter, booking, field, outfitter)
                                
                                st.rerun()
                        elif booking.status == 'pending':
                            st.caption("Awaiting approval")
                        elif booking.status == 'rejected':
                            st.caption("Refund processed")
                    st.markdown("---")
        else:
            st.info("No bookings yet. Browse fields to make your first booking!")
    
    with tab3:
        st.header("🎯 My Active Hunts Today")
        st.caption(f"Today's Date: {datetime.now().strftime('%d %B %Y')}")
        
        todays_bookings = get_todays_bookings_for_hunter(user.id)
        
        if todays_bookings:
            for booking in todays_bookings:
                field = get_field_by_id(booking.field_id)
                hunt_session = get_hunt_session_by_booking(booking.id)
                
                if not hunt_session:
                    hunt_session = create_hunt_session(booking.id, user.id, field.id)
                
                with st.expander(f"🏞️ {field.name} - {field.location}", expanded=True):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"**Field:** {field.name}")
                        st.markdown(f"**Location:** {field.location}")
                        st.markdown(f"**Type:** {field.type}")
                        st.markdown(f"**Hunters:** {booking.num_hunters}")
                        
                        if field.field_type == 'diy-leased':
                            if field.quarry_species:
                                st.markdown("**Quotas:**")
                                for q in field.quarry_species:
                                    st.markdown(f"- {q['species']}: {q.get('remaining', 0)} / {q.get('total', 0)}")
                            elif field.quarry_type:
                                st.markdown(f"**Quarry Type:** {field.quarry_type}")
                                if field.quarry_remaining is not None:
                                    st.markdown(f"**Quota Remaining:** {field.quarry_remaining} / {field.quarry_total}")
                        
                        if hunt_session.status == 'active':
                            start_time = hunt_session.start_time.strftime('%H:%M') if hunt_session.start_time else "Unknown"
                            st.success(f"✅ Hunt started at {start_time}")
                    
                    with col2:
                        if hunt_session.status == 'not_started':
                            if st.button("🚀 Start Day", key=f"start_{hunt_session.id}", use_container_width=True):
                                start_hunt_session(hunt_session.id)
                                
                                landowner = get_user_by_id(field.outfitter_id)
                                if landowner:
                                    email_service.send_hunt_started_to_landowner(user, field, booking, landowner)
                                email_service.send_hunt_started_to_admin(user, field, booking)
                                
                                st.success("Hunt session started! Notifications sent to admin and land owner.")
                                st.rerun()
                        
                        elif hunt_session.status == 'active':
                            if st.button("🏁 Finish Hunt", key=f"finish_{hunt_session.id}", use_container_width=True):
                                st.session_state.finishing_hunt = hunt_session.id
                                st.session_state.finishing_field = field.id
                                st.rerun()
                        
                        elif hunt_session.status == 'completed':
                            st.info("✓ Hunt completed")
                            
                            existing_report = get_hunt_report_by_session(hunt_session.id)
                            if existing_report and existing_report.review_rating:
                                if st.button("✏️ Edit Review", key=f"edit_review_{hunt_session.id}", use_container_width=True):
                                    st.session_state[f'editing_review_{hunt_session.id}'] = True
                                    st.rerun()
                    
                    if hunt_session.status == 'completed':
                        existing_report = get_hunt_report_by_session(hunt_session.id)
                        if existing_report and existing_report.review_rating:
                            st.markdown("---")
                            st.subheader("📝 Your Review")
                            st.markdown(f"**Rating:** {'⭐' * existing_report.review_rating}")
                            if existing_report.review_text:
                                st.markdown(f"**Review:** *\"{existing_report.review_text}\"*")
                            
                            if st.session_state.get(f'editing_review_{hunt_session.id}', False):
                                st.markdown("---")
                                st.markdown("### ✏️ Edit Your Review")
                                with st.form(f"edit_review_form_{hunt_session.id}"):
                                    new_rating = st.slider("Update Rating", 1, 5, existing_report.review_rating, key=f"edit_rating_{hunt_session.id}")
                                    new_text = st.text_area("Update Review", value=existing_report.review_text or "", key=f"edit_text_{hunt_session.id}")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if st.form_submit_button("💾 Save Changes"):
                                            update_hunt_report(existing_report.id, review_rating=new_rating, review_text=new_text)
                                            st.success("Review updated!")
                                            st.session_state[f'editing_review_{hunt_session.id}'] = False
                                            st.rerun()
                                    with col2:
                                        if st.form_submit_button("❌ Cancel"):
                                            st.session_state[f'editing_review_{hunt_session.id}'] = False
                                            st.rerun()
                
                if st.session_state.get('finishing_hunt') == hunt_session.id:
                    show_hunt_report_form(hunt_session, field, user)
        else:
            st.info("No active hunts today. Check your bookings for upcoming hunts.")
    
    with tab_tags:
        st.header("🏷️ My Animal Tags")
        st.markdown("Tag harvested animals with QR codes for traceability")
        
        user_sessions = get_hunt_sessions_by_hunter(user.id)
        completed_sessions = [s for s in user_sessions if s.status == 'completed']
        
        if completed_sessions:
            hunt_options = {f"{s.id} - {get_field_by_id(s.field_id).name if get_field_by_id(s.field_id) else 'Unknown'} ({s.start_time.strftime('%Y-%m-%d') if s.start_time else 'Date unknown'})": s for s in completed_sessions}
            selected_hunt_display = st.selectbox("Select Hunt to Tag Animals", list(hunt_options.keys()))
            selected_session = hunt_options[selected_hunt_display]
            
            hunt_report = get_hunt_report_by_session(selected_session.id)
            
            if hunt_report:
                existing_tags = get_animal_tags_by_hunt_report(hunt_report.id)
                
                if existing_tags:
                    st.subheader("📋 Existing Tags")
                    for tag in existing_tags:
                        with st.expander(f"🏷️ Tag: {tag.tag_number[:8]}... - {tag.species}"):
                            col1, col2 = st.columns([1, 2])
                            
                            with col1:
                                if tag.qr_code_path and os.path.exists(tag.qr_code_path):
                                    st.image(tag.qr_code_path, caption="QR Code", width=200)
                                    
                                    with open(tag.qr_code_path, "rb") as f:
                                        st.download_button(
                                            "📥 Download QR Code",
                                            f,
                                            file_name=f"animal_tag_{tag.tag_number[:8]}.png",
                                            mime="image/png",
                                            key=f"download_qr_{tag.id}"
                                        )
                            
                            with col2:
                                st.markdown(f"**Species:** {tag.species}")
                                st.markdown(f"**Condition:** {tag.condition}")
                                if tag.animal_tag:
                                    st.markdown(f"**Physical Tag:** {tag.animal_tag}")
                                if tag.disease_type:
                                    st.markdown(f"**Disease:** {tag.disease_type}")
                                if tag.notes:
                                    st.markdown(f"**Notes:** {tag.notes}")
                                st.markdown(f"**Created:** {tag.created_at.strftime('%Y-%m-%d %H:%M')}")
                                
                                if tag.photo_path and os.path.exists(tag.photo_path):
                                    st.image(tag.photo_path, caption="Animal Photo", use_column_width=True)
                    
                    st.markdown("---")
                
                st.subheader("➕ Add New Animal Tag")
                
                if hunt_report.animals_harvested and hunt_report.animals_harvested > 0:
                    with st.form(f"add_tag_form_{selected_session.id}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            tag_species = st.text_input("Species*", placeholder="e.g., Red Deer, Roe Deer")
                            tag_condition = st.selectbox("Condition*", ["Excellent", "Good", "Fair", "Diseased"])
                            physical_tag = st.text_input("Physical Tag Number (optional)", placeholder="e.g., UK123456")
                        
                        with col2:
                            disease_type = st.text_input("Disease Type (if applicable)", placeholder="e.g., CWD, TB")
                            tag_notes = st.text_area("Notes (optional)", placeholder="Additional information...")
                        
                        st.markdown("---")
                        st.markdown("**Animal Photo**")
                        
                        photo_option = st.radio("Photo Source", ["Take Photo", "Upload Photo"], key=f"photo_option_{selected_session.id}")
                        
                        photo_bytes = None
                        if photo_option == "Take Photo":
                            camera_photo = st.camera_input("Take a photo of the animal")
                            if camera_photo:
                                photo_bytes = camera_photo.getvalue()
                        else:
                            uploaded_photo = st.file_uploader("Upload photo", type=['jpg', 'jpeg', 'png'], key=f"upload_{selected_session.id}")
                            if uploaded_photo:
                                photo_bytes = uploaded_photo.getvalue()
                        
                        submitted = st.form_submit_button("🏷️ Create Animal Tag", type="primary")
                        
                        if submitted:
                            if not tag_species:
                                st.error("Please enter species")
                            elif not photo_bytes:
                                st.error("Please provide an animal photo")
                            else:
                                new_tag = create_animal_tag(
                                    hunt_report_id=hunt_report.id,
                                    hunter_id=user.id,
                                    field_id=selected_session.field_id,
                                    species=tag_species,
                                    condition=tag_condition,
                                    photo_bytes=photo_bytes,
                                    animal_tag=physical_tag if physical_tag else None,
                                    disease_type=disease_type if disease_type else None,
                                    notes=tag_notes if tag_notes else None
                                )
                                
                                st.success(f"✅ Animal tag created successfully!")
                                st.info(f"🏷️ Tag Number: {new_tag.tag_number}")
                                st.balloons()
                                st.rerun()
                else:
                    st.info("No animals harvested in this hunt. Complete a successful hunt first.")
            else:
                st.info("No hunt report found for this session")
        else:
            st.info("Complete a hunt first to tag animals")
    
    with tab4:
        st.header("Profile Settings")
        
        st.subheader("🎓 Hunter Certifications")
        
        if 'temp_certifications' not in st.session_state:
            st.session_state.temp_certifications = user.certifications if user.certifications else []
        
        if st.session_state.temp_certifications:
            st.markdown("**Your Certifications:**")
            cols_per_row = 3
            for i in range(0, len(st.session_state.temp_certifications), cols_per_row):
                cols = st.columns(cols_per_row)
                for col_idx, col in enumerate(cols):
                    if i + col_idx < len(st.session_state.temp_certifications):
                        cert = st.session_state.temp_certifications[i + col_idx]
                        with col:
                            cert_display = f"🎓 {cert['name']}"
                            if cert.get('date'):
                                cert_display += f" ({cert['date']})"
                            if st.button(f"❌ {cert_display}", key=f"del_cert_{i+col_idx}_{cert['name']}", use_container_width=True):
                                st.session_state.temp_certifications.pop(i + col_idx)
                                st.rerun()
            st.markdown("---")
        
        with st.expander("➕ Add New Certification", expanded=False):
            cert_options = [
                "DSC1 (Deer Stalking Certificate Level 1)",
                "DSC2 (Deer Stalking Certificate Level 2)",
                "DSC Level 1",
                "DSC Level 2",
                "Stalking Certificate",
                "Gamekeeper Training",
                "Lantra Awards",
                "Other (specify below)"
            ]
            new_cert_name = st.selectbox("Certification Type", cert_options, key="new_cert_dropdown")
            
            if new_cert_name == "Other (specify below)":
                new_cert_name = st.text_input("Specify Certification", key="new_cert_custom", placeholder="Enter certification name")
            
            new_cert_date = st.text_input("Date Achieved (MM/YYYY)", key="new_cert_date", placeholder="e.g., 06/2023")
            
            if st.button("➕ Add Certification", key="add_cert_btn", use_container_width=True, type="primary"):
                if new_cert_name and new_cert_name != "Other (specify below)":
                    st.session_state.temp_certifications.append({
                        "name": new_cert_name,
                        "date": new_cert_date
                    })
                    st.rerun()
                else:
                    st.error("Please enter a certification name")
        
        st.markdown("---")
        st.subheader("🚗 Vehicles")
        st.caption("Land owners need to know which vehicles will be on their property")
        
        if 'temp_vehicles' not in st.session_state:
            st.session_state.temp_vehicles = user.vehicles if user.vehicles else []
        
        if st.session_state.temp_vehicles:
            st.markdown("**Your Vehicles:**")
            cols_per_row = 2
            for i in range(0, len(st.session_state.temp_vehicles), cols_per_row):
                cols = st.columns(cols_per_row)
                for col_idx, col in enumerate(cols):
                    if i + col_idx < len(st.session_state.temp_vehicles):
                        vehicle = st.session_state.temp_vehicles[i + col_idx]
                        with col:
                            with st.container():
                                vehicle_display = f"🚗 **{vehicle.get('model', 'Unknown')}**"
                                st.markdown(vehicle_display)
                                st.caption(f"Reg: {vehicle.get('registration', 'N/A')}")
                                if st.button(f"❌ Remove", key=f"del_veh_{i+col_idx}_{vehicle.get('registration', i)}", use_container_width=True):
                                    st.session_state.temp_vehicles.pop(i + col_idx)
                                    st.rerun()
            st.markdown("---")
        
        with st.expander("➕ Add New Vehicle", expanded=False):
            new_veh_model = st.text_input("Vehicle Make/Model", key="new_veh_model", placeholder="e.g., Land Rover Defender, Toyota Hilux")
            new_veh_reg = st.text_input("Registration Number", key="new_veh_reg", placeholder="e.g., AB12 CDE")
            
            if st.button("➕ Add Vehicle", key="add_veh_btn", use_container_width=True, type="primary"):
                if new_veh_model and new_veh_reg:
                    st.session_state.temp_vehicles.append({
                        "model": new_veh_model,
                        "registration": new_veh_reg
                    })
                    st.rerun()
                else:
                    st.error("Please enter both vehicle model and registration number")
        
        st.markdown("---")
        
        with st.form("profile_form"):
            st.subheader("📋 Personal Information")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Name", value=user.name or "")
                email = st.text_input("Email", value=user.email, disabled=True)
            with col2:
                phone = st.text_input("Phone", value=user.phone or "")
                location = st.text_input("Location", value=user.location or "")
            
            st.markdown("---")
            st.subheader("🛡️ Insurance & Certificates")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                insurance_provider = st.text_input("Insurance Provider", value=user.insurance_provider or "", placeholder="e.g., NFU Mutual")
            with col2:
                insurance_number = st.text_input("Policy Number", value=user.insurance_number or "", placeholder="e.g., POL123456")
            with col3:
                insurance_expiry = st.text_input("Expiry Date", value=user.insurance_expiry or "", placeholder="DD/MM/YYYY")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                fac_certificate = st.text_input("FAC (Firearms Certificate)", value=user.fac_certificate or "", placeholder="FAC Number")
            with col2:
                fac_expiry = st.text_input("FAC Expiry", value=user.fac_expiry or "", placeholder="DD/MM/YYYY")
            with col3:
                st.text("")
            
            col1, col2 = st.columns(2)
            with col1:
                shotgun_certificate = st.text_input("Shotgun Certificate", value=user.shotgun_certificate or "", placeholder="Certificate Number")
            with col2:
                shotgun_expiry = st.text_input("Shotgun Cert Expiry", value=user.shotgun_expiry or "", placeholder="DD/MM/YYYY")
            
            st.markdown("---")
            st.subheader("👥 Membership Details")
            st.caption("ℹ️ Membership details are managed by administrators")
            col1, col2 = st.columns(2)
            with col1:
                membership_number = st.text_input("Membership Number", value=user.membership_number or "Not Assigned", disabled=True)
            with col2:
                membership_expiry = st.text_input("Membership Expiry", value=user.membership_expiry or "Not Set", disabled=True)
            
            st.markdown("---")
            st.subheader("🎒 Gear & Equipment (Optional)")
            st.caption("Visible to other users - helpful for sharing equipment")
            
            gear_text = user.gear if user.gear else ""
            gear_input = st.text_area("List your gear (one item per line)", value=gear_text, placeholder="e.g.,\nSwarovski binoculars 10x42\nLeica rangefinder\nStalking rifle .308")
            
            submitted = st.form_submit_button("💾 Save Profile", use_container_width=True)
            
            if submitted:
                profile_data = {
                    'name': name,
                    'phone': phone,
                    'location': location,
                    'insurance_provider': insurance_provider,
                    'insurance_number': insurance_number,
                    'insurance_expiry': insurance_expiry,
                    'fac_certificate': fac_certificate,
                    'fac_expiry': fac_expiry,
                    'shotgun_certificate': shotgun_certificate,
                    'shotgun_expiry': shotgun_expiry,
                    'certifications': st.session_state.temp_certifications,
                    'vehicles': st.session_state.temp_vehicles,
                    'gear': gear_input
                }
                
                updated_user = update_user_profile(user.id, profile_data)
                if updated_user:
                    st.success("✅ Profile updated successfully!")
                    st.session_state.user = updated_user
                    st.rerun()
                else:
                    st.error("Failed to update profile")
        
        st.markdown("---")
        st.subheader("📖 Hunting Journal Export")
        st.caption("Export your hunting records for police compliance and personal records")
        
        all_hunt_sessions = get_hunt_sessions_by_hunter(user.id)
        hunt_sessions = [session for session in all_hunt_sessions if session.status == 'completed']
        
        if hunt_sessions:
            st.info(f"You have **{len(hunt_sessions)}** completed hunt sessions")
            
            if st.button("📥 Export Hunting Journal (CSV)", use_container_width=True):
                import io
                csv_buffer = io.StringIO()
                
                csv_buffer.write("Date,Field Name,Location,Species,Quantity,Condition,Disease Type,Animal Tag,Ground Remarks\\n")
                
                for session in hunt_sessions:
                    hunt_report = get_hunt_report_by_session(session.id)
                    if hunt_report:
                        field = get_field_by_id(hunt_report.field_id)
                        booking = get_booking_by_id(session.booking_id)
                        hunt_date = booking.date if booking else "Unknown"
                        field_name = field.name if field else "Unknown"
                        field_location = field.location if field else "Unknown"
                        
                        if hunt_report.animals_detail:
                            for animal in hunt_report.animals_detail:
                                csv_buffer.write(f'"{hunt_date}","{field_name}","{field_location}",')
                                csv_buffer.write(f'"{animal.get("species", "N/A")}",1,')
                                csv_buffer.write(f'"{animal.get("condition", "N/A")}",')
                                csv_buffer.write(f'"{animal.get("disease_type", "N/A") if animal.get("disease_type") else "None"}",')
                                csv_buffer.write(f'"{animal.get("animal_tag", "N/A") if animal.get("animal_tag") else "None"}",')
                                csv_buffer.write(f'"{hunt_report.ground_remarks if hunt_report.ground_remarks else "None"}"\\n')
                        elif hunt_report.species_harvested:
                            for species_data in hunt_report.species_harvested:
                                species = species_data.get('species', species_data.get(' species', 'N/A'))
                                quantity = species_data.get('quantity', 0)
                                csv_buffer.write(f'"{hunt_date}","{field_name}","{field_location}",')
                                csv_buffer.write(f'"{species}",{quantity},"N/A","N/A","N/A",')
                                csv_buffer.write(f'"{hunt_report.ground_remarks if hunt_report.ground_remarks else "None"}"\\n')
                        else:
                            csv_buffer.write(f'"{hunt_date}","{field_name}","{field_location}","None",0,"N/A","N/A","N/A",')
                            csv_buffer.write(f'"{hunt_report.ground_remarks if hunt_report.ground_remarks else "None"}"\\n')
                
                csv_data = csv_buffer.getvalue()
                
                st.download_button(
                    label="⬇️ Download Journal CSV",
                    data=csv_data,
                    file_name=f"hunting_journal_{user.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        else:
            st.info("No completed hunts yet. Your journal will appear here after you complete your first hunt.")
    
    with tab5:
        st.header("Notifications")
        
        notifications = []
        for booking in get_bookings_by_hunter(user.id):
            if booking.status == 'confirmed':
                field = get_field_by_id(booking.field_id)
                notifications.append({
                    'type': 'success',
                    'message': f"Booking confirmed for {field.name} on {booking.date}",
                    'time': 'Today'
                })
        
        if notifications:
            for notif in notifications:
                if notif['type'] == 'success':
                    st.success(f"✓ {notif['message']} - {notif['time']}")
        else:
            st.info("No new notifications")
    
    with tab_forum:
        if 'forum_view' not in st.session_state:
            st.session_state.forum_view = 'categories'
        
        if st.session_state.forum_view == 'categories':
            st.header("💬 Member Forum")
            st.markdown("Connect with the fieldsports community - share experiences, buy/sell equipment, and get advice")
            
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("➕ Create New Post", type="primary", use_container_width=True):
                    st.session_state.forum_view = 'create_post'
                    st.rerun()
            
            st.markdown("---")
            
            categories = get_all_forum_categories()
            
            if categories:
                for category in categories:
                    posts_in_category = get_forum_posts_by_category(category.id)
                    post_count = len(posts_in_category)
                    
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        
                        with col1:
                            st.markdown(f"### {category.name}")
                            st.markdown(f"*{category.description}*")
                        
                        with col2:
                            st.markdown(f"**{post_count}** posts")
                            if st.button("Browse →", key=f"cat_{category.id}", use_container_width=True):
                                st.session_state.selected_category_id = category.id
                                st.session_state.forum_view = 'category_posts'
                                st.rerun()
                        
                        st.markdown("---")
            else:
                st.info("No forum categories available yet")
        
        elif st.session_state.forum_view == 'category_posts':
            selected_category = None
            categories = get_all_forum_categories()
            for cat in categories:
                if cat.id == st.session_state.selected_category_id:
                    selected_category = cat
                    break
            
            if selected_category:
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button("⬅️ Back", type="secondary"):
                        st.session_state.forum_view = 'categories'
                        st.rerun()
                
                st.header(f"{selected_category.name}")
                st.markdown(f"*{selected_category.description}*")
                st.markdown("---")
                
                posts = get_forum_posts_by_category(selected_category.id)
                
                if posts:
                    for post in posts:
                        post_author = get_user_by_id(post.user_id)
                        author_name = post_author.name if post_author else "Unknown"
                        
                        post_type_colors = {
                            'discussion': '🔵',
                            'for_sale': '🟢',
                            'wanted': '🟠',
                            'advice': '🟣'
                        }
                        post_type_badge = post_type_colors.get(post.post_type, '⚪')
                        post_type_label = post.post_type.replace('_', ' ').title()
                        
                        replies = get_forum_replies_by_post(post.id)
                        reply_count = len(replies)
                        
                        relative_time = format_relative_time(post.created_at)
                        
                        with st.container():
                            col1, col2, col3 = st.columns([5, 1, 1])
                            
                            with col1:
                                st.markdown(f"### {post_type_badge} {post.title}")
                                st.markdown(f"By **{author_name}** • {relative_time}")
                                
                                if post.post_type in ['for_sale', 'wanted'] and post.price:
                                    st.markdown(f"💰 **£{post.price}** {f'• 📍 {post.location}' if post.location else ''}")
                            
                            with col2:
                                st.markdown(f"👁️ {post.views} views")
                            
                            with col3:
                                st.markdown(f"💬 {reply_count} replies")
                            
                            if st.button(f"View Post →", key=f"post_{post.id}", use_container_width=True):
                                increment_post_views(post.id)
                                st.session_state.selected_post_id = post.id
                                st.session_state.forum_view = 'post_detail'
                                st.rerun()
                            
                            st.markdown("---")
                else:
                    st.info("No posts yet - be the first to post in this category!")
                    if st.button("Create First Post", type="primary"):
                        st.session_state.forum_view = 'create_post'
                        st.rerun()
        
        elif st.session_state.forum_view == 'post_detail':
            post = get_forum_post_by_id(st.session_state.selected_post_id)
            
            if post:
                col1, col2 = st.columns([1, 5])
                with col1:
                    if st.button("⬅️ Back", type="secondary"):
                        st.session_state.forum_view = 'category_posts'
                        st.rerun()
                
                post_author = get_user_by_id(post.user_id)
                author_name = post_author.name if post_author else "Unknown"
                
                post_type_colors = {
                    'discussion': '🔵 Discussion',
                    'for_sale': '🟢 For Sale',
                    'wanted': '🟠 Wanted',
                    'advice': '🟣 Advice'
                }
                post_type_display = post_type_colors.get(post.post_type, post.post_type)
                
                relative_time = format_relative_time(post.created_at)
                
                st.markdown(f"# {post.title}")
                st.markdown(f"{post_type_display}")
                st.markdown(f"Posted by **{author_name}** • {relative_time} • 👁️ {post.views} views")
                
                st.markdown("---")
                
                if post.post_type in ['for_sale', 'wanted']:
                    st.info(f"""
**Classified Listing Details:**

💰 **Price:** £{post.price if post.price else 'Contact for price'}

📍 **Location:** {post.location if post.location else 'Not specified'}

📞 **Contact:** {post.contact_info if post.contact_info else 'Use replies below'}
                    """)
                
                st.markdown(post.content)
                
                st.markdown("---")
                
                replies = get_forum_replies_by_post(post.id)
                
                st.subheader(f"💬 Replies ({len(replies)})")
                
                if replies:
                    for reply in replies:
                        reply_author = get_user_by_id(reply.user_id)
                        reply_author_name = reply_author.name if reply_author else "Unknown"
                        reply_time = format_relative_time(reply.created_at)
                        
                        with st.container():
                            st.markdown(f"**{reply_author_name}** • {reply_time}")
                            st.markdown(reply.content)
                            st.markdown("---")
                else:
                    st.info("No replies yet - be the first to reply!")
                
                st.markdown("---")
                st.subheader("💬 Add a Reply")
                
                with st.form(f"reply_form_{post.id}"):
                    reply_content = st.text_area("Your reply", placeholder="Share your thoughts...", height=150)
                    
                    submit_reply = st.form_submit_button("Post Reply", type="primary")
                    
                    if submit_reply:
                        if reply_content.strip():
                            create_forum_reply(post.id, user.id, reply_content)
                            st.success("✅ Reply posted successfully!")
                            st.rerun()
                        else:
                            st.error("Reply content cannot be empty")
            else:
                st.error("Post not found")
                if st.button("Back to Categories"):
                    st.session_state.forum_view = 'categories'
                    st.rerun()
        
        elif st.session_state.forum_view == 'create_post':
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("⬅️ Cancel", type="secondary"):
                    st.session_state.forum_view = 'categories'
                    st.rerun()
            
            st.header("✍️ Create New Post")
            st.markdown("Share your thoughts, sell equipment, or ask for advice")
            st.markdown("---")
            
            with st.form("create_post_form"):
                post_title = st.text_input("Post Title*", placeholder="e.g., Looking for stalking advice in Scottish Highlands")
                
                post_content = st.text_area("Post Content*", placeholder="Write your post here...", height=200)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    categories = get_all_forum_categories()
                    category_options = {cat.name: cat.id for cat in categories}
                    selected_category_name = st.selectbox("Category*", list(category_options.keys()))
                    selected_category_id = category_options[selected_category_name]
                
                with col2:
                    post_type = st.selectbox("Post Type*", ["Discussion", "For Sale", "Wanted", "Advice"])
                    post_type_value = post_type.lower().replace(' ', '_')
                
                price = None
                location = None
                contact_info = None
                
                if post_type in ["For Sale", "Wanted"]:
                    st.markdown("---")
                    st.markdown("**Classified Listing Details** (Optional)")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        price_input = st.number_input("Price (£)", min_value=0.0, step=10.0, value=0.0)
                        price = price_input if price_input > 0 else None
                    
                    with col2:
                        location = st.text_input("Location", placeholder="e.g., Edinburgh, Scotland")
                    
                    with col3:
                        contact_info = st.text_input("Contact Info", placeholder="Phone or email")
                
                st.markdown("---")
                
                submit_post = st.form_submit_button("📝 Create Post", type="primary", use_container_width=True)
                
                if submit_post:
                    if not post_title.strip():
                        st.error("Post title is required")
                    elif not post_content.strip():
                        st.error("Post content is required")
                    else:
                        create_forum_post(
                            category_id=selected_category_id,
                            user_id=user.id,
                            title=post_title,
                            content=post_content,
                            post_type=post_type_value,
                            price=price,
                            location=location if location else None,
                            contact_info=contact_info if contact_info else None,
                            image_url=None
                        )
                        
                        st.success("✅ Post created successfully!")
                        st.session_state.forum_view = 'categories'
                        st.rerun()

def show_hunt_report_form(hunt_session, field, user):
    """Display hunt report form with detailed animal tracking"""
    st.markdown("---")
    st.markdown("## 📝 End of Hunt Report")
    st.markdown(f"**Field:** {field.name}")
    
    UK_QUARRY_DISEASES = {
        "Deer": ["Chronic Wasting Disease (CWD)", "Tuberculosis (TB)", "Foot and Mouth Disease", 
                 "Bluetongue", "Mange", "Liver Fluke", "Lungworm", "Deer Wasting Syndrome"],
        "Game Birds": ["Avian Influenza", "Newcastle Disease", "Mycoplasma", "Coccidiosis", 
                       "Blackhead", "Gapeworm", "Trichomoniasis"],
        "Other": ["Mange", "Myxomatosis", "Rabbit Haemorrhagic Disease", "Sarcoptic Mange", 
                  "Toxoplasmosis", "Leptospirosis"]
    }
    
    with st.form("hunt_report_form"):
        st.subheader("1️⃣ Animals Harvested")
        animals_shot = st.radio("Did you harvest any animals?", ["Yes", "No"], horizontal=True, key="animals_shot")
        
        animals_detail = []
        species_harvested = []
        total_animals = 0
        
        if animals_shot == "Yes":
            if field.field_type == 'subsidised' and field.species_allowed:
                species_options = field.species_allowed
            elif field.field_type == 'diy-leased':
                if field.quarry_species:
                    species_options = [q['species'] for q in field.quarry_species]
                elif field.quarry_type:
                    species_options = [field.quarry_type]
                else:
                    species_options = ["Roe Deer", "Red Deer", "Fox", "Hare", "Pheasant", "Grouse", "Duck"]
            else:
                species_options = ["Roe Deer", "Red Deer", "Fox", "Hare", "Pheasant", "Grouse", "Duck"]
            
            num_animals = st.number_input("How many animals harvested?", min_value=1, max_value=20, value=1, 
                                         help="Total number of individual animals")
            
            for i in range(int(num_animals)):
                st.markdown(f"### Animal #{i+1}")
                col1, col2 = st.columns(2)
                
                with col1:
                    animal_species = st.selectbox(f"Species", species_options, key=f"animal_species_{i}")
                    condition = st.selectbox("Condition", 
                                           ["Excellent", "Good", "Bad", "Diseased"], 
                                           key=f"condition_{i}",
                                           help="Physical condition of the animal")
                
                with col2:
                    animal_tag = st.text_input("Animal Tag (Optional)", 
                                              placeholder="e.g., TAG12345 or QR code", 
                                              key=f"tag_{i}",
                                              help="Future feature: QR code tag number")
                    
                    disease_type = None
                    if condition == "Diseased":
                        disease_category = "Deer" if "Deer" in animal_species else "Game Birds" if animal_species in ["Pheasant", "Grouse", "Duck"] else "Other"
                        disease_options = UK_QUARRY_DISEASES.get(disease_category, UK_QUARRY_DISEASES["Other"])
                        disease_type = st.selectbox("Disease Type", disease_options, key=f"disease_{i}")
                
                animals_detail.append({
                    "species": animal_species,
                    "condition": condition,
                    "disease_type": disease_type,
                    "animal_tag": animal_tag if animal_tag else None
                })
                
                total_animals += 1
            
            species_count = {}
            for animal in animals_detail:
                species = animal['species']
                species_count[species] = species_count.get(species, 0) + 1
            
            for species, count in species_count.items():
                species_harvested.append({"species": species, "quantity": count})
            
            st.info(f"**Total animals harvested: {total_animals}**")
        
        st.markdown("---")
        st.subheader("2️⃣ Ground Remarks?")
        ground_remarks_yn = st.radio("Would you like to leave remarks for the syndicate manager?", ["Yes", "No"], horizontal=True, key="remarks_yn")
        
        ground_remarks = ""
        if ground_remarks_yn == "Yes":
            ground_remarks = st.text_area("Ground Remarks", placeholder="Enter feedback about the ground conditions, facilities, etc.", key="remarks_text")
        
        st.markdown("---")
        st.subheader("3️⃣ Leave a Review?")
        leave_review = st.radio("Would you like to leave a public review?", ["Yes", "No"], horizontal=True, key="review_yn")
        
        review_rating = 0
        review_text = ""
        if leave_review == "Yes":
            review_rating = st.slider("Rating", 1, 5, 5, help="This will appear on the ground card")
            review_text = st.text_area("Review", placeholder="Share your experience with other hunters...", key="review_text")
        
        st.markdown("---")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            submit = st.form_submit_button("💾 Save and Close", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("Cancel", use_container_width=True)
        
        if cancel:
            del st.session_state.finishing_hunt
            del st.session_state.finishing_field
            st.rerun()
        
        if submit:
            weather = st.session_state.get('weather', 'Good')
            time_spent = 8.0
            
            report_data = {
                'animals_harvested': total_animals,
                'species_harvested': species_harvested,
                'animals_detail': animals_detail,
                'weather_conditions': weather,
                'time_spent_hours': time_spent,
                'notes': '',
                'ground_remarks': ground_remarks,
                'review_rating': review_rating if leave_review == "Yes" else None,
                'review_text': review_text if leave_review == "Yes" else '',
                'success': animals_shot == "Yes"
            }
            
            create_hunt_report(hunt_session.id, field.id, user.id, report_data)
            end_hunt_session(hunt_session.id)
            
            del st.session_state.finishing_hunt
            del st.session_state.finishing_field
            
            st.success("✅ Hunt report submitted successfully!")
            if field.field_type == 'diy-leased' and total_animals > 0:
                st.info(f"📊 Quota updated: {total_animals} animals deducted from remaining quota")
            st.rerun()

def show_booking_modal(field_id: int, hunter_id: int):
    field = get_field_by_id(field_id)
    
    st.markdown("---")
    st.markdown(f"## Booking: {field.name}")
    
    col1, col2 = st.columns(2)
    with col1:
        booking_date = st.date_input("Select Date", min_value=datetime.now())
        num_hunters = st.number_input("Number of Hunters", min_value=1, max_value=field.capacity, value=1)
    
    with col2:
        st.markdown(f"**Price per day:** £{field.price_per_day}")
        total_price = field.price_per_day * num_hunters
        st.markdown(f"**Total:** £{total_price}")
    
    date_str = booking_date.strftime("%Y-%m-%d")
    available, message = check_availability(field_id, date_str, num_hunters)
    if available:
        st.success(f"✓ {message}")
    else:
        st.error(f"✗ {message}")
    
    st.markdown("### Payment Details")
    st.info("💳 This is a demo payment processor. For testing, use any 16-digit card number.")
    
    col1, col2 = st.columns(2)
    with col1:
        card_number = st.text_input("Card Number", placeholder="4242 4242 4242 4242")
        card_expiry = st.text_input("Expiry (MM/YY)", placeholder="12/25")
    with col2:
        card_name = st.text_input("Cardholder Name", placeholder="John Smith")
        card_cvv = st.text_input("CVV", placeholder="123", type="password")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Complete Booking", type="primary", disabled=not available):
            if not available:
                st.error("Cannot complete booking: " + message)
            else:
                card_details = {
                    'card_number': card_number,
                    'expiry': card_expiry,
                    'cvv': card_cvv,
                    'name': card_name
                }
                
                success, payment_message, payment_id = simulate_stripe_payment(total_price, card_details)
                
                if success:
                    booking, booking_message = create_booking(
                        field_id=field_id,
                        hunter_id=hunter_id,
                        date=date_str,
                        num_hunters=num_hunters,
                        total_price=total_price,
                        payment_id=payment_id
                    )
                    
                    if booking:
                        hunter = get_user_by_id(hunter_id)
                        outfitter = get_user_by_id(field.outfitter_id)
                        
                        if hunter and outfitter:
                            email_service.send_booking_created_to_hunter(hunter, booking, field, outfitter)
                            email_service.send_booking_created_to_outfitter(hunter, booking, field, outfitter)
                        
                        del st.session_state.booking_step
                        del st.session_state.selected_field_id
                        st.success(f"{booking_message} Payment processed. {'Confirmed!' if booking.status == 'confirmed' else 'Awaiting outfitter confirmation.'}")
                        st.rerun()
                    else:
                        st.error(booking_message)
                else:
                    st.error(f"Payment failed: {payment_message}")
    
    with col2:
        if st.button("Cancel"):
            del st.session_state.booking_step
            del st.session_state.selected_field_id
            st.rerun()

def outfitter_dashboard(user: User):
    # Show correct title based on user role
    if user.role == 'landowner_member':
        st.title("🏞️ Landowner Dashboard")
    elif user.role == 'guide_member':
        st.title("🏞️ Guide Dashboard")
    else:
        st.title("🏞️ Outfitter Dashboard")
    
    # Add "Land Requests" tab for landowner_member role
    if user.role == 'landowner_member':
        tab1, tab2, tab3, tab4, tab5, tab_requests = st.tabs(["Overview", "My Fields", "Bookings", "Availability", "Analytics", "Land Requests"])
    else:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "My Fields", "Bookings", "Availability", "Analytics"])
    
    with tab1:
        st.header("Dashboard Overview")
        
        outfitter_fields = get_fields_by_outfitter(user.id)
        outfitter_bookings = get_bookings_for_outfitter_fields(user.id)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Fields", len(outfitter_fields))
        with col2:
            st.metric("Total Bookings", len(outfitter_bookings))
        with col3:
            confirmed_bookings = [b for b in outfitter_bookings if b.status == 'confirmed']
            st.metric("Confirmed Bookings", len(confirmed_bookings))
        with col4:
            total_revenue = sum(b.total_price for b in confirmed_bookings)
            st.metric("Total Revenue", f"£{total_revenue:,}")
        
        st.markdown("---")
        st.subheader("Recent Bookings")
        
        if outfitter_bookings:
            booking_data = []
            for b in outfitter_bookings:
                field = get_field_by_id(b.field_id)
                hunter = get_user_by_id(b.hunter_id)
                booking_data.append({
                    'id': b.id,
                    'field_name': field.name,
                    'hunter_email': hunter.email if hunter else 'Unknown',
                    'date': b.date,
                    'num_hunters': b.num_hunters,
                    'total_price': b.total_price,
                    'status': b.status
                })
            df = pd.DataFrame(booking_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No bookings yet")
    
    with tab2:
        st.header("My Fields")
        
        # Field creation removed - now handled in Admin Dashboard
        if user.role == 'landowner_member':
            st.info("ℹ️ View your assigned fields below. To request changes or add new land, use the 'Land Requests' tab.")
        elif user.role in ['guide_member', 'outfitter']:
            st.info("ℹ️ View and manage your assigned fields below. Only administrators can create new fields.")
        
        st.markdown("---")
        
        for field in get_fields_by_outfitter(user.id):
            field_type_badge = "🎯 DIY-LEASED" if field.field_type == 'diy-leased' else "🌟 SUBSIDISED"
            with st.expander(f"{field_type_badge} | {field.name} - {field.location}", expanded=False):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Type:** {field.type}")
                    st.markdown(f"**Season:** {field.season}")
                    st.markdown(f"**Description:** {field.description}")
                with col2:
                    st.markdown(f"**Price:** £{field.price_per_day}/day")
                    st.markdown(f"**Capacity:** {field.capacity}")
                
                if field.field_type == 'diy-leased' and user.role != 'landowner_member':
                    st.markdown("---")
                    st.markdown("### 📝 Edit DIY Ground Information")
                    
                    with st.form(f"edit_diy_field_{field.id}"):
                        special_mentions = st.text_area(
                            "⚠️ Special Mentions (Important Notices)",
                            value=field.special_mentions or "",
                            placeholder="Add important notices that members should see prominently (e.g., path closures, safety alerts, tide warnings)",
                            help="These will appear as a warning at the top of the DIY field detail page"
                        )
                        
                        ground_rules = st.text_area(
                            "🔰 Ground Rules",
                            value=field.ground_rules or "",
                            placeholder="List the ground rules members must follow:\n1. Rule 1\n2. Rule 2",
                            height=150
                        )
                        
                        directions = st.text_area(
                            "📍 Directions & Access",
                            value=field.directions or "",
                            placeholder="How to get there:\nFrom M6 junction...\nGPS: lat, lon",
                            height=100
                        )
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            contact_name = st.text_input("Contact Name", value=field.contact_name or "")
                        with col2:
                            contact_phone = st.text_input("Contact Phone", value=field.contact_phone or "")
                        with col3:
                            contact_email = st.text_input("Contact Email", value=field.contact_email or "")
                        
                        if st.form_submit_button("💾 Save Changes", type="primary"):
                            update_diy_field_info(
                                field.id,
                                special_mentions=special_mentions,
                                ground_rules=ground_rules,
                                directions=directions,
                                contact_name=contact_name,
                                contact_phone=contact_phone,
                                contact_email=contact_email
                            )
                            st.success("DIY ground information updated successfully!")
                            st.rerun()
        
        # Price Management Section for Guide Members
        if user.role in ['guide_member', 'outfitter']:
            st.markdown("---")
            st.markdown("---")
            st.subheader("💰 Manage Pricing")
            st.markdown("Update outing fees, full prices, and price list items for your subsidised/international fields")
            
            # Field selector
            guide_fields = get_fields_by_outfitter(user.id)
            subsidised_fields = [f for f in guide_fields if f.field_type in ['subsidised', 'international']]
            
            if subsidised_fields:
                selected_field = st.selectbox("Select Field", subsidised_fields, format_func=lambda f: f.name, key="price_management_field_selector")
                
                # Display current pricing
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Outing Fee", f"£{selected_field.outing_fee or 0}")
                with col2:
                    st.metric("Full Price", f"£{selected_field.full_price or 0}")
                
                # Edit outing fee and full price
                with st.form("edit_outing_fee"):
                    st.markdown("### Update Pricing")
                    col1, col2 = st.columns(2)
                    with col1:
                        new_outing_fee = st.number_input("Update Outing Fee (£)", value=float(selected_field.outing_fee or 0), min_value=0.0)
                    with col2:
                        new_full_price = st.number_input("Update Full Price (£)", value=float(selected_field.full_price or 0), min_value=0.0)
                    
                    if st.form_submit_button("Update Prices", type="primary"):
                        update_field_pricing(selected_field.id, outing_fee=new_outing_fee, full_price=new_full_price)
                        st.success("Prices updated!")
                        st.rerun()
                
                st.markdown("---")
                st.subheader("📋 Price List Items")
                st.markdown("Manage additional costs and services (e.g., Professional Stalker, Ghillie Service, Equipment Rental)")
                
                # Display existing items
                if selected_field.price_list and len(selected_field.price_list) > 0:
                    st.markdown("**Current Price List:**")
                    for item in selected_field.price_list:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.markdown(f"**{item.get('item', 'Unknown')}**")
                        with col2:
                            st.markdown(f"£{item.get('cost', 0)}")
                        with col3:
                            if st.button("Remove", key=f"remove_{selected_field.id}_{item.get('item', '')}"):
                                remove_price_list_item(selected_field.id, item.get('item', ''))
                                st.success(f"Removed {item.get('item', '')}")
                                st.rerun()
                else:
                    st.info("No price list items yet")
                
                # Add new item
                with st.form("add_price_item"):
                    st.subheader("Add Price List Item")
                    col1, col2 = st.columns(2)
                    with col1:
                        item_name = st.text_input("Item Name", placeholder="e.g., Professional Stalker, Ghillie Service")
                    with col2:
                        item_cost = st.number_input("Cost (£)", min_value=0.0, step=10.0)
                    
                    if st.form_submit_button("Add Item", type="primary"):
                        if item_name and item_cost > 0:
                            add_price_list_item(selected_field.id, item_name, item_cost)
                            st.success(f"Added {item_name}")
                            st.rerun()
                        else:
                            st.error("Please provide both item name and cost (greater than 0)")
            else:
                st.info("You don't have any subsidised or international fields yet")
    
    with tab3:
        st.header("Booking Management")
        
        outfitter_bookings = get_bookings_for_outfitter_fields(user.id)
        
        pending_bookings = [b for b in outfitter_bookings if b.status == 'pending']
        if pending_bookings:
            st.warning(f"⚠️ {len(pending_bookings)} booking(s) pending approval")
        
        if outfitter_bookings:
            for booking in outfitter_bookings:
                field = get_field_by_id(booking.field_id)
                hunter = get_user_by_id(booking.hunter_id)
                
                status_color = {
                    'confirmed': '🟢',
                    'pending': '🟡',
                    'cancelled': '🔴',
                    'rejected': '🔴'
                }
                
                with st.expander(f"Booking #{booking.id} - {field.name} - {status_color.get(booking.status, '⚪')} {booking.status.title()}", expanded=(booking.status == 'pending')):
                    col1, col2, col3 = st.columns([2, 2, 2])
                    
                    with col1:
                        st.markdown("### 📅 Booking Details")
                        st.markdown(f"**Field:** {field.name}")
                        st.markdown(f"**Date:** {booking.date}")
                        st.markdown(f"**Number of Hunters:** {booking.num_hunters}")
                        st.markdown(f"**Total Price:** £{booking.total_price}")
                        if booking.payment_id:
                            st.caption(f"Payment ID: {booking.payment_id[:20]}...")
                    
                    with col2:
                        st.markdown("### 👤 Hunter Information")
                        if hunter:
                            st.markdown(f"**Name:** {hunter.name or 'Not provided'}")
                            st.markdown(f"**Email:** {hunter.email or 'Not provided'}")
                            st.markdown(f"**Phone:** {hunter.phone or 'Not provided'}")
                            st.markdown(f"**Location:** {hunter.location or 'Not provided'}")
                    
                    with col3:
                        st.markdown("### 📋 Certifications & Insurance")
                        if hunter:
                            if hunter.insurance_provider:
                                st.markdown(f"**Insurance:** {hunter.insurance_provider}")
                                if hunter.insurance_number:
                                    st.caption(f"Policy: {hunter.insurance_number}")
                                if hunter.insurance_expiry:
                                    expiry = hunter.insurance_expiry
                                    st.caption(f"Expires: {expiry}")
                            else:
                                st.warning("⚠️ No insurance info provided")
                            
                            if hunter.fac_certificate:
                                st.markdown(f"**FAC Certificate:** ✓ Yes")
                            else:
                                st.caption("FAC: Not provided")
                            
                            if hunter.shotgun_certificate:
                                st.markdown(f"**Shotgun Certificate:** ✓ Yes")
                                if hunter.shotgun_expiry:
                                    st.caption(f"Expires: {hunter.shotgun_expiry}")
                            else:
                                st.caption("Shotgun: Not provided")
                    
                    st.markdown("---")
                    st.markdown("### 🚗 Vehicle Information")
                    if hunter and hunter.vehicles and len(hunter.vehicles) > 0:
                        col_v1, col_v2 = st.columns(2)
                        with col_v1:
                            for i, vehicle in enumerate(hunter.vehicles):
                                st.markdown(f"**Vehicle {i+1}:** {vehicle.get('model', 'Not specified')}")
                        with col_v2:
                            for vehicle in hunter.vehicles:
                                st.markdown(f"**Reg:** {vehicle.get('reg', 'Not specified')}")
                    else:
                        st.caption("No vehicle information provided")
                    
                    st.markdown("---")
                    st.markdown("### 🎒 Equipment & Gear")
                    if hunter and hunter.gear:
                        st.text(hunter.gear)
                    else:
                        st.caption("No equipment information provided")
                    
                    if booking.status == 'pending':
                        st.markdown("---")
                        col_action1, col_action2, col_action3 = st.columns([2, 1, 1])
                        with col_action1:
                            st.markdown("**Review and approve or reject this booking:**")
                        with col_action2:
                            if st.button("✅ Approve Booking", key=f"approve_{booking.id}", type="primary", use_container_width=True):
                                update_booking_status(booking.id, 'confirmed')
                                
                                hunter = get_user_by_id(booking.hunter_id)
                                if hunter and field:
                                    outfitter_user = user
                                    email_service.send_booking_approved_to_hunter(hunter, booking, field, outfitter_user)
                                
                                st.success("Booking approved!")
                                st.rerun()
                        with col_action3:
                            if st.button("❌ Reject Booking", key=f"reject_{booking.id}", use_container_width=True):
                                update_booking_status(booking.id, 'rejected')
                                
                                hunter = get_user_by_id(booking.hunter_id)
                                if hunter and field:
                                    outfitter_user = user
                                    email_service.send_booking_rejected_to_hunter(hunter, booking, field, outfitter_user)
                                
                                st.info("Booking rejected. Payment will be refunded.")
                                st.rerun()
        else:
            st.info("No bookings yet")
    
    with tab4:
        st.header("Availability Management")
        
        st.markdown("Manage field availability and block specific dates.")
        
        outfitter_fields = get_fields_by_outfitter(user.id)
        if outfitter_fields:
            field_options = {f.id: f.name for f in outfitter_fields}
            field_id_select = st.selectbox(
                "Select Field",
                options=list(field_options.keys()),
                format_func=lambda x: field_options[x]
            )
            
            if field_id_select:
                field = get_field_by_id(field_id_select)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Block Dates")
                    block_date = st.date_input("Select date to block", min_value=datetime.now())
                    if st.button("Block Date"):
                        date_str = block_date.strftime("%Y-%m-%d")
                        blocked_dates = field.blocked_dates or []
                        if date_str not in blocked_dates:
                            blocked_dates.append(date_str)
                            update_field_blocked_dates(field_id_select, blocked_dates)
                            st.success(f"Date {date_str} blocked successfully")
                            st.rerun()
                        else:
                            st.warning("Date is already blocked")
                
                with col2:
                    st.subheader("Blocked Dates")
                    if field.blocked_dates:
                        for blocked_date in field.blocked_dates:
                            col_a, col_b = st.columns([3, 1])
                            with col_a:
                                st.text(blocked_date)
                            with col_b:
                                if st.button("Unblock", key=f"unblock_{blocked_date}"):
                                    blocked_dates = field.blocked_dates.copy()
                                    blocked_dates.remove(blocked_date)
                                    update_field_blocked_dates(field_id_select, blocked_dates)
                                    st.success("Date unblocked")
                                    st.rerun()
                    else:
                        st.info("No blocked dates")
    
    with tab5:
        st.header("Analytics")
        
        if user.role == 'landowner_member':
            # Landowner-specific analytics
            st.markdown("### 📊 Land Performance Overview")
            
            # Get all bookings and hunt sessions for landowner's fields
            landowner_fields = get_fields_by_outfitter(user.id)
            all_bookings = []
            all_hunt_sessions = []
            all_hunt_reports = []
            
            for field in landowner_fields:
                field_bookings = get_bookings_by_field(field.id)
                all_bookings.extend(field_bookings)
                
                # Get hunt sessions for this field
                field_sessions = [s for s in get_all_hunt_sessions() if s.field_id == field.id]
                all_hunt_sessions.extend(field_sessions)
                
                # Get hunt reports for this field's sessions
                for session in field_sessions:
                    session_reports = [r for r in get_all_hunt_reports() if r.session_id == session.id]
                    all_hunt_reports.extend(session_reports)
            
            # Display key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Bookings", len(all_bookings))
            
            with col2:
                successful_visits = len([s for s in all_hunt_sessions if s.status == 'completed'])
                st.metric("Successful Visits", successful_visits)
            
            with col3:
                # Calculate total cull numbers from hunt reports
                total_cull = 0
                for report in all_hunt_reports:
                    if report.animals_detail and isinstance(report.animals_detail, list):
                        total_cull += len(report.animals_detail)
                st.metric("Total Animals Culled", total_cull)
            
            with col4:
                # Count fields with wildlife survey reports
                fields_with_surveys = len([f for f in landowner_fields if hasattr(f, 'wildlife_survey_report') and f.wildlife_survey_report])
                st.metric("Survey Reports", fields_with_surveys)
            
            st.markdown("---")
            
            # Bookings breakdown
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📅 Bookings by Status")
                if all_bookings:
                    booking_status_counts = {}
                    for b in all_bookings:
                        booking_status_counts[b.status] = booking_status_counts.get(b.status, 0) + 1
                    
                    status_df = pd.DataFrame([
                        {'Status': k.title(), 'Count': v} 
                        for k, v in booking_status_counts.items()
                    ])
                    fig = px.pie(status_df, values='Count', names='Status', title="Booking Status Distribution")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No bookings yet")
            
            with col2:
                st.subheader("🦌 Cull Numbers by Species")
                if all_hunt_reports:
                    species_counts = {}
                    for report in all_hunt_reports:
                        if report.animals_detail and isinstance(report.animals_detail, list):
                            for animal in report.animals_detail:
                                species = animal.get('species', 'Unknown')
                                species_counts[species] = species_counts.get(species, 0) + 1
                    
                    if species_counts:
                        species_df = pd.DataFrame([
                            {'Species': k, 'Count': v} 
                            for k, v in species_counts.items()
                        ])
                        fig = px.bar(species_df, x='Species', y='Count', title="Animals Culled by Species")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No cull data available")
                else:
                    st.info("No hunt reports yet")
            
            st.markdown("---")
            st.subheader("📄 Wildlife Survey Reports")
            
            # Display wildlife survey reports for each field
            if landowner_fields:
                for field in landowner_fields:
                    if hasattr(field, 'wildlife_survey_report') and field.wildlife_survey_report:
                        with st.expander(f"🏞️ {field.name} - Survey Report"):
                            st.markdown(field.wildlife_survey_report)
                    else:
                        with st.expander(f"🏞️ {field.name} - No Survey Report"):
                            st.info("No wildlife survey report uploaded yet. Admin can add this.")
            else:
                st.info("No fields available")
        
        else:
            # Original analytics for outfitters and guide members
            outfitter_bookings = get_bookings_for_outfitter_fields(user.id)
            
            if outfitter_bookings:
                booking_data = []
                for b in outfitter_bookings:
                    field = get_field_by_id(b.field_id)
                    booking_data.append({
                        'field_name': field.name,
                        'total_price': b.total_price,
                        'status': b.status
                    })
                df = pd.DataFrame(booking_data)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Revenue by Field")
                    revenue_by_field = df.groupby('field_name')['total_price'].sum().reset_index()
                    fig = px.bar(revenue_by_field, x='field_name', y='total_price', 
                               title="Revenue by Field", labels={'total_price': 'Revenue (£)', 'field_name': 'Field'})
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    st.subheader("Bookings by Status")
                    status_count = df['status'].value_counts().reset_index()
                    status_count.columns = ['status', 'count']
                    fig = px.pie(status_count, values='count', names='status', title="Bookings by Status")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data available for analytics yet")
    
    # Land Requests tab (only for landowner_member role)
    if user.role == 'landowner_member':
        with tab_requests:
            st.header("📝 Request Land Addition")
            st.markdown("Submit a request for admin to add your land to the platform")
            
            # Show existing requests
            user_requests = get_landowner_requests_by_user(user.id)
            if user_requests:
                st.subheader("Your Previous Requests")
                for req in user_requests:
                    status_color = {"pending": "🟡", "approved": "🟢", "rejected": "🔴"}
                    status_icon = status_color.get(req.status, "⚪")
                    
                    with st.expander(f"{status_icon} {req.land_name} - {req.status.title()}"):
                        st.markdown(f"**Location:** {req.land_location}")
                        st.markdown(f"**Size:** {req.land_size or 'Not specified'}")
                        st.markdown(f"**Type:** {req.land_type or 'Not specified'}")
                        st.markdown(f"**Description:** {req.description}")
                        st.markdown(f"**Submitted:** {req.created_at.strftime('%Y-%m-%d %H:%M') if req.created_at else 'Unknown'}")
                        if req.admin_notes:
                            st.info(f"**Admin Notes:** {req.admin_notes}")
                st.markdown("---")
            
            # Request submission form
            st.subheader("Submit New Request")
            with st.form("land_request_form"):
                land_name = st.text_input("Land Name*", placeholder="e.g., Highland Deer Estate")
                land_location = st.text_input("Location*", placeholder="e.g., Scottish Highlands, Inverness")
                land_size = st.text_input("Land Size", placeholder="e.g., 500 acres, 200 hectares")
                land_type = st.selectbox("Land Type", [
                    "Select type...",
                    "Woodland", 
                    "Moorland", 
                    "Coastal/Marshland",
                    "Farmland",
                    "Mixed Terrain"
                ])
                description = st.text_area("Description*", 
                    placeholder="Describe your land, hunting opportunities, available species, etc.",
                    help="This helps admin understand your offering")
                contact_details = st.text_input("Contact Details", 
                    placeholder="Phone or email for admin contact",
                    value=user.phone or user.email)
                
                submitted = st.form_submit_button("Submit Request", type="primary")
                
                if submitted:
                    if not land_name or not land_location or not description:
                        st.error("Please fill in all required fields (marked with *)")
                    else:
                        selected_type = land_type if land_type != "Select type..." else None
                        create_landowner_request(
                            user_id=user.id,
                            land_name=land_name,
                            land_location=land_location,
                            description=description,
                            land_size=land_size,
                            land_type=selected_type,
                            contact_details=contact_details
                        )
                        st.success(f"✅ Request submitted for {land_name}! Admin will review it soon.")
                        st.balloons()
                        st.rerun()

def admin_dashboard(user: User):
    st.title("⚙️ Admin Dashboard")
    
    tab1, tab2, tab_fields, tab3, tab_land_requests, tab_review_moderation = st.tabs(["Platform Overview", "User Management", "Field Management", "Booking Management", "Land Requests", "Review Moderation"])
    
    with tab1:
        st.header("Platform Overview")
        
        all_users = get_all_users()
        all_fields = get_all_fields()
        all_bookings = get_all_bookings()
        all_hunt_sessions = get_all_hunt_sessions()
        all_hunt_reports = get_all_hunt_reports()
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("Total Users", len(all_users))
        with col2:
            st.metric("Total Fields", len(all_fields))
        with col3:
            st.metric("Total Bookings", len(all_bookings))
        with col4:
            confirmed_bookings = [b for b in all_bookings if b.status == 'confirmed']
            st.metric("Confirmed Bookings", len(confirmed_bookings))
        with col5:
            total_revenue = sum(b.total_price for b in all_bookings if b.status == 'confirmed')
            st.metric("Total Revenue", f"£{total_revenue:,}")
        
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            completed_hunts = [hs for hs in all_hunt_sessions if hs.status == 'completed']
            st.metric("Completed Hunts", len(completed_hunts))
        with col2:
            active_hunts = [hs for hs in all_hunt_sessions if hs.status == 'active']
            st.metric("Active Hunts", len(active_hunts))
        with col3:
            st.metric("Hunt Reports", len(all_hunt_reports))
        with col4:
            total_harvest = sum(hr.animals_harvested or 0 for hr in all_hunt_reports)
            st.metric("Total Animals Harvested", total_harvest)
        
        st.markdown("---")
        st.subheader("📊 Field Visit Analytics")
        
        if all_bookings:
            field_visit_data = []
            for field in all_fields:
                field_bookings = [b for b in all_bookings if b.field_id == field.id]
                confirmed_visits = [b for b in field_bookings if b.status == 'confirmed']
                field_revenue = sum(b.total_price for b in confirmed_visits)
                
                hunt_sessions_for_field = [hs for hs in all_hunt_sessions if hs.field_id == field.id]
                completed_sessions = [hs for hs in hunt_sessions_for_field if hs.status == 'completed']
                
                field_visit_data.append({
                    'Field Name': field.name,
                    'Location': field.location,
                    'Type': field.field_type or 'Standard',
                    'Total Bookings': len(field_bookings),
                    'Confirmed Visits': len(confirmed_visits),
                    'Completed Hunts': len(completed_sessions),
                    'Revenue (£)': field_revenue
                })
            
            df_visits = pd.DataFrame(field_visit_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Most Popular Fields (by confirmed visits)**")
                top_fields = df_visits.nlargest(10, 'Confirmed Visits')[['Field Name', 'Confirmed Visits', 'Revenue (£)']]
                fig = px.bar(top_fields, x='Field Name', y='Confirmed Visits', 
                           title="Top 10 Fields by Visits",
                           labels={'Confirmed Visits': 'Visits', 'Field Name': 'Field'},
                           color='Revenue (£)', color_continuous_scale='Viridis')
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Revenue by Field Type**")
                revenue_by_type = df_visits.groupby('Type')['Revenue (£)'].sum().reset_index()
                fig = px.pie(revenue_by_type, values='Revenue (£)', names='Type', 
                           title="Revenue Distribution by Field Type")
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📈 Booking Trends")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Booking Status Distribution**")
                status_data = df_visits.agg({'Total Bookings': 'sum'}).to_dict()
                all_statuses = {}
                for booking in all_bookings:
                    all_statuses[booking.status] = all_statuses.get(booking.status, 0) + 1
                
                status_df = pd.DataFrame(list(all_statuses.items()), columns=['Status', 'Count'])
                fig = px.pie(status_df, values='Count', names='Status', 
                           title="Bookings by Status",
                           color_discrete_map={
                               'confirmed': '#28a745',
                               'pending': '#ffc107',
                               'cancelled': '#dc3545',
                               'rejected': '#6c757d'
                           })
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("**Hunt Completion Rate**")
                if all_hunt_sessions:
                    session_status = {}
                    for hs in all_hunt_sessions:
                        session_status[hs.status] = session_status.get(hs.status, 0) + 1
                    
                    session_df = pd.DataFrame(list(session_status.items()), columns=['Status', 'Count'])
                    fig = px.pie(session_df, values='Count', names='Status', 
                               title="Hunt Session Status",
                               color_discrete_map={
                                   'completed': '#28a745',
                                   'active': '#ffc107',
                                   'not_started': '#6c757d'
                               })
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hunt session data available yet")
            
            st.markdown("---")
            st.subheader("📋 Detailed Field Visit History")
            st.dataframe(df_visits.sort_values('Confirmed Visits', ascending=False), 
                        use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("🦌 Harvested Animals Analytics")
            
            if all_hunt_reports:
                animal_conditions = {'Excellent': 0, 'Good': 0, 'Bad': 0, 'Diseased': 0}
                species_count = {}
                disease_count = {}
                total_tracked_animals = 0
                
                for report in all_hunt_reports:
                    if report.animals_detail:
                        for animal in report.animals_detail:
                            total_tracked_animals += 1
                            condition = animal.get('condition', 'Unknown')
                            species = animal.get('species', 'Unknown')
                            disease = animal.get('disease_type')
                            
                            animal_conditions[condition] = animal_conditions.get(condition, 0) + 1
                            species_count[species] = species_count.get(species, 0) + 1
                            
                            if disease and disease != 'None':
                                disease_count[disease] = disease_count.get(disease, 0) + 1
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Animal Conditions**")
                    if total_tracked_animals > 0:
                        condition_df = pd.DataFrame(list(animal_conditions.items()), columns=['Condition', 'Count'])
                        condition_df = condition_df[condition_df['Count'] > 0]
                        fig = px.pie(condition_df, values='Count', names='Condition', 
                                   title="Harvested Animals by Condition",
                                   color_discrete_map={
                                       'Excellent': '#28a745',
                                       'Good': '#17a2b8',
                                       'Bad': '#ffc107',
                                       'Diseased': '#dc3545'
                                   })
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No detailed animal tracking data available")
                
                with col2:
                    st.markdown("**Species Breakdown**")
                    if species_count:
                        species_df = pd.DataFrame(list(species_count.items()), columns=['Species', 'Count'])
                        fig = px.bar(species_df.sort_values('Count', ascending=False), 
                                   x='Species', y='Count', 
                                   title="Harvested Animals by Species")
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No species data available")
                
                with col3:
                    st.markdown("**Disease Tracking**")
                    if disease_count:
                        disease_df = pd.DataFrame(list(disease_count.items()), columns=['Disease', 'Count'])
                        st.dataframe(disease_df.sort_values('Count', ascending=False), 
                                   use_container_width=True, hide_index=True)
                        st.warning(f"⚠️ Total diseased animals reported: {sum(disease_count.values())}")
                    else:
                        st.success("✓ No diseased animals reported")
            else:
                st.info("No hunt reports available yet")
        else:
            st.info("No booking data available yet. Analytics will appear once bookings are made.")
    
    with tab2:
        st.header("User Management")
        
        st.subheader("All Users")
        
        all_users = get_all_users()
        
        for user_obj in all_users:
            compliance_icon = "✅" if user_obj.is_compliant else "❌"
            compliance_color = "green" if user_obj.is_compliant else "red"
            
            with st.expander(f"{compliance_icon} {user_obj.name} ({user_obj.email}) - {user_obj.role.upper()}", expanded=False):
                st.markdown(f"**Compliance Status:** :{compliance_color}[{'COMPLIANT' if user_obj.is_compliant else 'NOT COMPLIANT'}]")
                
                if not user_obj.is_compliant:
                    st.warning("⚠️ This user is not compliant and may have restricted access")
                
                st.markdown("---")
                
                with st.form(f"edit_user_{user_obj.id}"):
                    st.markdown("### Edit User Details")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_name = st.text_input("Name", value=user_obj.name or "")
                        edit_email = st.text_input("Email", value=user_obj.email or "")
                        edit_phone = st.text_input("Phone", value=user_obj.phone or "")
                    
                    with col2:
                        edit_location = st.text_input("Location", value=user_obj.location or "")
                        edit_role = st.selectbox("Role", 
                                                ["hunter", "shooting_member", "international_hunter", "landowner_member", "guide_member", "outfitter", "admin"],
                                                index=["hunter", "shooting_member", "international_hunter", "landowner_member", "guide_member", "outfitter", "admin"].index(user_obj.role) if user_obj.role in ["hunter", "shooting_member", "international_hunter", "landowner_member", "guide_member", "outfitter", "admin"] else 0)
                        edit_is_compliant = st.checkbox("Is Compliant", value=user_obj.is_compliant)
                    
                    st.markdown("---")
                    st.markdown("### Membership Information")
                    col3, col4 = st.columns(2)
                    with col3:
                        edit_membership_number = st.text_input("Membership Number", value=user_obj.membership_number or "")
                    with col4:
                        edit_membership_expiry = st.date_input("Membership Expiry", 
                                                              value=datetime.strptime(user_obj.membership_expiry, "%Y-%m-%d").date() if user_obj.membership_expiry else None,
                                                              help="Leave empty for no expiry")
                    
                    st.markdown("---")
                    st.markdown("### Change Password (Optional)")
                    edit_password = st.text_input("New Password (leave empty to keep current)", type="password", key=f"pwd_{user_obj.id}")
                    
                    if st.form_submit_button("💾 Update User", type="primary"):
                        update_data = {
                            'name': edit_name,
                            'email': edit_email,
                            'phone': edit_phone,
                            'location': edit_location,
                            'role': edit_role,
                            'membership_number': edit_membership_number,
                            'membership_expiry': edit_membership_expiry.strftime("%Y-%m-%d") if edit_membership_expiry else None,
                            'is_compliant': edit_is_compliant
                        }
                        
                        if edit_password:
                            update_data['password'] = edit_password
                        
                        updated_user = admin_update_user(user_obj.id, update_data)
                        
                        if updated_user:
                            st.success(f"✅ User {edit_name} updated successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to update user")
        
        st.markdown("---")
        
        with st.expander("➕ Add New User"):
            with st.form("add_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_email = st.text_input("Email")
                    new_name = st.text_input("Name")
                    new_password = st.text_input("Password", type="password")
                with col2:
                    new_role = st.selectbox("Role", ["hunter", "shooting_member", "international_hunter", "landowner_member", "guide_member", "outfitter", "admin"])
                    new_phone = st.text_input("Phone")
                    new_location = st.text_input("Location")
                
                if st.form_submit_button("Add User"):
                    if new_email and not get_user_by_email(new_email):
                        create_user(new_email, new_password, new_role, new_name, new_phone, new_location)
                        st.success(f"User {new_email} added successfully!")
                        st.rerun()
                    else:
                        st.error("Email already exists or is invalid")
    
    with tab_fields:
        st.header("🏞️ Field Management")
        st.markdown("Add, view, and manage all fields on the platform")
        
        # Add New Field Button
        if st.button("➕ Add New Field", type="primary"):
            st.session_state.show_admin_add_field = True
        
        if st.session_state.get('show_admin_add_field', False):
            with st.form("admin_add_field_form"):
                st.subheader("Add New Field")
                
                col1, col2 = st.columns(2)
                with col1:
                    field_name = st.text_input("Field Name*")
                    hunting_type = st.selectbox("Hunting Type", ["Red Deer Stalking", "Driven Grouse", "Pheasant & Partridge", "Duck & Goose"])
                    field_location = st.text_input("Location*")
                    field_price = st.number_input("Price per Day (£)", min_value=0, value=300)
                with col2:
                    field_capacity = st.number_input("Capacity", min_value=1, value=4)
                    field_lat = st.number_input("Latitude", value=55.0)
                    field_lon = st.number_input("Longitude", value=-3.0)
                    field_season = st.text_input("Season", value="Aug-Dec")
                
                # Assign to outfitter/guide/landowner
                all_outfitters = [u for u in get_all_users() if u.role in ['guide_member', 'landowner_member', 'outfitter']]
                outfitter_options = {f"{o.name} ({o.email}) - {o.role.upper()}": o.id for o in all_outfitters}
                if outfitter_options:
                    assigned_outfitter = st.selectbox("Assign to Guide/Landowner*", ["Unassigned"] + list(outfitter_options.keys()))
                else:
                    st.warning("No guides or landowners available. Create users first.")
                    assigned_outfitter = "Unassigned"
                
                field_description = st.text_area("Description")
                
                st.markdown("---")
                st.markdown("### 📸 Field Images")
                uploaded_images = st.file_uploader(
                    "Upload field images (max 5 images)", 
                    type=['png', 'jpg', 'jpeg'],
                    accept_multiple_files=True,
                    help="Upload up to 5 images that will appear in the carousel on the field listing"
                )
                
                if uploaded_images and len(uploaded_images) > 5:
                    st.warning("⚠️ Maximum 5 images allowed. Only the first 5 will be used.")
                    uploaded_images = uploaded_images[:5]
                
                st.markdown("---")
                field_type = st.selectbox("Ground Type", ["DIY-Leased", "Subsidised", "International"], help="Choose the field type")
                
                if field_type in ["Subsidised", "International"]:
                    st.markdown("### Subsidised/International Ground Details")
                    col1, col2 = st.columns(2)
                    with col1:
                        guide_name = st.text_input("Guide Name")
                        guide_contact = st.text_input("Guide Contact (Phone/Email)")
                    with col2:
                        subsidy_percentage = st.number_input("Subsidy Discount (%)", min_value=0, max_value=100, value=0)
                    
                    species_allowed_input = st.text_area("Species Allowed (one per line)", placeholder="e.g.,\nRed Deer\nRoe Deer\nWild Boar")
                    species_allowed = [s.strip() for s in species_allowed_input.split("\n") if s.strip()]
                else:
                    st.markdown("### DIY-Leased Ground Details")
                    st.markdown("**Quarry Species and Quotas**")
                    
                    num_species = st.number_input("Number of Quarry Species", min_value=1, max_value=10, value=1)
                    
                    quarry_species = []
                    for i in range(int(num_species)):
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            species = st.text_input(f"Species {i+1}", key=f"admin_species_{i}", placeholder="e.g., Red Grouse, Pheasant")
                        with col2:
                            quota = st.number_input(f"Quota", min_value=0, value=100, key=f"admin_quota_{i}")
                        
                        if species:
                            quarry_species.append({
                                "species": species,
                                "total": quota,
                                "remaining": quota
                            })
                
                st.markdown("---")
                auto_approve = st.checkbox("Auto-approve bookings", value=False, help="When enabled, bookings will be automatically approved without manual review")
                
                rules_info = st.text_area("Ground Rules & Information", placeholder="Any special rules, requirements, or information for hunters")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Save Field", type="primary"):
                        if not field_name or not field_location or (assigned_outfitter == "Unassigned"):
                            st.error("Please fill in all required fields (marked with *) and assign to a guide/landowner")
                        else:
                            outfitter_id = outfitter_options[assigned_outfitter] if assigned_outfitter != "Unassigned" else None
                            
                            # Save uploaded images
                            image_paths = []
                            if uploaded_images:
                                image_paths = save_field_images(uploaded_images, field_name)
                            
                            if field_type in ["Subsidised", "International"]:
                                new_field = create_subsidised_field(
                                    outfitter_id=outfitter_id,
                                    name=field_name,
                                    location=field_location,
                                    lat=field_lat,
                                    lon=field_lon,
                                    hunting_type=hunting_type,
                                    price=field_price,
                                    capacity=field_capacity,
                                    description=field_description,
                                    season=field_season,
                                    guide_name=guide_name,
                                    guide_contact=guide_contact,
                                    subsidy_percentage=subsidy_percentage,
                                    species_allowed=species_allowed,
                                    rules_info=rules_info,
                                    auto_approve=auto_approve,
                                    image_gallery=image_paths
                                )
                            else:
                                new_field = create_diy_leased_field(
                                    outfitter_id=outfitter_id,
                                    name=field_name,
                                    location=field_location,
                                    lat=field_lat,
                                    lon=field_lon,
                                    hunting_type=hunting_type,
                                    price=field_price,
                                    capacity=field_capacity,
                                    description=field_description,
                                    season=field_season,
                                    quarry_species=quarry_species,
                                    rules_info=rules_info,
                                    auto_approve=auto_approve,
                                    image_gallery=image_paths
                                )
                            
                            st.session_state.show_admin_add_field = False
                            st.success(f"✅ Field '{field_name}' added successfully!")
                            st.rerun()
                with col2:
                    if st.form_submit_button("Cancel"):
                        st.session_state.show_admin_add_field = False
                        st.rerun()
        
        st.markdown("---")
        st.subheader("📋 All Fields")
        
        all_fields = get_all_fields()
        if all_fields:
            for field in all_fields:
                field_type_badge = "🎯 DIY-LEASED" if field.field_type == 'diy-leased' else "🌟 SUBSIDISED" if field.field_type == 'subsidised' else "🌍 INTERNATIONAL"
                outfitter = get_user_by_id(field.outfitter_id) if field.outfitter_id else None
                
                with st.expander(f"{field_type_badge} | {field.name} - {field.location}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Type:** {field.type}")
                        st.markdown(f"**Season:** {field.season}")
                        st.markdown(f"**Description:** {field.description}")
                        st.markdown(f"**Price:** £{field.price_per_day}/day")
                    with col2:
                        st.markdown(f"**Capacity:** {field.capacity}")
                        st.markdown(f"**GPS:** {field.lat}, {field.lon}")
                        if outfitter:
                            st.markdown(f"**Assigned to:** {outfitter.name} ({outfitter.role})")
                        else:
                            st.warning("⚠️ Not assigned to any outfitter/guide")
                    
                    # Wildlife survey report upload for landowner fields
                    if field.outfitter_id:
                        field_outfitter = get_user_by_id(field.outfitter_id)
                        if field_outfitter and field_outfitter.role == 'landowner_member':
                            st.markdown("---")
                            st.markdown("### 📄 Wildlife Survey Report")
                            current_report = field.wildlife_survey_report if hasattr(field, 'wildlife_survey_report') else None
                            
                            if current_report:
                                st.success("✅ Survey report uploaded")
                                with st.expander("View Current Report"):
                                    st.markdown(current_report)
                            else:
                                st.info("No survey report uploaded")
                            
                            new_report = st.text_area("Upload/Update Survey Report", 
                                value=current_report or "", 
                                key=f"survey_{field.id}",
                                placeholder="Enter wildlife survey data, species counts, habitat conditions, etc.")
                            
                            if st.button("💾 Save Survey Report", key=f"save_survey_{field.id}"):
                                update_field_survey_report(field.id, new_report)
                                st.success("Survey report updated!")
                                st.rerun()
                    
                    # Delete field section
                    st.markdown("---")
                    st.markdown("### 🗑️ Delete Field")
                    st.warning("⚠️ **Warning:** Deleting this field will permanently remove all associated bookings, hunt sessions, and reports. This action cannot be undone.")
                    
                    # Use session state for confirmation
                    confirm_key = f"confirm_delete_{field.id}"
                    if confirm_key not in st.session_state:
                        st.session_state[confirm_key] = False
                    
                    col_del1, col_del2 = st.columns(2)
                    with col_del1:
                        if not st.session_state[confirm_key]:
                            if st.button("🗑️ Delete Field", key=f"delete_btn_{field.id}", type="secondary"):
                                st.session_state[confirm_key] = True
                                st.rerun()
                        else:
                            if st.button("✅ Confirm Delete", key=f"confirm_btn_{field.id}", type="primary"):
                                if delete_field(field.id):
                                    st.success(f"Field '{field.name}' deleted successfully!")
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to delete field")
                    with col_del2:
                        if st.session_state[confirm_key]:
                            if st.button("❌ Cancel", key=f"cancel_delete_{field.id}"):
                                st.session_state[confirm_key] = False
                                st.rerun()
        else:
            st.info("No fields created yet")
    
    with tab3:
        st.header("Booking Management")
        
        all_bookings = get_all_bookings()
        
        if all_bookings:
            booking_data = []
            for b in all_bookings:
                field = get_field_by_id(b.field_id)
                hunter = get_user_by_id(b.hunter_id)
                booking_data.append({
                    'id': b.id,
                    'field_name': field.name,
                    'hunter_email': hunter.email if hunter else 'Unknown',
                    'date': b.date,
                    'num_hunters': b.num_hunters,
                    'total_price': b.total_price,
                    'status': b.status,
                    'created_at': b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else ''
                })
            
            df_bookings = pd.DataFrame(booking_data)
            st.dataframe(df_bookings, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔐 Admin: Create Booking (with Override)")
            
            with st.expander("Create New Booking"):
                with st.form("admin_create_booking"):
                    st.caption("Admin can override double booking prevention for special cases")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        all_hunters = [u for u in get_all_users() if u.role in ['hunter', 'shooting_member', 'international_hunter']]
                        hunter_options = {f"{h.name} ({h.email})": h.id for h in all_hunters}
                        selected_hunter = st.selectbox("Select Hunter", list(hunter_options.keys()))
                        
                        all_fields = get_all_fields()
                        field_options = {f"{f.name} - {f.location}": f.id for f in all_fields}
                        selected_field = st.selectbox("Select Field", list(field_options.keys()))
                    
                    with col2:
                        booking_date = st.date_input("Booking Date", min_value=datetime.now())
                        num_hunters_admin = st.number_input("Number of Hunters", min_value=1, max_value=10, value=1)
                    
                    override_double_booking = st.checkbox("Override Double Booking Prevention", 
                                                         help="Check this to allow booking even if hunter has another booking on the same date")
                    
                    if st.form_submit_button("Create Booking", type="primary"):
                        if selected_hunter and selected_field:
                            hunter_id = hunter_options[selected_hunter]
                            field_id = field_options[selected_field]
                            field = get_field_by_id(field_id)
                            
                            date_str = booking_date.strftime("%Y-%m-%d")
                            total_price = field.price_per_day * num_hunters_admin if field else 100.0
                            
                            has_existing, existing_booking = check_hunter_has_booking_on_date(hunter_id, date_str)
                            
                            if has_existing and not override_double_booking:
                                st.warning(f"⚠️ Hunter already has a booking on {date_str}. Check 'Override' to proceed anyway.")
                            else:
                                booking, message = create_booking(
                                    field_id=field_id,
                                    hunter_id=hunter_id,
                                    date=date_str,
                                    num_hunters=num_hunters_admin,
                                    total_price=total_price,
                                    payment_id=f"ADMIN_{datetime.now().timestamp()}",
                                    admin_override=override_double_booking
                                )
                                
                                if booking:
                                    st.success(f"✅ {message}")
                                    st.rerun()
                                else:
                                    st.error(message)
            
            st.markdown("---")
            st.subheader("Manage Bookings")
            
            for booking in all_bookings:
                field = get_field_by_id(booking.field_id)
                with st.expander(f"Booking #{booking.id} - {field.name} ({booking.status})"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Field:** {field.name}")
                        hunter = get_user_by_id(booking.hunter_id)
                        st.markdown(f"**Hunter:** {hunter.email if hunter else 'Unknown'}")
                        st.markdown(f"**Date:** {booking.date}")
                        st.markdown(f"**Hunters:** {booking.num_hunters}")
                        st.markdown(f"**Total:** £{booking.total_price}")
                        st.markdown(f"**Created:** {booking.created_at.strftime('%Y-%m-%d %H:%M') if booking.created_at else 'Unknown'}")
                    with col2:
                        status_options = ["confirmed", "pending", "cancelled", "rejected"]
                        current_status = booking.status
                        if current_status in status_options:
                            current_index = status_options.index(current_status)
                        else:
                            current_index = 0
                        
                        new_status = st.selectbox("Status", status_options, 
                                                 index=current_index,
                                                 key=f"status_{booking.id}")
                        if st.button("Update", key=f"update_{booking.id}"):
                            update_booking_status(booking.id, new_status)
                            st.success("Status updated!")
                            st.rerun()
        else:
            st.info("No bookings in the system yet")
    
    with tab_land_requests:
        st.header("📋 Landowner Request Management")
        
        tab_pending, tab_all = st.tabs(["⏳ Pending Requests", "📑 All Requests"])
        
        with tab_pending:
            pending_requests = get_pending_landowner_requests()
            
            if pending_requests:
                st.markdown(f"**{len(pending_requests)} pending request(s)**")
                
                for req in pending_requests:
                    with st.expander(f"📝 {req.land_name} - {req.land_location}"):
                        requester = get_user_by_id(req.user_id)
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"**Requester:** {requester.name if requester else 'Unknown'}")
                            st.markdown(f"**Email:** {requester.email if requester else 'Unknown'}")
                            st.markdown(f"**Location:** {req.land_location}")
                            if req.land_size:
                                st.markdown(f"**Size:** {req.land_size}")
                            if req.land_type:
                                st.markdown(f"**Type:** {req.land_type}")
                            st.markdown(f"**Contact:** {req.contact_details or 'Not provided'}")
                            st.markdown(f"**Submitted:** {req.created_at.strftime('%Y-%m-%d %H:%M') if req.created_at else 'Unknown'}")
                        
                        with col2:
                            st.info(f"**Request ID:** {req.id}")
                        
                        st.markdown("**Description:**")
                        st.write(req.description)
                        
                        st.markdown("---")
                        st.subheader("Admin Actions")
                        
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            if st.button("✅ Approve", key=f"approve_{req.id}", type="primary"):
                                update_landowner_request_status(req.id, "approved", "Request approved by admin")
                                st.success(f"Approved {req.land_name}")
                                st.info("💡 Next step: Create the field manually in 'Add New Field' section and assign it to this landowner")
                                st.rerun()
                        
                        with col2:
                            if st.button("❌ Reject", key=f"reject_{req.id}"):
                                admin_notes = st.text_input("Rejection reason", key=f"reason_{req.id}")
                                if admin_notes:
                                    update_landowner_request_status(req.id, "rejected", admin_notes)
                                    st.warning(f"Rejected {req.land_name}")
                                    st.rerun()
                                else:
                                    st.error("Please provide a rejection reason")
            else:
                st.success("✅ No pending requests")
        
        with tab_all:
            all_requests = get_all_landowner_requests()
            
            if all_requests:
                st.markdown(f"**Total: {len(all_requests)} request(s)**")
                
                for req in all_requests:
                    status_color = {"pending": "🟡", "approved": "🟢", "rejected": "🔴"}
                    status_icon = status_color.get(req.status, "⚪")
                    
                    with st.expander(f"{status_icon} {req.land_name} - {req.status.title()}"):
                        requester = get_user_by_id(req.user_id)
                        
                        st.markdown(f"**Requester:** {requester.name if requester else 'Unknown'}")
                        st.markdown(f"**Location:** {req.land_location}")
                        if req.land_size:
                            st.markdown(f"**Size:** {req.land_size}")
                        st.markdown(f"**Status:** {req.status.title()}")
                        st.markdown(f"**Submitted:** {req.created_at.strftime('%Y-%m-%d %H:%M') if req.created_at else 'Unknown'}")
                        if req.reviewed_at:
                            st.markdown(f"**Reviewed:** {req.reviewed_at.strftime('%Y-%m-%d %H:%M')}")
                        if req.admin_notes:
                            st.info(f"**Admin Notes:** {req.admin_notes}")
                        st.markdown("**Description:**")
                        st.write(req.description)
            else:
                st.info("No requests submitted yet")
    
    with tab_review_moderation:
        st.header("⭐ Review Moderation")
        st.markdown("Manage and moderate user reviews from hunt reports")
        
        all_reports = get_all_hunt_reports()
        reports_with_reviews = [r for r in all_reports if r.review_rating or r.review_text]
        
        if reports_with_reviews:
            st.markdown(f"**Total Reviews: {len(reports_with_reviews)}**")
            st.markdown("---")
            
            for report in sorted(reports_with_reviews, key=lambda r: r.created_at, reverse=True):
                hunter = get_user_by_id(report.hunter_id)
                field = get_field_by_id(report.field_id)
                
                with st.expander(f"{'⭐' * (report.review_rating or 0)} {field.name if field else 'Unknown Field'} - by {hunter.name if hunter else 'Unknown'}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**Hunter:** {hunter.name if hunter else 'Unknown'}")
                        st.markdown(f"**Email:** {hunter.email if hunter else 'Unknown'}")
                        st.markdown(f"**Field:** {field.name if field else 'Unknown'}")
                        st.markdown(f"**Location:** {field.location if field else 'Unknown'}")
                        st.markdown(f"**Rating:** {'⭐' * (report.review_rating or 0)}")
                        st.markdown(f"**Review:**")
                        st.write(report.review_text or "No review text")
                        st.markdown(f"**Date:** {report.created_at.strftime('%Y-%m-%d %H:%M') if report.created_at else 'Unknown'}")
                    
                    with col2:
                        st.metric("Report ID", report.id)
                        if report.animals_harvested > 0:
                            st.success(f"✅ {report.animals_harvested} harvested")
                        else:
                            st.info("❌ No harvest")
                    
                    st.markdown("---")
                    st.subheader("Admin Actions")
                    
                    with st.form(f"admin_edit_review_{report.id}"):
                        st.markdown("**Edit Review:**")
                        admin_rating = st.slider("Rating", 1, 5, report.review_rating or 5, key=f"admin_rating_{report.id}")
                        admin_text = st.text_area("Review Text", value=report.review_text or "", key=f"admin_text_{report.id}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Update Review"):
                                update_hunt_report(report.id, review_rating=admin_rating, review_text=admin_text)
                                st.success("Review updated!")
                                st.rerun()
                        
                        with col2:
                            if st.form_submit_button("🗑️ Delete Review"):
                                update_hunt_report(report.id, review_rating=None, review_text=None)
                                st.warning("Review deleted!")
                                st.rerun()
        else:
            st.info("No reviews submitted yet")

def show_public_tag_verification():
    """Public page to verify animal tags - no login required"""
    st.title("🏷️ Fieldsports Alliance")
    st.subheader("Animal Tag Verification System")
    
    tag_number = st.query_params.get('tag', '')
    
    if tag_number:
        tag = get_animal_tag_by_tag_number(tag_number)
        
        if tag:
            st.success("✅ Tag Verified")
            
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("### Animal Photo")
                if tag.photo_path and os.path.exists(tag.photo_path):
                    st.image(tag.photo_path, use_column_width=True)
                else:
                    st.info("Photo not available")
                
                st.markdown("---")
                st.markdown("### QR Code")
                if tag.qr_code_path and os.path.exists(tag.qr_code_path):
                    st.image(tag.qr_code_path, width=200)
            
            with col2:
                st.markdown("### Tag Information")
                st.markdown(f"**Tag Number:** `{tag.tag_number}`")
                st.markdown(f"**Species:** {tag.species}")
                st.markdown(f"**Condition:** {tag.condition}")
                
                if tag.animal_tag:
                    st.markdown(f"**Physical Tag:** {tag.animal_tag}")
                
                if tag.disease_type:
                    st.warning(f"⚠️ **Disease Detected:** {tag.disease_type}")
                
                st.markdown("---")
                st.markdown("### Hunt Details")
                
                hunter = get_user_by_id(tag.hunter_id)
                if hunter:
                    st.markdown(f"**Hunter:** {hunter.name}")
                    st.markdown(f"**Hunter Location:** {hunter.location or 'Not specified'}")
                
                field = get_field_by_id(tag.field_id)
                if field:
                    st.markdown(f"**Field:** {field.name}")
                    st.markdown(f"**Location:** {field.location}")
                    st.markdown(f"**GPS:** {field.lat}, {field.lon}")
                
                st.markdown(f"**Tagged:** {tag.created_at.strftime('%Y-%m-%d %H:%M')}")
                
                if tag.notes:
                    st.markdown("---")
                    st.markdown("### Additional Notes")
                    st.info(tag.notes)
        else:
            st.error("❌ Tag Not Found")
            st.markdown("This tag number is not registered in our system.")
            st.markdown(f"Tag: `{tag_number}`")
    else:
        st.info("👉 Scan a QR code to verify animal tag details")
        st.markdown("This page displays traceability information for tagged animals.")
    
    st.markdown("---")
    st.caption("Powered by Fieldsports Alliance | Animal Traceability System")

def main():
    if 'tag' in st.query_params:
        show_public_tag_verification()
        return
    
    if not st.session_state.logged_in:
        login_page()
    else:
        user = get_user_by_id(st.session_state.current_user_id)
        
        if not user:
            st.error("User not found. Please log in again.")
            logout()
            return
        
        # Check user compliance - force logout if non-compliant
        if hasattr(user, 'is_compliant') and user.is_compliant == False:
            st.error("🚫 Your account has been deactivated due to non-compliance. Please contact admin to reactivate your account.")
            logout()
            return
        
        # Map role labels for display
        role_display = {
            'hunter': 'Shooting Member',
            'shooting_member': 'Shooting Member',
            'international_hunter': 'International Hunter',
            'landowner_member': 'Landowner Member',
            'outfitter': 'Guide Member',
            'guide_member': 'Guide Member',
            'admin': 'Admin'
        }
        
        with st.sidebar:
            st.title("🦌 Fieldsports Alliance")
            st.markdown(f"**Name:** {user.name or 'Not set'}")
            st.markdown(f"**Role:** {role_display.get(user.role, user.role.title())}")
            
            if user.role in ['hunter', 'shooting_member', 'international_hunter']:
                st.markdown("---")
                st.subheader("👤 Membership")
                if user.membership_number:
                    st.markdown(f"**Number:** {user.membership_number}")
                else:
                    st.caption("No membership number" if user.role in ['shooting_member', 'hunter'] else "N/A - International")
                
                if user.membership_expiry:
                    st.markdown(f"**Expires:** {user.membership_expiry}")
                else:
                    st.caption("No expiry date set" if user.role in ['shooting_member', 'hunter'] else "N/A - International")
            
            elif user.role in ['outfitter', 'guide_member', 'landowner_member']:
                st.markdown("---")
                st.subheader("🏞️ Your Grounds")
                outfitter_fields = get_fields_by_outfitter(user.id)
                if outfitter_fields:
                    for field in outfitter_fields:
                        st.caption(f"📍 {field.name} - {field.location}")
                else:
                    st.caption("No grounds assigned yet")
            
            st.markdown("---")
            if st.button("Logout", use_container_width=True):
                logout()
        
        # Route to appropriate dashboard (support old and new role names)
        if st.session_state.user_role in ['hunter', 'shooting_member', 'international_hunter']:
            hunter_dashboard(user)
        elif st.session_state.user_role in ['outfitter', 'guide_member', 'landowner_member']:
            outfitter_dashboard(user)
        elif st.session_state.user_role == 'admin':
            admin_dashboard(user)

if __name__ == "__main__":
    main()
