# Fieldsports Alliance

## Overview
Fieldsports Alliance is a digital marketplace connecting fieldsport enthusiasts with landowners and guides globally. It offers DIY-Leased Grounds, Subsidised Grounds, and International Opportunities. The platform features multi-role user management, field discovery with map-based search, booking and payment processing, a member forum, and admin-controlled land creation. The vision is to be the leading platform for fieldsport adventures, enhancing accessibility and efficiency.

## Recent Changes (November 6, 2025)

### Field Deletion Functionality
- **Admin Field Management**: Added field deletion capability with safety measures
  * Two-step confirmation process (Delete → Confirm Delete)
  * Clear warning about permanent data removal
  * Cascading deletion of all associated data (bookings, hunt sessions, hunt reports)
  * Cancel option to abort deletion
  * Success/error feedback after deletion attempt
- **Database Function**: Created `delete_field()` in db_helpers.py
  * Removes all bookings for the field
  * Deletes all hunt sessions and associated hunt reports
  * Removes the field record
  * Returns boolean indicating success/failure

### Carousel Image Display
- **Fixed carousel image rendering**: Switched from st.image() to HTML img tags for reliable styling
  * Fixed 280px height with object-fit: cover for consistent presentation
  * All field cards now align perfectly in grid layout
  * Works with both remote URLs (Unsplash) and local uploaded images
  * Dedicated CSS wrapper (.field-carousel-container) for scoped styling

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### UI/UX Decisions
The current frontend uses Streamlit for rapid prototyping, featuring session-based state management, Plotly for interactive visualizations, and Folium for map integration. The target architecture aims for responsive web and mobile frontends, supporting multi-language interfaces. UI elements like image carousels, certification displays, and vehicle management have been redesigned for improved user experience.

### Technical Implementations
The system is currently a monolithic Streamlit application with a PostgreSQL database and SQLAlchemy ORM. Authentication uses bcrypt. The target architecture is a microservices-based system built with NestJS, orchestrated by Kubernetes, aiming for high scalability and an API response time under 200ms.

### Feature Specifications
- **User Management:** Five user types (Shooting Member, International Hunter, Landowner Member, Guide Member, Admin) with distinct permissions, self-service registration, and compliance enforcement.
- **Field Discovery & Booking:** Advanced filtering, detailed field pages with calendar, booking history, location, reviews, and ground rules. Role-based pricing, `auto_approve_bookings` toggle, and double-booking prevention.
- **Hunt Session Workflow & Reporting:** Manages hunt lifecycle from "Start Day" to "Finish Hunt," including automatic session creation and comprehensive reporting with detailed animal data capture (species, condition, disease, tag), ground remarks, and public reviews. Multi-species quota management for DIY fields.
- **Hunter Certifications & Membership:** Tracks certifications (DSC1, DSC2, FAC, shotgun) and fieldsport association memberships with expiry dates.
- **Booking Management:** Outfitters see comprehensive hunter information for review.
- **Admin Tools:** Analytics dashboard, field visit analytics, harvested animal data tracking, user management, and booking management with override capabilities. Includes a dedicated field management tab for creating, assigning, and updating fields, and managing landowner requests.
- **Member Forum System:** Classified-style forum with categories, post creation (discussion, for sale, wanted, advice), reply system, and view counters.
- **Review System:** Allows review editing, features "Verified Hunt" badges, and includes an admin moderation dashboard.
- **QR Code Animal Tagging System:** Complete animal traceability with unique UUIDs and QR codes for harvested animals, supporting photo capture, species/condition/disease tracking, and a public verification page.
- **Landowner Dashboard:** Role-specific dashboard with read-only field access, custom analytics (bookings, visits, culls, survey reports), and a land request submission workflow.

### System Design Choices
- **Authentication & Authorization:** Email/password authentication with bcrypt and session-based role-based access control. Target includes OAuth 2.0 and GDPR compliance. Non-compliant users are blocked.
- **Data Architecture:** PostgreSQL with PostGIS for geospatial queries, managed by SQLAlchemy. Key tables include `users`, `fields`, `bookings`, `payment_tokens`, `hunt_sessions`, `hunt_reports`, `ForumCategory`, `ForumPost`, `ForumReply`, `LandOwnerRequest`, and `AnimalTag`.
- **System Performance & Scalability:** Target goals include 99.9% uptime, horizontal scaling via Kubernetes, distributed caching with Redis, and load balancing.

## External Dependencies

-   **Streamlit**: Python web application framework.
-   **PostgreSQL**: Primary relational database with PostGIS.
-   **SQLAlchemy**: Python ORM.
-   **bcrypt**: Password hashing.
-   **Pandas**: Data manipulation.
-   **Plotly Express & Graph Objects**: Interactive data visualization.
-   **Folium & streamlit-folium**: Map integration.
-   **Stripe API**: Planned for payment processing.
-   **AWS**: Planned primary cloud provider.
-   **Redis**: Planned for caching.
-   **Elasticsearch**: Planned for advanced search.
-   **NestJS**: Planned backend framework.