from flask import Flask, request, jsonify
import sqlite3
import hashlib
import secrets
from flask_socketio import SocketIO, join_room, leave_room, emit


DATABASE = "server.db"


# server_assistant.py


def init_db():
    create_users_table()
    create_groups_table()
    create_group_members_table()
    create_faults_table()
    create_missions_table()
    create_bills_table()
    create_outcomes_table()
    create_notifications_table()
    create_events_table()
    create_files_table() 
    create_chat_rooms_table()
    create_chat_messages_table()
    create_invitations_table()
# ... Other functions ...

def invite_user_to_group(email, group_id):
    """
    Stores an invitation for a user to join a group.
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO invitations (email, group_id) VALUES (?, ?)", 
            (email, group_id)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def check_user_invitation(email):
    """
    Checks if there are any invitations for a user.
    """
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT group_id FROM invitations WHERE email=?", (email,))
    group_ids = cur.fetchall()
    conn.close()
    return group_ids





# server_assistant.py
def create_invitations_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invitations (
            id INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            group_id TEXT NOT NULL,
            date_invited TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def create_files_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            group_id TEXT NOT NULL,
            user_id TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_file_metadata(filename, filepath, groupID, userID):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("INSERT INTO files (filename, filepath, group_id, user_id) VALUES (?, ?, ?, ?)",
                (filename, filepath, groupID, userID))
    conn.commit()
    conn.close()
    



def fetch_photos_by_group(group_id):
    with sqlite3.connect(DATABASE) as con:
        con.row_factory = sqlite3.Row  # This allows you to access row data by column name
        cur = con.cursor()
        cur.execute('SELECT * FROM files WHERE group_id = ?', (group_id,))
        
        rows = cur.fetchall()
        photos = [dict(row) for row in rows]  # Convert rows to dictionaries for easy JSON conversion
        
        return photos






def add_room(room_name, group_id, user1, user2):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    try:
        print("Asssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss", room_name, group_id, user1, user2)
        cur.execute(
            "INSERT INTO chat_rooms (room_name, group_id, user1, user2) VALUES (?, ?, ?, ?)", 
            (room_name, group_id, user1, user2)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_room(room_name):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("DELETE FROM chat_rooms WHERE room_name=?", (room_name,))
    conn.commit()
    conn.close()

def get_all_rooms():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT room_name, group_id, user1, user2 FROM chat_rooms")
    rooms = cur.fetchall()
    conn.close()
    return rooms


# You already have a way to insert a message, but just to make it more modular
def insert_message(room_id, user_id, message_text, timestamp):
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chat_messages (room_id, user_id, message_text, timestamp) VALUES (?, ?, ?, ?)",
        (room_id, user_id, message_text, timestamp)
    )
    conn.commit()
    conn.close()




def create_chat_rooms_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
    """
    CREATE TABLE IF NOT EXISTS chat_rooms (
        room_id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_name TEXT NOT NULL UNIQUE,
        group_id TEXT,
        user1 TEXT,
        user2 TEXT
    )
    """
)


    conn.commit()
    conn.close()

def create_chat_messages_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (room_id) REFERENCES chat_rooms (room_id),
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )"""
    )

    conn.commit()
    conn.close()







def create_users_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL,
                            hashedPassword TEXT NOT NULL,
                            email TEXT NOT NULL,
                            fullName TEXT NOT NULL,
                            profilePicture TEXT,
                            dateOfBirth TEXT,
                            createdAt TIMESTAMP NOT NULL,
                            updatedAt TIMESTAMP NOT NULL,
                            lastLogin TIMESTAMP NOT NULL,
                            role TEXT NOT NULL
                        )"""
    )

    conn.commit()
    conn.close()


def create_groups_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS `groups` (
                        group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        group_name TEXT NOT NULL,
                        group_max_members INTEGER NOT NULL,
                        group_details TEXT,
                        end_of_contract TEXT
                    )"""
    )

    conn.commit()
    conn.close()


def create_group_members_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS group_members (
                    group_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    is_landlord INTEGER NOT NULL,
                    user_join_to_group INTEGER NOT NULL,
                    date_intended_contract_termination INTEGER,
                    is_finish INTEGER NOT NULL,
                    FOREIGN KEY (group_id) REFERENCES groups (group_id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(group_id, user_id)
                )"""
    )

    conn.commit()
    conn.close()


def create_faults_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS faults (
                    fault_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    fault_name TEXT NOT NULL,
                    fault_description TEXT,
                    created_date TIMESTAMP NOT NULL,
                    fixed BOOLEAN NOT NULL,

                    FOREIGN KEY (group_id) REFERENCES groups (group_id)
                )"""
    )

    conn.commit()
    conn.close()


def create_missions_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS missions (
                    mission_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    mission_name TEXT NOT NULL,
                    mission_description TEXT,
                    created_date TIMESTAMP NOT NULL,
                    completed BOOLEAN NOT NULL,

                    FOREIGN KEY (group_id) REFERENCES groups (group_id)
                )"""
    )

    conn.commit()
    conn.close()


def create_bills_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS bills (
                    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    user_id INTEGER,
                    bill_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    bill_date TIMESTAMP,
                    created_date TIMESTAMP NOT NULL,

                    FOREIGN KEY (group_id) REFERENCES group_members (group_id),
                    FOREIGN KEY (user_id) REFERENCES group_members (user_id)
                )"""
    )

    conn.commit()
    conn.close()


def create_outcomes_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS outcomes (
                    outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    outcome_name TEXT NOT NULL,
                    outcome_description TEXT,
                    amount REAL NOT NULL,
                    outcome_date TIMESTAMP,
                    created_date TIMESTAMP NOT NULL,

                    FOREIGN KEY (group_id) REFERENCES group_members (group_id),
                    FOREIGN KEY (user_id) REFERENCES group_members (user_id)
                )"""
    )

    conn.commit()
    conn.close()


def create_events_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_creator_id INTEGER NOT NULL,
                        event_name TEXT NOT NULL,
                        event_description TEXT NOT NULL,
                        event_date TIMESTAMP NOT NULL,                        
                        created_date TIMESTAMP NOT NULL,
                        
                        FOREIGN KEY (user_creator_id) REFERENCES users (user_creator_id)
                    )"""
    )

    conn.commit()
    conn.close()


def create_notifications_table():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS notifications (
                    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    notification_name TEXT NOT NULL,
                    created_date TIMESTAMP NOT NULL,

                    FOREIGN KEY (group_id) REFERENCES group_members (group_id),
                    FOREIGN KEY (user_id) REFERENCES group_members (user_id)
                )"""
    )

    conn.commit()
    conn.close()




def query_db(query, args=(), one=False):
    try:
        conn = sqlite3.connect(DATABASE)
        cur = conn.cursor()
        cur.execute(query, args)
        if query.strip().upper().startswith("INSERT"):
            last_row_id = cur.lastrowid
            conn.commit()
            conn.close()
            return last_row_id, True
        conn.commit()  # Add this line if your query modifies the database (INSERT, UPDATE, DELETE)

        result = cur.fetchall()
        if query.strip().upper().startswith("DELETE"):
            result = cur.rowcount
            return result, True
        conn.close()

        # Return a tuple containing the result and a boolean indicating success
        return result if not one else (result[0] if result else None), True

    except sqlite3.Error as error:
        print("An error occurred:", error)
        if conn:
            conn.close()

        # Return None and a boolean indicating failure
        return None, False


def generate_token():
    return secrets.token_hex(16)

