from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
from datetime import date, datetime, time, timedelta
from decimal import Decimal

app = Flask(__name__)
CORS(app)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Pratisql26",
        database="ticket_booking",
        autocommit=True
    )

def convert_value(value):
    """Convert MySQL values into JSON-serializable values."""
    if isinstance(value, timedelta):
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    if isinstance(value, (datetime, date, time)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, dict):
        return {key: convert_value(item) for key, item in value.items()}

    if isinstance(value, (list, tuple)):
        return [convert_value(item) for item in value]

    return value

def json_response(data, status=200):
    return jsonify(convert_value(data)), status

@app.route("/api/shows", methods=["GET"])
def get_shows():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                sh.Show_ID,
                e.Event_Name,
                e.Event_Type,
                v.Venue_Name,
                v.Location,
                sh.Show_Date,
                sh.Start_Time,
                sh.End_Time
            FROM `Show` sh
            JOIN Event e ON e.Event_ID = sh.Event_ID
            JOIN Venue v ON v.Venue_ID = sh.Venue_ID
            WHERE sh.Show_Date >= CURDATE()
            ORDER BY sh.Show_Date, sh.Start_Time
        """
        cursor.execute(query)
        shows = cursor.fetchall()
        return json_response(shows)

    except Error as err:
        app.logger.exception("Error fetching shows")
        return json_response({"error": str(err)}, 500)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()

@app.route("/api/events", methods=["GET"])
def get_events():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Event ORDER BY Event_ID")
        events = cursor.fetchall()
        return json_response(events)

    except Error as err:
        app.logger.exception("Error fetching events")
        return json_response({"error": str(err)}, 500)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()

@app.route("/api/venues", methods=["GET"])
def get_venues():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Venue ORDER BY Venue_ID")
        venues = cursor.fetchall()
        return json_response(venues)

    except Error as err:
        app.logger.exception("Error fetching venues")
        return json_response({"error": str(err)}, 500)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()

@app.route("/api/bookings", methods=["POST"])
def create_booking():
    data = request.get_json(silent=True) or {}

    user_id = data.get("user_id")
    show_id = data.get("show_id")
    seat_id = data.get("seat_id")
    ticket_type = data.get("ticket_type", "Standard")
    price = data.get("price")

    if user_id is None or show_id is None or seat_id is None or price is None:
        return json_response({
            "error": "user_id, show_id, seat_id, and price are required"
        }, 400)

    try:
        price = float(price)
        if price < 0:
            raise ValueError
    except (TypeError, ValueError):
        return json_response({
            "error": "price must be a valid non-negative number"
        }, 400)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT User_ID FROM `User` WHERE User_ID = %s",
            (user_id,)
        )
        if cursor.fetchone() is None:
            return json_response({"error": "User not found"}, 404)

        cursor.execute("""
            SELECT s.Seat_ID, sh.Venue_ID, sh.Show_ID
            FROM Seat s
            JOIN `Show` sh ON sh.Venue_ID = s.Venue_ID
            WHERE s.Seat_ID = %s AND sh.Show_ID = %s
        """, (seat_id, show_id))

        if cursor.fetchone() is None:
            return json_response({
                "error": "Seat does not belong to this show's venue"
            }, 400)

        cursor.execute("""
            SELECT 1
            FROM Ticket
            WHERE Show_ID = %s
              AND Seat_ID = %s
              AND Ticket_Status <> 'Cancelled'
        """, (show_id, seat_id))

        if cursor.fetchone() is not None:
            return json_response({
                "error": "Seat already booked for this show"
            }, 409)

        cursor.execute(
            "INSERT INTO Booking (User_ID, Status) VALUES (%s, 'Pending')",
            (user_id,)
        )
        booking_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO Ticket
                (Booking_ID, Show_ID, Seat_ID, Ticket_Type, Price, Ticket_Status)
            VALUES (%s, %s, %s, %s, %s, 'Valid')
        """, (booking_id, show_id, seat_id, ticket_type, price))

        cursor.execute("""
            INSERT INTO Payment
                (Booking_ID, Amount, Payment_Method, Payment_Status)
            VALUES (%s, %s, 'UPI', 'Success')
        """, (booking_id, price))

        if not conn.autocommit:
            conn.commit()

        return json_response({
            "message": "Booking created successfully",
            "booking_id": booking_id,
            "show_id": show_id,
            "seat_id": seat_id,
            "status": "Confirmed"
        }, 201)

    except Error as err:
        if conn is not None and conn.is_connected() and not conn.autocommit:
            conn.rollback()
        app.logger.exception("Error creating booking")
        return json_response({"error": str(err)}, 500)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()

@app.route("/api/bookings/<int:user_id>", methods=["GET"])
def get_user_bookings(user_id):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                b.Booking_ID,
                b.Status AS Booking_Status,
                b.Booking_Date,
                b.Total_Amount,
                GROUP_CONCAT(
                    CONCAT(
                        t.Ticket_ID, ':', e.Event_Name, ' - ', v.Venue_Name
                    )
                    ORDER BY t.Ticket_ID SEPARATOR '; '
                ) AS ticket_summary
            FROM Booking b
            LEFT JOIN Ticket t ON t.Booking_ID = b.Booking_ID
            LEFT JOIN `Show` sh ON sh.Show_ID = t.Show_ID
            LEFT JOIN Event e ON e.Event_ID = sh.Event_ID
            LEFT JOIN Venue v ON v.Venue_ID = sh.Venue_ID
            WHERE b.User_ID = %s
            GROUP BY
                b.Booking_ID, b.Status, b.Booking_Date, b.Total_Amount
            ORDER BY b.Booking_Date DESC
        """
        cursor.execute(query, (user_id,))
        bookings = cursor.fetchall()
        return json_response(bookings)

    except Error as err:
        app.logger.exception("Error fetching user bookings")
        return json_response({"error": str(err)}, 500)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()

@app.route("/api/health", methods=["GET"])
def health_check():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return json_response({"status": "ok", "database": "connected"})

    except Error as err:
        app.logger.exception("Database health check failed")
        return json_response({
            "status": "error",
            "database": "disconnected",
            "error": str(err)
        }, 500)

    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
