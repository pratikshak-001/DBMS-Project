TicketEase frontend — matched to your supplied backend
======================================================

1. Update the MySQL password in app.py (password="your_password") to your actual local MySQL password.
2. Make sure your ticket_booking database and tables exist. Warning: the supplied SQL script begins with DROP DATABASE IF EXISTS ticket_booking; running it deletes/recreates that database.
3. Install dependencies in the same Python environment:
   python -m pip install -r requirements.txt
4. In the backend folder, run:
   python app.py
   The Flask server uses port 5001.
5. In this frontend folder, run:
   python -m http.server 5500
6. Open http://127.0.0.1:5500

This frontend calls GET /api/shows and POST /api/bookings at http://127.0.0.1:5001.
It does not show fabricated demo events if the API fails.
Booking requires an existing User_ID, a Seat_ID at the show's venue, ticket type and price.
The SQL seed data includes User_ID 3 (Pratiksha) and venues/seats; confirm IDs in your own database before booking.

Known backend limitations:
- The supplied app.py has no /api/login or /api/register routes, so the UI buttons explain that those features are not implemented.
- The booking route accepts one seat per request, so the ticket quantity selector is intentionally fixed to 1.
- The backend marks payment as Success automatically and does not integrate a real payment gateway.
- app.py currently allows CORS globally with CORS(app), suitable for a local college demo but should be restricted for production.
