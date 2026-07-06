import random
import sqlite3
from datetime import date, datetime

import streamlit as st

DB_PATH = "service.db"
SLOT_OPTIONS = ["09:00-11:00", "11:00-13:00", "15:00-17:00"]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = connect()
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
    conn.close()


def register_customer(user_name, email, password, address, contact_no):
    user_id = random.randint(1000000, 9999999)
    conn = connect()
    existing = conn.execute("SELECT 1 FROM customer WHERE email = ?", (email,)).fetchone()

    if existing:
        conn.close()
        return False, "Email already registered"

    conn.execute(
        "INSERT INTO customer (user_id, user_name, email, password, address, contact_no) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, user_name, email, password, address, contact_no),
    )
    conn.commit()
    conn.close()
    return True, user_id


def login_customer(user_id, password):
    conn = connect()
    row = conn.execute(
        "SELECT * FROM customer WHERE user_id = ? AND password = ?",
        (user_id, password),
    ).fetchone()
    conn.close()

    if row:
        return dict(row)
    return None


def book_service(user_id, service_type, booking_date, slot, vendor, amount):
    conn = connect()
    conn.execute(
        "INSERT INTO booking (user_id, service_type, booking_date, slot, vendor, amount, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, service_type, booking_date, slot, vendor, amount, "Booked"),
    )
    conn.commit()
    conn.close()


def get_booking_history(user_id):
    conn = connect()
    rows = conn.execute(
        "SELECT booking_id, service_type, booking_date, slot, vendor, amount, status FROM booking WHERE user_id = ? ORDER BY booking_id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def update_booking(booking_id, service_type, booking_date, slot, vendor, amount):
    conn = connect()
    conn.execute(
        "UPDATE booking SET service_type = ?, booking_date = ?, slot = ?, vendor = ?, amount = ? WHERE booking_id = ?",
        (service_type, booking_date, slot, vendor, amount, booking_id),
    )
    conn.commit()
    conn.close()


def delete_booking(booking_id):
    conn = connect()
    conn.execute("DELETE FROM booking WHERE booking_id = ?", (booking_id,))
    conn.commit()
    conn.close()


def slot_is_free(service_type, booking_date, slot, booking_id=None):
    conn = connect()
    if booking_id is None:
        row = conn.execute(
            "SELECT 1 FROM booking WHERE service_type = ? AND booking_date = ? AND slot = ?",
            (service_type, booking_date, slot),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM booking WHERE service_type = ? AND booking_date = ? AND slot = ? AND booking_id != ?",
            (service_type, booking_date, slot, booking_id),
        ).fetchone()
    conn.close()
    return row is None


st.set_page_config(page_title="Home Service App", page_icon="🛠️", layout="centered")
create_tables()

if "customer" not in st.session_state:
    st.session_state.customer = None

st.title("SERVICE MANAGEMENT SYSTEM")

if st.session_state.customer is None:
    st.subheader("Register or Login")
    st.write("")
    st.write("Register")

    with st.form("register_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        password = st.text_input("Password")
        address = st.text_area("Address")
        contact = st.text_input("Contact Number")
        submitted = st.form_submit_button("Register")

        if submitted:
            if name and email and password and address and contact:
                success, result = register_customer(name, email, password, address, contact)
                if success:
                    st.success(f"Registration successful! Your User ID is {result}")
                else:
                    st.error(result)
            else:
                st.warning("Please fill in all fields")

    st.write("")
    st.write("Login")

    with st.form("login_form"):
        user_id = st.text_input("User ID")
        password = st.text_input("Password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if user_id.strip():
                customer = login_customer(int(user_id), password)
                if customer:
                    st.session_state.customer = customer
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
            else:
                st.warning("Please enter your user ID")
else:
    customer = st.session_state.customer
    st.success(f"Logged in as {customer['user_name']} (User ID: {customer['user_id']})")

    if st.button("Logout"):
        st.session_state.customer = None
        st.rerun()

    st.divider()
    st.subheader("Book a Service")

    with st.form("booking_form"):
        service_type = st.selectbox("Service", ["AC Repair", "TV Repair", "Fridge Repair", "Washing Machine Repair", "Microwave Repair"])
        booking_date = st.date_input("Preferred Date", min_value=date.today())
        slot = st.selectbox("Time Slot", SLOT_OPTIONS)
        vendor = st.selectbox("Vendor", ["Vendor A", "Vendor B", "Vendor C"])
        amount_map = {"Vendor A": 500, "Vendor B": 700, "Vendor C": 1000}
        submitted = st.form_submit_button("Book Service")

        if submitted:
            date_text = booking_date.strftime("%d-%m-%Y")
            if slot_is_free(service_type, date_text, slot):
                book_service(customer["user_id"], service_type, date_text, slot, vendor, amount_map[vendor])
                st.success("Booking placed successfully")
                st.rerun()
            else:
                st.warning("This service is already booked for the selected date and time slot")

    st.divider()
    st.subheader("Booking History")
    history = get_booking_history(customer["user_id"])

    if history:
        st.dataframe(history, use_container_width=True, hide_index=True)

        st.subheader("Manage Bookings")
        booking_names = []
        booking_map = {}

        for row in history:
            name = f"{row['booking_id']} - {row['service_type']} ({row['booking_date']})"
            booking_names.append(name)
            booking_map[name] = row

        selected_name = st.selectbox("Select a booking to edit", booking_names)
        selected_booking = booking_map[selected_name]

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
            edit_slot = st.selectbox(
                "Time Slot",
                SLOT_OPTIONS,
                index=SLOT_OPTIONS.index(selected_booking["slot"]) if selected_booking["slot"] in SLOT_OPTIONS else 0,
            )
            edit_vendor = st.selectbox(
                "Vendor",
                ["Vendor A", "Vendor B", "Vendor C"],
                index=["Vendor A", "Vendor B", "Vendor C"].index(selected_booking["vendor"]),
            )
            amount_map = {"Vendor A": 500, "Vendor B": 700, "Vendor C": 1000}
            col1, col2 = st.columns(2)
            update_clicked = col1.form_submit_button("Update")
            delete_clicked = col2.form_submit_button("Delete")

            if update_clicked:
                date_text = edit_date.strftime("%d-%m-%Y")
                if slot_is_free(edit_service_type, date_text, edit_slot, selected_booking["booking_id"]):
                    update_booking(selected_booking["booking_id"], edit_service_type, date_text, edit_slot, edit_vendor, amount_map[edit_vendor])
                    st.success("Booking updated")
                    st.rerun()
                else:
                    st.warning("This service is already booked for the selected date and time slot")

            if delete_clicked:
                delete_booking(selected_booking["booking_id"])
                st.success("Booking deleted")
                st.rerun()
    else:
        st.info("No bookings yet")