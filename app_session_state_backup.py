import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
import json

st.set_page_config(
    page_title="Fieldsport Booking Platform",
    page_icon="🦌",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    if 'users' not in st.session_state:
        st.session_state.users = {
            'hunter@example.com': {
                'password': 'hunter123',
                'role': 'hunter',
                'name': 'John Hunter',
                'phone': '+44 7700 900000',
                'location': 'London, UK',
                'bookings': []
            },
            'outfitter@example.com': {
                'password': 'outfitter123',
                'role': 'outfitter',
                'name': 'Estate Management Ltd',
                'phone': '+44 7700 900001',
                'location': 'Scottish Highlands',
                'fields': [1, 2]
            },
            'admin@example.com': {
                'password': 'admin123',
                'role': 'admin',
                'name': 'Platform Admin',
                'phone': '+44 7700 900002',
                'location': 'London, UK'
            }
        }

initialize_session_state()

if 'fields' not in st.session_state:
    st.session_state.fields = {
        1: {
            'name': 'Highland Estate',
            'outfitter': 'Estate Management Ltd',
            'location': 'Scottish Highlands',
            'lat': 57.4778,
            'lon': -4.2247,
            'type': 'Red Deer Stalking',
            'price_per_day': 450,
            'currency': 'GBP',
            'capacity': 4,
            'description': 'Premium red deer stalking on 5,000 acres of highland estate with professional stalker.',
            'amenities': ['Professional Stalker', 'Larder Facilities', 'Transport', 'Accommodation Available'],
            'season': 'Jul-Oct',
            'image': 'https://images.unsplash.com/photo-1542273917363-3b1817f69a2d',
            'available_dates': {},
            'blocked_dates': []
        },
        2: {
            'name': 'Cairngorms Sporting Estate',
            'outfitter': 'Estate Management Ltd',
            'location': 'Cairngorms National Park',
            'lat': 57.0941,
            'lon': -3.6184,
            'type': 'Driven Grouse',
            'price_per_day': 650,
            'currency': 'GBP',
            'capacity': 8,
            'description': 'World-class driven grouse shooting with experienced beaters and loaders.',
            'amenities': ['Beaters', 'Loaders', 'Gun Dogs Available', 'Lunch Included'],
            'season': 'Aug-Dec',
            'image': 'https://images.unsplash.com/photo-1516466723877-e4ec1d736c8a',
            'available_dates': {},
            'blocked_dates': []
        },
        3: {
            'name': 'Yorkshire Moorland Shoot',
            'outfitter': 'Northern Shoots',
            'location': 'North Yorkshire',
            'lat': 54.2378,
            'lon': -1.4159,
            'type': 'Pheasant & Partridge',
            'price_per_day': 380,
            'currency': 'GBP',
            'capacity': 6,
            'description': 'Traditional driven pheasant and partridge shooting across beautiful moorland.',
            'amenities': ['Beaters', 'Gun Dogs', 'Refreshments', 'Game Processing'],
            'season': 'Oct-Feb',
            'image': 'https://images.unsplash.com/photo-1542273917363-3b1817f69a2d',
            'available_dates': {},
            'blocked_dates': []
        },
        4: {
            'name': 'Lake District Wildfowling',
            'outfitter': 'Lakeland Sporting',
            'location': 'Cumbria',
            'lat': 54.5970,
            'lon': -2.8212,
            'type': 'Duck & Goose',
            'price_per_day': 280,
            'currency': 'GBP',
            'capacity': 4,
            'description': 'Exciting wildfowling on coastal marshes with experienced guide.',
            'amenities': ['Guide', 'Boat Access', 'Decoys Provided', 'Hot Drinks'],
            'season': 'Sep-Jan',
            'image': 'https://images.unsplash.com/photo-1516466723877-e4ec1d736c8a',
            'available_dates': {},
            'blocked_dates': []
        }
    }

if 'bookings' not in st.session_state:
    st.session_state.bookings = []

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.user_role = None

if 'booking_counter' not in st.session_state:
    st.session_state.booking_counter = 1

if 'payment_tokens' not in st.session_state:
    st.session_state.payment_tokens = {}

def check_availability(field_id, date, num_hunters):
    field = st.session_state.fields[field_id]
    date_str = date.strftime("%Y-%m-%d") if isinstance(date, datetime) else str(date)
    
    if date_str in field.get('blocked_dates', []):
        return False, "Date is blocked by outfitter"
    
    bookings_on_date = [b for b in st.session_state.bookings 
                        if b['field_id'] == field_id 
                        and b['date'] == date_str 
                        and b['status'] in ['confirmed', 'pending']]
    
    total_hunters_booked = sum(b['num_hunters'] for b in bookings_on_date)
    
    if total_hunters_booked + num_hunters > field['capacity']:
        return False, f"Insufficient capacity. Only {field['capacity'] - total_hunters_booked} spots available"
    
    return True, "Available"

def simulate_stripe_payment(amount, card_details):
    import hashlib
    import time
    import re
    
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
    
    st.session_state.payment_tokens[payment_id] = {
        'amount': amount,
        'currency': 'GBP',
        'status': 'succeeded',
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'card_last4': card_details['card_number'].replace(' ', '')[-4:]
    }
    
    return True, "Payment successful", payment_id

def login_page():
    st.title("🦌 Fieldsport Booking Platform")
    st.markdown("### Welcome to the UK's Premier Fieldsport Booking System")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        tab1, tab2 = st.tabs(["Login", "Demo Accounts"])
        
        with tab1:
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            if st.button("Login", use_container_width=True):
                if email in st.session_state.users and st.session_state.users[email]['password'] == password:
                    st.session_state.logged_in = True
                    st.session_state.current_user = email
                    st.session_state.user_role = st.session_state.users[email]['role']
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        with tab2:
            st.markdown("**Test Accounts:**")
            st.code("Hunter: hunter@example.com / hunter123")
            st.code("Outfitter: outfitter@example.com / outfitter123")
            st.code("Admin: admin@example.com / admin123")

def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.user_role = None
    st.rerun()

def hunter_dashboard():
    st.title("🎯 Hunter Dashboard")
    
    user_data = st.session_state.users[st.session_state.current_user]
    
    tab1, tab2, tab3, tab4 = st.tabs(["Browse Fields", "My Bookings", "Profile", "Notifications"])
    
    with tab1:
        st.header("Discover Hunting Fields")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            search_type = st.selectbox("Hunting Type", ["All Types", "Red Deer Stalking", "Driven Grouse", "Pheasant & Partridge", "Duck & Goose"])
        with col2:
            search_location = st.selectbox("Location", ["All Locations", "Scottish Highlands", "Cairngorms National Park", "North Yorkshire", "Cumbria"])
        with col3:
            max_price = st.slider("Max Price (£)", 0, 1000, 1000)
        with col4:
            search_date = st.date_input("Preferred Date", datetime.now())
        
        filtered_fields = st.session_state.fields
        if search_type != "All Types":
            filtered_fields = {k: v for k, v in filtered_fields.items() if v['type'] == search_type}
        if search_location != "All Locations":
            filtered_fields = {k: v for k, v in filtered_fields.items() if v['location'] == search_location}
        filtered_fields = {k: v for k, v in filtered_fields.items() if v['price_per_day'] <= max_price}
        
        st.markdown("---")
        
        m = folium.Map(location=[55.3781, -3.4360], zoom_start=6)
        for field_id, field in filtered_fields.items():
            folium.Marker(
                [field['lat'], field['lon']],
                popup=f"{field['name']}<br>£{field['price_per_day']}/day",
                tooltip=field['name'],
                icon=folium.Icon(color='green', icon='tree', prefix='fa')
            ).add_to(m)
        
        st_folium(m, width=1200, height=400)
        
        st.markdown("---")
        
        for field_id, field in filtered_fields.items():
            with st.expander(f"🏞️ {field['name']} - {field['location']}", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**Type:** {field['type']}")
                    st.markdown(f"**Season:** {field['season']}")
                    st.markdown(f"**Description:** {field['description']}")
                    st.markdown("**Amenities:**")
                    for amenity in field['amenities']:
                        st.markdown(f"- ✓ {amenity}")
                
                with col2:
                    st.markdown(f"### £{field['price_per_day']} / day")
                    st.markdown(f"**Capacity:** {field['capacity']} hunters")
                    st.markdown(f"**Outfitter:** {field['outfitter']}")
                    
                    if st.button(f"Book Now", key=f"book_{field_id}"):
                        st.session_state.selected_field = field_id
                        st.session_state.booking_step = 'details'
                        st.rerun()
        
        if 'booking_step' in st.session_state and st.session_state.booking_step == 'details':
            show_booking_modal(st.session_state.selected_field)
    
    with tab2:
        st.header("My Bookings")
        
        user_bookings = [b for b in st.session_state.bookings if b['hunter_email'] == st.session_state.current_user]
        
        if user_bookings:
            for booking in user_bookings:
                field = st.session_state.fields[booking['field_id']]
                status_color = {
                    'confirmed': '🟢',
                    'pending': '🟡',
                    'cancelled': '🔴',
                    'rejected': '🔴'
                }
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    with col1:
                        st.markdown(f"**{field['name']}**")
                        st.markdown(f"{field['location']}")
                    with col2:
                        st.markdown(f"**Date:** {booking['date']}")
                        st.markdown(f"**Hunters:** {booking['num_hunters']}")
                    with col3:
                        st.markdown(f"**Total:** £{booking['total_price']}")
                        st.markdown(f"**Status:** {status_color.get(booking['status'], '⚪')} {booking['status'].title()}")
                    with col4:
                        if booking['status'] == 'confirmed':
                            if st.button("Cancel", key=f"cancel_{booking['id']}"):
                                booking['status'] = 'cancelled'
                                st.rerun()
                        elif booking['status'] == 'pending':
                            st.caption("Awaiting approval")
                        elif booking['status'] == 'rejected':
                            st.caption("Refund processed")
                    st.markdown("---")
        else:
            st.info("No bookings yet. Browse fields to make your first booking!")
    
    with tab3:
        st.header("Profile Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Name", value=user_data['name'])
            st.text_input("Email", value=st.session_state.current_user, disabled=True)
        with col2:
            st.text_input("Phone", value=user_data['phone'])
            st.text_input("Location", value=user_data['location'])
        
        if st.button("Update Profile"):
            st.success("Profile updated successfully!")
    
    with tab4:
        st.header("Notifications")
        
        notifications = []
        for booking in [b for b in st.session_state.bookings if b['hunter_email'] == st.session_state.current_user]:
            if booking['status'] == 'confirmed':
                notifications.append({
                    'type': 'success',
                    'message': f"Booking confirmed for {st.session_state.fields[booking['field_id']]['name']} on {booking['date']}",
                    'time': 'Today'
                })
        
        if notifications:
            for notif in notifications:
                if notif['type'] == 'success':
                    st.success(f"✓ {notif['message']} - {notif['time']}")
        else:
            st.info("No new notifications")

def show_booking_modal(field_id):
    field = st.session_state.fields[field_id]
    
    st.markdown("---")
    st.markdown(f"## Booking: {field['name']}")
    
    col1, col2 = st.columns(2)
    with col1:
        booking_date = st.date_input("Select Date", min_value=datetime.now())
        num_hunters = st.number_input("Number of Hunters", min_value=1, max_value=field['capacity'], value=1)
    
    with col2:
        st.markdown(f"**Price per day:** £{field['price_per_day']}")
        total_price = field['price_per_day'] * num_hunters
        st.markdown(f"**Total:** £{total_price}")
    
    available, message = check_availability(field_id, booking_date, num_hunters)
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
                    booking = {
                        'id': st.session_state.booking_counter,
                        'field_id': field_id,
                        'hunter_email': st.session_state.current_user,
                        'date': booking_date.strftime("%Y-%m-%d"),
                        'num_hunters': num_hunters,
                        'total_price': total_price,
                        'status': 'pending',
                        'payment_method': 'card',
                        'payment_id': payment_id,
                        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    st.session_state.bookings.append(booking)
                    st.session_state.booking_counter += 1
                    del st.session_state.booking_step
                    del st.session_state.selected_field
                    st.success("Booking request submitted! Payment processed. Awaiting outfitter confirmation.")
                    st.rerun()
                else:
                    st.error(f"Payment failed: {payment_message}")
    
    with col2:
        if st.button("Cancel"):
            del st.session_state.booking_step
            del st.session_state.selected_field
            st.rerun()

def outfitter_dashboard():
    st.title("🏞️ Outfitter Dashboard")
    
    user_data = st.session_state.users[st.session_state.current_user]
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "My Fields", "Bookings", "Availability", "Analytics"])
    
    with tab1:
        st.header("Dashboard Overview")
        
        outfitter_bookings = [b for b in st.session_state.bookings 
                              if st.session_state.fields[b['field_id']]['outfitter'] == user_data['name']]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Fields", len(user_data.get('fields', [])))
        with col2:
            st.metric("Total Bookings", len(outfitter_bookings))
        with col3:
            confirmed_bookings = [b for b in outfitter_bookings if b['status'] == 'confirmed']
            st.metric("Confirmed Bookings", len(confirmed_bookings))
        with col4:
            total_revenue = sum(b['total_price'] for b in confirmed_bookings)
            st.metric("Total Revenue", f"£{total_revenue:,}")
        
        st.markdown("---")
        st.subheader("Recent Bookings")
        
        if outfitter_bookings:
            df = pd.DataFrame(outfitter_bookings)
            df['field_name'] = df['field_id'].map(lambda x: st.session_state.fields[x]['name'])
            st.dataframe(df[['id', 'field_name', 'hunter_email', 'date', 'num_hunters', 'total_price', 'status']], 
                        use_container_width=True)
        else:
            st.info("No bookings yet")
    
    with tab2:
        st.header("Manage Fields")
        
        if st.button("➕ Add New Field"):
            st.session_state.show_add_field = True
        
        if st.session_state.get('show_add_field', False):
            with st.form("add_field_form"):
                st.subheader("Add New Field")
                col1, col2 = st.columns(2)
                with col1:
                    field_name = st.text_input("Field Name")
                    field_type = st.selectbox("Hunting Type", ["Red Deer Stalking", "Driven Grouse", "Pheasant & Partridge", "Duck & Goose"])
                    field_location = st.text_input("Location")
                    field_price = st.number_input("Price per Day (£)", min_value=0, value=300)
                with col2:
                    field_capacity = st.number_input("Capacity", min_value=1, value=4)
                    field_lat = st.number_input("Latitude", value=55.0)
                    field_lon = st.number_input("Longitude", value=-3.0)
                    field_season = st.text_input("Season", value="Aug-Dec")
                
                field_description = st.text_area("Description")
                
                if st.form_submit_button("Save Field"):
                    new_id = max(st.session_state.fields.keys()) + 1
                    st.session_state.fields[new_id] = {
                        'name': field_name,
                        'outfitter': user_data['name'],
                        'location': field_location,
                        'lat': field_lat,
                        'lon': field_lon,
                        'type': field_type,
                        'price_per_day': field_price,
                        'currency': 'GBP',
                        'capacity': field_capacity,
                        'description': field_description,
                        'amenities': [],
                        'season': field_season,
                        'image': 'https://images.unsplash.com/photo-1542273917363-3b1817f69a2d',
                        'available_dates': {},
            'blocked_dates': []
                    }
                    if 'fields' not in user_data:
                        user_data['fields'] = []
                    user_data['fields'].append(new_id)
                    st.session_state.show_add_field = False
                    st.success(f"Field '{field_name}' added successfully!")
                    st.rerun()
        
        st.markdown("---")
        
        for field_id in user_data.get('fields', []):
            if field_id in st.session_state.fields:
                field = st.session_state.fields[field_id]
                with st.expander(f"{field['name']} - {field['location']}", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"**Type:** {field['type']}")
                        st.markdown(f"**Season:** {field['season']}")
                        st.markdown(f"**Description:** {field['description']}")
                    with col2:
                        st.markdown(f"**Price:** £{field['price_per_day']}/day")
                        st.markdown(f"**Capacity:** {field['capacity']}")
                        if st.button("Edit", key=f"edit_{field_id}"):
                            st.info("Edit functionality coming soon")
    
    with tab3:
        st.header("Booking Management")
        
        outfitter_bookings = [b for b in st.session_state.bookings 
                              if st.session_state.fields[b['field_id']]['outfitter'] == user_data['name']]
        
        pending_bookings = [b for b in outfitter_bookings if b['status'] == 'pending']
        if pending_bookings:
            st.warning(f"⚠️ {len(pending_bookings)} booking(s) pending approval")
        
        if outfitter_bookings:
            for booking in outfitter_bookings:
                field = st.session_state.fields[booking['field_id']]
                status_color = {
                    'confirmed': '🟢',
                    'pending': '🟡',
                    'cancelled': '🔴',
                    'rejected': '🔴'
                }
                
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
                    with col1:
                        st.markdown(f"**Booking #{booking['id']}**")
                        st.markdown(f"Field: {field['name']}")
                    with col2:
                        st.markdown(f"**Hunter:** {booking['hunter_email']}")
                        st.markdown(f"**Date:** {booking['date']}")
                    with col3:
                        st.markdown(f"**Hunters:** {booking['num_hunters']}")
                        st.markdown(f"**Total:** £{booking['total_price']}")
                        if 'payment_id' in booking:
                            st.caption(f"Payment: {booking['payment_id'][:12]}...")
                    with col4:
                        st.markdown(f"**Status:** {status_color.get(booking['status'], '⚪')} {booking['status'].title()}")
                        if booking['status'] == 'pending':
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("✓", key=f"approve_{booking['id']}", help="Approve booking"):
                                    booking['status'] = 'confirmed'
                                    st.success("Booking approved!")
                                    st.rerun()
                            with col_b:
                                if st.button("✗", key=f"reject_{booking['id']}", help="Reject booking"):
                                    booking['status'] = 'rejected'
                                    st.info("Booking rejected. Payment will be refunded.")
                                    st.rerun()
                    st.markdown("---")
        else:
            st.info("No bookings yet")
    
    with tab4:
        st.header("Availability Management")
        
        st.markdown("Manage field availability and block specific dates.")
        
        field_id_select = st.selectbox(
            "Select Field",
            options=[fid for fid in user_data.get('fields', []) if fid in st.session_state.fields],
            format_func=lambda x: st.session_state.fields[x]['name']
        )
        
        if field_id_select:
            field = st.session_state.fields[field_id_select]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Block Dates")
                block_date = st.date_input("Select date to block", min_value=datetime.now())
                if st.button("Block Date"):
                    date_str = block_date.strftime("%Y-%m-%d")
                    if 'blocked_dates' not in field:
                        field['blocked_dates'] = []
                    if date_str not in field['blocked_dates']:
                        field['blocked_dates'].append(date_str)
                        st.success(f"Date {date_str} blocked successfully")
                        st.rerun()
                    else:
                        st.warning("Date is already blocked")
            
            with col2:
                st.subheader("Blocked Dates")
                if field.get('blocked_dates'):
                    for blocked_date in field['blocked_dates']:
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.text(blocked_date)
                        with col_b:
                            if st.button("Unblock", key=f"unblock_{blocked_date}"):
                                field['blocked_dates'].remove(blocked_date)
                                st.success("Date unblocked")
                                st.rerun()
                else:
                    st.info("No blocked dates")
            
            st.markdown("---")
            st.subheader("Upcoming Bookings for this Field")
            
            field_bookings = [b for b in st.session_state.bookings 
                            if b['field_id'] == field_id_select 
                            and b['status'] in ['confirmed', 'pending']]
            
            if field_bookings:
                df_bookings = pd.DataFrame(field_bookings)
                df_bookings = df_bookings.sort_values('date')
                st.dataframe(df_bookings[['date', 'num_hunters', 'status', 'hunter_email']], 
                           use_container_width=True)
                
                st.markdown("**Capacity Overview**")
                for booking in sorted(field_bookings, key=lambda x: x['date']):
                    bookings_same_date = [b for b in field_bookings if b['date'] == booking['date']]
                    total_hunters = sum(b['num_hunters'] for b in bookings_same_date)
                    remaining = field['capacity'] - total_hunters
                    
                    progress = total_hunters / field['capacity']
                    st.markdown(f"**{booking['date']}**: {total_hunters}/{field['capacity']} hunters")
                    st.progress(progress)
            else:
                st.info("No upcoming bookings for this field")
    
    with tab5:
        st.header("Analytics")
        
        outfitter_bookings = [b for b in st.session_state.bookings 
                              if st.session_state.fields[b['field_id']]['outfitter'] == user_data['name']]
        
        if outfitter_bookings:
            df = pd.DataFrame(outfitter_bookings)
            df['field_name'] = df['field_id'].map(lambda x: st.session_state.fields[x]['name'])
            
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

def admin_dashboard():
    st.title("⚙️ Admin Dashboard")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Platform Overview", "User Management", "Booking Management", "Analytics"])
    
    with tab1:
        st.header("Platform Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Users", len(st.session_state.users))
        with col2:
            st.metric("Total Fields", len(st.session_state.fields))
        with col3:
            st.metric("Total Bookings", len(st.session_state.bookings))
        with col4:
            total_revenue = sum(b['total_price'] for b in st.session_state.bookings if b['status'] == 'confirmed')
            st.metric("Total Revenue", f"£{total_revenue:,}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("User Distribution")
            role_counts = {}
            for user in st.session_state.users.values():
                role = user['role']
                role_counts[role] = role_counts.get(role, 0) + 1
            
            df_roles = pd.DataFrame(list(role_counts.items()), columns=['Role', 'Count'])
            fig = px.pie(df_roles, values='Count', names='Role', title="Users by Role")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Platform Activity")
            if st.session_state.bookings:
                df_bookings = pd.DataFrame(st.session_state.bookings)
                df_bookings['date'] = pd.to_datetime(df_bookings['date'])
                bookings_by_date = df_bookings.groupby('date').size().reset_index(name='count')
                fig = px.line(bookings_by_date, x='date', y='count', title="Bookings Over Time")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No booking data yet")
    
    with tab2:
        st.header("User Management")
        
        st.subheader("All Users")
        users_list = []
        for email, data in st.session_state.users.items():
            users_list.append({
                'Email': email,
                'Name': data['name'],
                'Role': data['role'],
                'Phone': data['phone'],
                'Location': data['location']
            })
        
        df_users = pd.DataFrame(users_list)
        st.dataframe(df_users, use_container_width=True)
        
        st.markdown("---")
        
        with st.expander("Add New User"):
            with st.form("add_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_email = st.text_input("Email")
                    new_name = st.text_input("Name")
                    new_password = st.text_input("Password", type="password")
                with col2:
                    new_role = st.selectbox("Role", ["hunter", "outfitter", "admin"])
                    new_phone = st.text_input("Phone")
                    new_location = st.text_input("Location")
                
                if st.form_submit_button("Add User"):
                    if new_email and new_email not in st.session_state.users:
                        st.session_state.users[new_email] = {
                            'password': new_password,
                            'role': new_role,
                            'name': new_name,
                            'phone': new_phone,
                            'location': new_location,
                            'bookings': [] if new_role == 'hunter' else None,
                            'fields': [] if new_role == 'outfitter' else None
                        }
                        st.success(f"User {new_email} added successfully!")
                        st.rerun()
                    else:
                        st.error("Email already exists or is invalid")
    
    with tab3:
        st.header("Booking Management")
        
        if st.session_state.bookings:
            df_bookings = pd.DataFrame(st.session_state.bookings)
            df_bookings['field_name'] = df_bookings['field_id'].map(lambda x: st.session_state.fields[x]['name'])
            
            st.dataframe(df_bookings[['id', 'field_name', 'hunter_email', 'date', 'num_hunters', 
                                      'total_price', 'status', 'created_at']], use_container_width=True)
            
            st.markdown("---")
            st.subheader("Manage Bookings")
            
            for booking in st.session_state.bookings:
                field = st.session_state.fields[booking['field_id']]
                with st.expander(f"Booking #{booking['id']} - {field['name']} ({booking['status']})"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**Field:** {field['name']}")
                        st.markdown(f"**Hunter:** {booking['hunter_email']}")
                        st.markdown(f"**Date:** {booking['date']}")
                        st.markdown(f"**Hunters:** {booking['num_hunters']}")
                        st.markdown(f"**Total:** £{booking['total_price']}")
                        st.markdown(f"**Created:** {booking['created_at']}")
                    with col2:
                        status_options = ["confirmed", "pending", "cancelled", "rejected"]
                        current_status = booking['status']
                        if current_status in status_options:
                            current_index = status_options.index(current_status)
                        else:
                            current_index = 0
                        
                        new_status = st.selectbox("Status", status_options, 
                                                 index=current_index,
                                                 key=f"status_{booking['id']}")
                        if st.button("Update", key=f"update_{booking['id']}"):
                            booking['status'] = new_status
                            st.success("Status updated!")
                            st.rerun()
        else:
            st.info("No bookings in the system yet")
    
    with tab4:
        st.header("Platform Analytics")
        
        if st.session_state.bookings:
            df = pd.DataFrame(st.session_state.bookings)
            df['field_name'] = df['field_id'].map(lambda x: st.session_state.fields[x]['name'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Revenue by Field")
                revenue_by_field = df[df['status'] == 'confirmed'].groupby('field_name')['total_price'].sum().reset_index()
                fig = px.bar(revenue_by_field, x='field_name', y='total_price',
                           title="Total Revenue by Field",
                           labels={'total_price': 'Revenue (£)', 'field_name': 'Field'})
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Booking Status Distribution")
                status_count = df['status'].value_counts().reset_index()
                status_count.columns = ['Status', 'Count']
                fig = px.pie(status_count, values='Count', names='Status', 
                           title="Bookings by Status")
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Top Performing Fields")
            top_fields = df[df['status'] == 'confirmed'].groupby('field_name').agg({
                'id': 'count',
                'total_price': 'sum'
            }).reset_index()
            top_fields.columns = ['Field', 'Bookings', 'Revenue']
            top_fields = top_fields.sort_values('Revenue', ascending=False)
            st.dataframe(top_fields, use_container_width=True)
            
            st.subheader("Monthly Revenue Trend")
            df['date'] = pd.to_datetime(df['date'])
            df['month'] = df['date'].dt.to_period('M').astype(str)
            monthly_revenue = df[df['status'] == 'confirmed'].groupby('month')['total_price'].sum().reset_index()
            fig = go.Figure(data=[go.Bar(x=monthly_revenue['month'], y=monthly_revenue['total_price'])])
            fig.update_layout(title="Monthly Revenue", xaxis_title="Month", yaxis_title="Revenue (£)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for analytics yet")

def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        user_data = st.session_state.users[st.session_state.current_user]
        
        with st.sidebar:
            st.title("🦌 Fieldsport Platform")
            st.markdown(f"**Logged in as:** {user_data['name']}")
            st.markdown(f"**Role:** {user_data['role'].title()}")
            st.markdown("---")
            
            if st.button("Logout", use_container_width=True):
                logout()
        
        if st.session_state.user_role == 'hunter':
            hunter_dashboard()
        elif st.session_state.user_role == 'outfitter':
            outfitter_dashboard()
        elif st.session_state.user_role == 'admin':
            admin_dashboard()

if __name__ == "__main__":
    main()
