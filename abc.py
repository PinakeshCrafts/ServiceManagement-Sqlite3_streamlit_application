import random
import sqlite3
from datetime import date, datetime

import streamlit as st

DB_PATH = "service.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS customer (
                user_id INTEGER PRIMARY KEY,
                user_name TEXT,
                email TEXT,
                password TEXT,
                address TEXT,
                contact_no TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS booking (
                booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service_type TEXT,
                booking_date TEXT,
                slot TEXT,
                vendor TEXT,
                amount INTEGER,
                status TEXT
            )
            """
        )
        conn.commit()


def register_customer(user_name, email, password, address, contact_no):
    user_id = random.randint(1000000, 9999999)

    with get_connection() as conn:
        existing = conn.execute("SELECT 1 FROM customer WHERE email = ?", (email,)).fetchone()
        if existing:
            return False, "Email already registered"

        conn.execute(
            "INSERT INTO customer (user_id, user_name, email, password, address, contact_no) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, user_name, email, password, address, contact_no),
        )
        conn.commit()

    return True, user_id


def login_customer(user_id, password):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM customer WHERE user_id = ? AND password = ?",
            (user_id, password),
        ).fetchone()

    if row:
        return dict(row)
    return None


def book_service(user_id, service_type, booking_date, slot, vendor, amount):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO booking (user_id, service_type, booking_date, slot, vendor, amount, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, service_type, booking_date, slot, vendor, amount, "Booked"),
        )
        conn.commit()


def get_booking_history(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT booking_id, service_type, booking_date, slot, vendor, amount, status
            FROM booking
            WHERE user_id = ?
            ORDER BY booking_id DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_booking(booking_id, service_type, booking_date, slot, vendor, amount):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE booking
            SET service_type = ?, booking_date = ?, slot = ?, vendor = ?, amount = ?
            WHERE booking_id = ?
            """,
            (service_type, booking_date, slot, vendor, amount, booking_id),
        )
        conn.commit()


def delete_booking(booking_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM booking WHERE booking_id = ?", (booking_id,))
        conn.commit()


st.set_page_config(page_title="Home Service App", page_icon="🛠️", layout="centered")
create_tables()

if "customer" not in st.session_state:
    st.session_state.customer = None

st.title("Home Service Booking")
st.caption("Book mobile and home appliance services with a simple Streamlit UI")

if st.session_state.customer is None:
    st.subheader("Register or Login")
    tab1, tab2 = st.tabs(["Register", "Login"])

    with tab1:
        with st.form("register_form"):
            name = st.text_input("Name")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            address = st.text_area("Address")
            contact = st.text_input("Contact Number")
            submitted = st.form_submit_button("Register")

            if submitted:
                if not all([name, email, password, address, contact]):
                    st.warning("Please fill in all fields")
                else:
                    success, result = register_customer(name, email, password, address, contact)
                    if success:
                        st.success(f"Registration successful! Your User ID is {result}")
                    else:
                        st.error(result)

    with tab2:
        with st.form("login_form"):
            user_id = st.number_input("User ID", min_value=1000000, max_value=9999999, step=1)
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                customer = login_customer(int(user_id), password)
                if customer:
                    st.session_state.customer = customer
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
else:
    customer = st.session_state.customer
    st.success(f"Logged in as {customer['user_name']} (User ID: {customer['user_id']})")
    if st.button("Logout"):
        st.session_state.customer = None
        st.rerun()

    st.divider()
    st.subheader("Book a Service")

    with st.form("booking_form"):
        service_type = st.selectbox(
            "Service",
            ["AC Repair", "TV Repair", "Fridge Repair", "Washing Machine Repair", "Microwave Repair"],
        )
        booking_date = st.date_input("Preferred Date", min_value=date.today())
        slot = st.text_input("Time Slot")
        vendor = st.selectbox("Vendor", ["Vendor A", "Vendor B", "Vendor C"])
        amount_map = {"Vendor A": 500, "Vendor B": 700, "Vendor C": 1000}
        submitted = st.form_submit_button("Book Service")

        if submitted:
            if slot.strip():
                book_service(
                    customer["user_id"],
                    service_type,
                    booking_date.strftime("%d-%m-%Y"),
                    slot.strip(),
                    vendor,
                    amount_map[vendor],
                )
                st.success("Booking placed successfully")
                st.rerun()
            else:
                st.warning("Please enter a time slot")

    st.divider()
    st.subheader("Booking History")
    history = get_booking_history(customer["user_id"])

    if history:
        st.dataframe(history, use_container_width=True, hide_index=True)

        st.subheader("Manage Bookings")
        booking_options = {
            f"{row['booking_id']} - {row['service_type']} ({row['booking_date']})": row for row in history
        }
        selected_key = st.selectbox("Select a booking to edit", list(booking_options.keys()))
        selected_booking = booking_options[selected_key]

        with st.form("edit_booking_form"):
            edit_service_type = st.selectbox(
                "Service",
                ["AC Repair", "TV Repair", "Fridge Repair", "Washing Machine Repair", "Microwave Repair"],
                index=["AC Repair", "TV Repair", "Fridge Repair", "Washing Machine Repair", "Microwave Repair"].index(selected_booking["service_type"]),
            )
            edit_date = st.date_input(
                "Preferred Date",
                value=datetime.strptime(selected_booking["booking_date"], "%d-%m-%Y").date(),
            )
            edit_slot = st.text_input("Time Slot", value=selected_booking["slot"])
            edit_vendor = st.selectbox(
                "Vendor",
                ["Vendor A", "Vendor B", "Vendor C"],
                index=["Vendor A", "Vendor B", "Vendor C"].index(selected_booking["vendor"]),
            )
            amount_map = {"Vendor A": 500, "Vendor B": 700, "Vendor C": 1000}
            col1, col2 = st.columns(2)
            update_clicked = col1.form_submit_button("Update Booking")
            delete_clicked = col2.form_submit_button("Delete Booking")

            if update_clicked:
                if edit_slot.strip():
                    update_booking(
                        selected_booking["booking_id"],
                        edit_service_type,
                        edit_date.strftime("%d-%m-%Y"),
                        edit_slot.strip(),
                        edit_vendor,
                        amount_map[edit_vendor],
                    )
                    st.success("Booking updated successfully")
                    st.rerun()
                else:
                    st.warning("Please enter a time slot")

            if delete_clicked:
                delete_booking(selected_booking["booking_id"])
                st.success("Booking deleted successfully")
                st.rerun()
    else:
        st.info("No bookings yet")