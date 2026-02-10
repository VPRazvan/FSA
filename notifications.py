import os
from typing import Optional
from datetime import datetime
from database import User, Field, Booking

def format_booking_date(booking_date) -> str:
    """
    Safely format booking date whether it's a string, date, or datetime object.
    """
    if booking_date is None:
        return 'TBD'
    
    if isinstance(booking_date, str):
        try:
            date_obj = datetime.strptime(booking_date, '%Y-%m-%d')
            return date_obj.strftime('%B %d, %Y')
        except:
            return booking_date
    
    if hasattr(booking_date, 'strftime'):
        return booking_date.strftime('%B %d, %Y')
    
    return str(booking_date)

class EmailNotificationService:
    """
    Email notification service for booking lifecycle events.
    Currently logs emails to console. Can be upgraded to use SendGrid, Resend, or SMTP.
    """
    
    def __init__(self):
        self.email_backend = os.getenv("EMAIL_BACKEND", "console")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@fieldsport-booking.com")
    
    def _send_email(self, to_email: str, subject: str, body: str):
        """
        Send email using configured backend.
        For now, logs to console. Can be upgraded to real email service.
        """
        if self.email_backend == "console":
            print("\n" + "="*80)
            print(f"📧 EMAIL NOTIFICATION")
            print("="*80)
            print(f"To: {to_email}")
            print(f"From: {self.from_email}")
            print(f"Subject: {subject}")
            print("-"*80)
            print(body)
            print("="*80 + "\n")
        else:
            # Future: Add SendGrid, Resend, or SMTP implementation
            pass
    
    def send_booking_created_to_hunter(self, hunter: User, booking: Booking, field: Field, outfitter: User):
        """
        Notify hunter that their booking request was created successfully.
        """
        subject = f"Booking Request Created - {field.name}"
        
        body = f"""
Dear {hunter.name},

Your booking request has been successfully created!

BOOKING DETAILS:
----------------
Field: {field.name}
Location: {field.location}
Hunting Type: {field.type}
Date: {format_booking_date(booking.date)}
Number of Hunters: {booking.num_hunters}
Total Price: £{booking.total_price}
Status: PENDING APPROVAL

WHAT'S NEXT:
The outfitter ({outfitter.name}) will review your request and respond within 24-48 hours.
You will receive an email notification once they approve or decline your booking.

Outfitter Contact: {outfitter.phone}

Thank you for using the Fieldsport Booking Platform!

Best regards,
The Fieldsport Team
        """
        
        self._send_email(hunter.email, subject, body)
    
    def send_booking_created_to_outfitter(self, hunter: User, booking: Booking, field: Field, outfitter: User):
        """
        Notify outfitter that they have a new booking request to review.
        """
        subject = f"New Booking Request - {field.name}"
        
        body = f"""
Dear {outfitter.name},

You have received a new booking request for your field!

BOOKING DETAILS:
----------------
Field: {field.name}
Hunter: {hunter.name}
Contact: {hunter.email} | {hunter.phone}
Date: {format_booking_date(booking.date)}
Number of Hunters: {booking.num_hunters}
Total Price: £{booking.total_price}
Status: PENDING YOUR APPROVAL

ACTION REQUIRED:
Please log in to your outfitter dashboard to review and approve or decline this booking request.
Dashboard: https://fieldsport-booking.replit.app

Hunter's Message: {hunter.location}

Best regards,
The Fieldsport Team
        """
        
        self._send_email(outfitter.email, subject, body)
    
    def send_booking_approved_to_hunter(self, hunter: User, booking: Booking, field: Field, outfitter: User):
        """
        Notify hunter that their booking was approved.
        """
        subject = f"Booking Approved - {field.name}"
        
        body = f"""
Dear {hunter.name},

Great news! Your booking has been APPROVED!

BOOKING DETAILS:
----------------
Field: {field.name}
Location: {field.location}
Hunting Type: {field.type}
Date: {format_booking_date(booking.date)}
Number of Hunters: {booking.num_hunters}
Total Price: £{booking.total_price}
Status: CONFIRMED

NEXT STEPS:
1. Payment: Your payment of £{booking.total_price} has been processed
2. Preparation: Review the field amenities and prepare accordingly
3. Contact: Reach out to the outfitter if you have any questions

Outfitter Contact:
Name: {outfitter.name}
Phone: {outfitter.phone}
Email: {outfitter.email}

WHAT TO BRING:
{', '.join(field.amenities) if field.amenities else 'Check with outfitter for specific requirements'}

We hope you have an excellent hunting experience!

Best regards,
The Fieldsport Team
        """
        
        self._send_email(hunter.email, subject, body)
    
    def send_booking_rejected_to_hunter(self, hunter: User, booking: Booking, field: Field, outfitter: User):
        """
        Notify hunter that their booking was rejected.
        """
        subject = f"Booking Update - {field.name}"
        
        body = f"""
Dear {hunter.name},

We regret to inform you that your booking request was not approved.

BOOKING DETAILS:
----------------
Field: {field.name}
Location: {field.location}
Date: {format_booking_date(booking.date)}
Number of Hunters: {booking.num_hunters}
Status: DECLINED

WHAT'S NEXT:
The date you requested may not be available, or the outfitter may have specific requirements.
We encourage you to:
1. Try booking a different date
2. Browse other available fields in the area
3. Contact the outfitter directly: {outfitter.phone}

Don't worry - there are many other excellent hunting opportunities available on our platform!

Browse Available Fields: https://fieldsport-booking.replit.app

Best regards,
The Fieldsport Team
        """
        
        self._send_email(hunter.email, subject, body)
    
    def send_booking_cancelled_to_outfitter(self, hunter: User, booking: Booking, field: Field, outfitter: User):
        """
        Notify outfitter that a booking was cancelled.
        """
        subject = f"Booking Cancelled - {field.name}"
        
        body = f"""
Dear {outfitter.name},

A confirmed booking has been cancelled.

BOOKING DETAILS:
----------------
Field: {field.name}
Hunter: {hunter.name}
Date: {format_booking_date(booking.date)}
Number of Hunters: {booking.num_hunters}
Previous Status: CONFIRMED → CANCELLED

This date is now available for other bookings.

Best regards,
The Fieldsport Team
        """
        
        self._send_email(outfitter.email, subject, body)
    
    def send_hunt_started_to_admin(self, hunter: User, field: Field, booking: Booking):
        """
        Notify admin that a hunt has started.
        """
        admin_email = os.getenv("ADMIN_EMAIL", "admin@fieldsport-booking.com")
        subject = f"Hunt Started - {field.name}"
        
        body = f"""
Dear Admin,

A hunt session has been started on the platform.

HUNT SESSION DETAILS:
--------------------
Field: {field.name}
Location: {field.location}
Hunter: {hunter.name}
Contact: {hunter.email} | {hunter.phone}
Date: {format_booking_date(booking.date)}
Number of Hunters: {booking.num_hunters}
Start Time: {datetime.now().strftime('%H:%M on %B %d, %Y')}

This is an automated notification for platform monitoring.

Best regards,
The Fieldsport System
        """
        
        self._send_email(admin_email, subject, body)
    
    def send_hunt_started_to_landowner(self, hunter: User, field: Field, booking: Booking, landowner: User):
        """
        Notify landowner that a hunt has started on their property.
        """
        subject = f"Hunt Started - {field.name}"
        
        body = f"""
Dear {landowner.name},

The scheduled hunt on your property has begun.

HUNT SESSION DETAILS:
--------------------
Field: {field.name}
Hunter: {hunter.name}
Contact: {hunter.email} | {hunter.phone}
Date: {format_booking_date(booking.date)}
Number of Hunters: {booking.num_hunters}
Start Time: {datetime.now().strftime('%H:%M on %B %d, %Y')}

The hunter has checked in and started their session. You will receive another notification when the hunt is completed with a full report.

If you have any questions or concerns, please contact the hunter directly or our support team.

Best regards,
The Fieldsport Team
        """
        
        self._send_email(landowner.email, subject, body)

# Singleton instance
email_service = EmailNotificationService()
