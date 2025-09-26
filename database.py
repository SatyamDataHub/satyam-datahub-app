# -*- coding: utf-8 -*-
import sqlite3
import os

# --- CONFIGURATION ---
DATABASE_FILE = 'dems.db'

# --- DATABASE FUNCTIONS ---

def create_connection():
    """Create a database connection to the SQLite database."""
    conn = None
    try:
        # Connect to the database file. It will be created if it doesn't exist.
        conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def create_tables(conn):
    """
    Create all necessary tables for the application.
    Uses 'IF NOT EXISTS' to prevent errors if the script is run multiple times,
    but it will NOT update existing tables.
    """
    try:
        cursor = conn.cursor()
        
        # Table to store user accounts (admins and employees)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL, -- 'admin' or 'employee'
            joining_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL DEFAULT 'active', -- 'active' or 'inactive'
            wallet_balance REAL NOT NULL DEFAULT 0.0,
            profile_picture TEXT, -- Filename of the uploaded avatar
            bank_details TEXT, -- Stored as a JSON string
            
            -- Enhanced profile fields
            phone_number TEXT,
            gender TEXT,
            date_of_birth DATE,
            designation TEXT,
            last_login TIMESTAMP
        );
        """)

        # Table to track every image file in the uploads folder
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'unassigned' -- 'unassigned' or 'assigned'
        );
        """)
        
        # Table to group tasks into projects assigned to an employee
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL UNIQUE,
            employee_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'In Progress', -- 'In Progress', 'In Review', 'Approved', 'Rejected'
            assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cost REAL NOT NULL DEFAULT 0.0,
            security_deposit REAL NOT NULL DEFAULT 0.0,
            expiry_date TIMESTAMP,
            
            -- Future-proof field
            notes TEXT, -- For admin comments on a project
            
            FOREIGN KEY (employee_id) REFERENCES users (id)
        );
        """)

        # Table for individual data entry tasks, linked to a project and an image
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL, -- This links the task to a project
            image_id INTEGER NOT NULL,  -- This links the task to an image
            status TEXT NOT NULL DEFAULT 'Pending', -- 'Pending', 'Saved', 'Submitted'
            data_json TEXT, -- Stores the entered data as a JSON string
            
            -- Future-proof field
            last_updated TIMESTAMP,
            
            FOREIGN KEY (project_id) REFERENCES projects (id),
            FOREIGN KEY (image_id) REFERENCES images (id)
        );
        """)

        # Table for storing contact form inquiries
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            mobile_number TEXT,
            message TEXT NOT NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        conn.commit()
        print("✅ Tables created or verified successfully.")

    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")

def init_db():
    """
    Main function to initialize the database.
    It connects and calls the table creation function.
    """
    print("--- Initializing Database ---")
    if not os.path.exists(DATABASE_FILE):
        print(f"Creating new database file: {DATABASE_FILE}")
    else:
        print(f"Database file '{DATABASE_FILE}' already exists. Verifying tables...")

    conn = create_connection()
    if conn is not None:
        create_tables(conn)
        conn.close()
        print("--- Database setup complete. ---")
    else:
        print("🔴 CRITICAL: Could not create the database connection.")


# This part allows you to run 'python database.py' directly from the terminal
if __name__ == '__main__':
    # **IMPORTANT REMINDER**
    # If you are running this script to fix an error, you must
    # DELETE your old 'dems.db' file first for the changes to apply.
    init_db()