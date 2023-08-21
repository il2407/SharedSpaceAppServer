import eventlet
eventlet.monkey_patch()


import datetime
import hashlib
import json
import sqlite3
import bcrypt
from flask import Flask, request, jsonify, g
import server_assistent
from flask_cors import CORS
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from flask import send_from_directory


from werkzeug.utils import secure_filename
import os



app = Flask(__name__)
cors = CORS(app)
server_assistent.init_db()







socketio = SocketIO(app, cors_allowed_origins="*")



UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER




# ... Other imports ...

@app.route('/invite_user', methods=['POST'])
def invite_user():
    data = request.json
    email = data['email']
    group_id = data['group_id']
    result = server_assistent.invite_user_to_group(email, group_id)
    if result:
        return jsonify({"status": "success", "message": "User invited successfully."}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to invite user."}), 400

@app.route('/check_invitations/<email>', methods=['GET'])
def check_invitations(email):
    group_ids = server_assistent.check_user_invitation(email)
    return jsonify(group_ids)

# ... Rest of app.py ...




def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
           
           
@app.route('/uploads/<filename>', methods=['GET'])
def uploaded_file(filename):
    return send_from_directory('uploads', filename)



@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    print("Inside upload_photo function.")
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        groupID = request.form.get('groupID')
        userID = request.form.get('userID')
        # You should validate these values here (not implemented for simplicity)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print ("groupID", groupID , "userID" , userID)

        
        # Save file metadata to SQLite database
        server_assistent.save_file_metadata(filename, filepath, groupID, userID)
        
        return jsonify({'success': True, 'filepath': filepath}), 201
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/get_photos/<group_id>', methods=['GET'])
def get_photos(group_id):
    photos = server_assistent.fetch_photos_by_group(group_id)
    if not photos:
        return jsonify({'error': 'No photos found for this group'}), 404
    
    return jsonify({'photos': photos}), 200



@socketio.on("join")
def on_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    send(username + ' has entered the room.', room=room)

@socketio.on("leave")
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    send(username + ' has left the room.', room=room)

@socketio.on("message")
def handle_message(data):
    room = data['room']
    user_id = data['user_id']
    message_text = data['message']
    timestamp = datetime.datetime.now()
    # Save message to database
    server_assistent.query_db(
        "INSERT INTO chat_messages (room_id, user_id, message_text, timestamp) VALUES (?, ?, ?, ?)",
        (room, user_id, message_text, timestamp)
    )
    # Emit the message to the room
    emit("new_message", {
        "user_id": user_id,
        "message": message_text,
        "timestamp": str(timestamp)
    }, room=room)


@socketio.on("get_chat_history")
def handle_chat_history(data):
    try:
        room = data['room']
        print("asdassssssssssssssssssssssssss")

        # Fetch messages for the room from the database
        messages = server_assistent.query_db(
            "SELECT user_id, message_text FROM chat_messages WHERE room_id = ?", 
            (room)
        )

        # Check if messages were fetched
        if not messages:
            print(f"No messages found for room: {room}")
            emit("error", {"message": f"No messages found for room: {room}"}, room=room)
            return

        stringified_messages = [{"username": (msg[0]), "message": (msg[1])} for msg in messages]
        print(f"Messages for room {room}: {stringified_messages}")

        # Send the messages to the requesting client
        emit("chat_history", stringified_messages, room=room)

    except KeyError:
        print("Error: 'room' key not found in data.")
        emit("error", {"message": "Data format error."})
    except Exception as e:
        print(f"Error fetching chat history: {e}")
        emit("error", {"message": "Failed to fetch chat history."})






# ... existing imports and setup ...

@socketio.on("get_rooms")
def handle_get_rooms():
    rooms = server_assistent.get_all_rooms()
    emit("room_list", rooms)


@socketio.on("add_room")
def handle_add_room(data):
    room_name = data["room_name"]
    group_id = data["group_id"]   # Use .get() to ensure the code doesn't break if the field isn't provided
    user1 = data["user1"]
    user2 = data["user2"]

    success = server_assistent.add_room(room_name, group_id, user1, user2)   # Assuming the function now accepts these args
    if success:
     emit("room_added", {"message": "Room added successfully!", "room_name": room_name})
    else:
     emit("error", {"error": "Room already exists!"})
     
        


@socketio.on("delete_room")
def handle_delete_room(data):
    room_name = data["room_name"]
    server_assistent.delete_room(room_name)
    emit("room_deleted", {"message": "Room deleted successfully!", "room_name": room_name})

@socketio.on("message")
def handle_message(data):
    room = data['room']
    user_id = data['user_id']
    message_text = data['message']
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    server_assistent.insert_message(room, user_id, message_text, timestamp)
    emit("new_message", {
        "user_id": user_id,
        "message": message_text,
        "timestamp": timestamp
    }, room=room)

# ... rest of your app.py ...





@app.route("/get_group_details_by_id", methods=["POST"])
def get_group_details_by_id():
    data = request.get_json()
    user_id = data["user_id"]

    # Fetching group_ids associated with the user
    rows, success = server_assistent.query_db(
        f"SELECT group_id FROM group_members WHERE user_id={user_id}"
    )

    if not success:
        return jsonify({"error": "Failed to fetch group_ids for the user."}), 500

    column_names = ["group_id"]
    rows_as_dicts = [dict(zip(column_names, row)) for row in rows]

    group_details = []
    for row in rows_as_dicts:
        group_id = row["group_id"]

        # Fetching details of the group based on group_id
        group_row, group_success = server_assistent.query_db(
            f"SELECT * FROM groups WHERE group_id='{group_id}'"
        )

        if group_success and group_row:
            group_column_names = [
                "group_id",
                "group_name",
                "group_max_members",
                "group_details",
                "end_of_contract",  # Add other columns as needed
            ]
            group_details.append(dict(zip(group_column_names, group_row[0])))
        else:
            # Handle the case when the group_id is not found in the groups table
            group_details.append({"group_id": group_id, "error": "Group not found."})

    return jsonify(group_details)


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data or "email" not in data or "password" not in data:
        return jsonify({"message": "Invalid input"}), 400

    email = data["email"]
    password = data["password"]

    # Check if the user exists in the database by username
    user, success = server_assistent.query_db(
        "SELECT * FROM users WHERE email=?", (email,), one=True
    )

    if success and user:
        # User found, compare the stored password hash with the provided password
        # Assuming the column name is 'hashedPassword'
        stored_hashed_password = user[2]
        if bcrypt.checkpw(password.encode("utf-8"), stored_hashed_password):
            # Passwords match, generate token and return it with status code 200
            token = server_assistent.generate_token()
            return jsonify({"token": token}), 200
        else:
            # Passwords don't match, return error message
            return jsonify({"message": "Invalid username or password"}), 401
    else:
        # User not found or query failed, return error message
        return jsonify({"message": "Invalid username or password"}), 401


@app.route("/adduser", methods=["POST"])
def add_user():
    data = request.get_json()
    username = data["username"]
    password = data["password"]
    email = data["email"]
    full_name = data["full_name"]
    role = data["role"]
    # profile_picture = data['profile_picture']
    date_of_birth = data["date_of_birth"]
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    created_at = datetime.datetime.now()
    updated_at = datetime.datetime.now()
    last_login = datetime.datetime.now()
    # profile_picture = 'C:\\Users\\lmaim\\Desktop\\bsc\\4th_year\\Final_progect\\alternative_final_project\\client\\assets\\profilePic.png'
    if (
        validate_new_user(username, password, email, full_name, date_of_birth)
        is not True
    ):
        return jsonify({"status": "fail"}), 400
    result, success = server_assistent.query_db(
        "INSERT INTO users (username, hashedPassword, email, fullName, dateOfBirth, createdAt, updatedAt, lastLogin, role) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            username,
            hashed_password,
            email,
            full_name,
            date_of_birth,
            created_at,
            updated_at,
            last_login,
            role,
        ),
    )

    if success:
        return jsonify({"status": "success"}), 200
    else:
        return jsonify({"status": "fail"}), 500


@app.route("/open_call", methods=["POST"])
def open_call():
    data = request.get_json()
    email = data["email"]
    fault_name = data["subject"]
    fault_description = data["summary"]

    user_id, success = server_assistent.query_db(
        "SELECT id FROM users WHERE email=?", (email,), True
    )
    user_id = user_id[0]
    if success and user_id:
        group_id, success = server_assistent.query_db(
            "SELECT group_id FROM group_members where user_id=?", (user_id,), True
        )
        group_id = group_id[0]
        created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result, success = server_assistent.query_db(
            "INSERT INTO faults (group_id, fault_name, fault_description,"
            " created_date, fixed) VALUES (?,?,?,?,?)",
            (group_id, fault_name, fault_description, created_date, False),
        )
        if success:
            return jsonify({"status": "success"}), 200
        else:
            return (
                jsonify({"status": "fail", "message": "Failed to add user to group"}),
                500,
            )


@app.route("/delete_call", methods=["POST"])
def delete_call():
    data = request.get_json()
    fault_id = data["fault_id"]

    deleted_row, success = server_assistent.query_db(
        "DELETE FROM faults WHERE fault_id = ?", (fault_id,), True
    )
    if success:
        if deleted_row:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "fail", "message": "no row deleted"}), 500
    else:
        return jsonify({"status": "fail", "message": "Failed to connect to DB"}), 500


@app.route("/add_group", methods=["POST"])
def add_group():
    data = request.get_json()

    user_id = data["userID"]
    is_landlord = data["is_landlord"]
    group_name = data["group_name"]
    group_max_members = data["group_max_members"]
    group_description = data["group_description"]
    end_of_contract = data["end_of_contract"]

    group_id, success = server_assistent.query_db(
        "INSERT INTO groups (group_name,group_max_members, group_details,end_of_contract) VALUES (?, ?, ? ,?)",
        (
            group_name,
            group_max_members,
            group_description,
            end_of_contract,
        ),
    )
    if not success:
        return jsonify({"status": "fail", "message": "Failed to create group"}), 500
    created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _, success = server_assistent.query_db(
        "INSERT INTO group_members (group_id, user_id, is_landlord, user_join_to_group,is_finish) "
        "VALUES (?,?,?,?,?)",
        (group_id, user_id, is_landlord, created_date, False),
    )
    if success:
        return jsonify({"status": "success", "group_id": group_id}), 200
    else:
        return jsonify({"status": "fail"}), 500


@app.route("/toggle_finish", methods=["POST"])
def toggle_finish():
    data = request.get_json()
    user_id = data["user_id"]

    # Check if the user exists in the group_members table
    user_in_group, success = server_assistent.query_db(
        "SELECT * FROM group_members WHERE user_id=?", (user_id,), one=True
    )
    print("user_in_group", user_in_group)
    if not success or not user_in_group:
        return (
            jsonify({"status": "fail", "message": "User not found in group_members"}),
            404,
        )

    # Get the current value of 'is_finish' (assume it's the fourth column)
    is_finish = not user_in_group[6]

    # Update the 'is_finish' field for the specific user_id
    result, success = server_assistent.query_db(
        "UPDATE group_members SET is_finish=? WHERE user_id=?",
        (is_finish, user_id),
    )

    if success:
        return jsonify({"status": "success", "is_finish": is_finish}), 200
    else:
        return jsonify({"status": "fail", "message": "Failed to update is_finish"}), 500


@app.route("/id_from_email", methods=["POST"])
def id_from_email():
    data = request.get_json()

    user_email = data["email"]
    user_id, success = server_assistent.query_db(
        "SELECT id FROM users WHERE email=?", (user_email,), True
    )
    if success:
        if user_id:
            user_id = user_id[0]
            return jsonify({"status": "success", "user": user_id}), 200
        else:
            return (
                jsonify(
                    {"status": "fail", "message": "Failed to find this user email"}
                ),
                500,
            )
    else:
        return (
            jsonify({"status": "fail", "message": "Failed to find this user email"}),
            500,
        )


@app.route("/group_id_from_user_id", methods=["POST"])
def group_id_from_user_id():
    data = request.get_json()

    user_id = data["user_id"]
    group_id, success = server_assistent.query_db(
        "SELECT group_id FROM group_members WHERE user_id=?", (user_id,), True
    )
    if success:
        if group_id:
            group_id = group_id[0]
            return jsonify({"status": "success", "group": group_id}), 200
        else:
            return (
                jsonify({"status": "fail", "message": "Failed to find this user id"}),
                200,
            )
    else:
        return (
            jsonify({"status": "fail", "message": "Failed to find this user id"}),
            200,
        )


@app.route("/add_mission", methods=["POST"])
def add_mission():
    data = request.get_json()

    group_id = data["group_id"]
    mission_name = data["mission_name"]
    mission_description = data["mission_description"]
    # Add mission to the missions
    created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mission_id, success = server_assistent.query_db(
        "INSERT INTO missions (group_id, mission_name, mission_description, created_date, completed) VALUES (?,?,?,?,?)",
        (group_id, mission_name, mission_description, created_date, False),
        True,
    )
    if success:
        if mission_id:
            return jsonify({"status": "success", "group": mission_id}), 200
        else:
            return (
                jsonify({"status": "fail", "message": "Failed to insert this mission"}),
                500,
            )
    else:
        return jsonify({"status": "fail", "message": "Failed to add to DB"}), 500


@app.route("/remove_mission", methods=["POST"])
def remove_mission():
    data = request.get_json()

    mission_id = data["mission_id"]

    deleted_row, success = server_assistent.query_db(
        "DELETE FROM missions WHERE mission_id = ?", (mission_id,), True
    )
    if success:
        if deleted_row:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "fail", "message": "no row deleted"}), 500
    else:
        return jsonify({"status": "fail", "message": "Failed to connect to DB"}), 500


@app.route("/add_outcome", methods=["POST"])
def add_outcome():
    data = request.get_json()
    group_id = data["group_id"]
    user_id = data["user_id"]
    outcome_name = data["outcome_name"]
    # outcome_description = data['outcome_description']
    amount = data["amount"]
    # outcome_date = data['outcome_date']
    created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    outcome_id, success = server_assistent.query_db(
        "INSERT INTO outcomes (group_id, user_id, outcome_name,  amount,  "
        "created_date) VALUES (?,?,?,?,?)",
        (group_id, user_id, outcome_name, amount, created_date),
        True,
    )
    if success:
        if outcome_id:
            return jsonify({"status": "success", "outcome_id": outcome_id}), 200
        else:
            return (
                jsonify({"status": "fail", "message": "Failed to insert this outcome"}),
                500,
            )
    else:
        return jsonify({"status": "fail", "message": "Failed to add to DB"}), 500


@app.route("/remove_outcome", methods=["POST"])
def remove_outcome():
    data = request.get_json()

    outcome_id = data["outcome_id"]

    deleted_row, success = server_assistent.query_db(
        "DELETE FROM outcomes WHERE outcome_id = ?", (outcome_id,), True
    )
    if success:
        if deleted_row:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "fail", "message": "no row deleted"}), 500
    else:
        return jsonify({"status": "fail", "message": "Failed to connect to DB"}), 500


@app.route("/add_bill", methods=["POST"])
def add_bill():
    data = request.get_json()
    group_id = data["group_id"]
    user_id = data["user_id"]
    bill_name = data["bill_name"]
    amount = data["amount"]
    bill_date = data["bill_date"]
    created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bill_id, success = server_assistent.query_db(
        "INSERT INTO bills (group_id, user_id, bill_name, amount, bill_date, "
        "created_date) VALUES (?,?,?,?,?,?)",
        (group_id, user_id, bill_name, amount, bill_date, created_date),
        True,
    )
    if success:
        if bill_id:
            return jsonify({"status": "success", "bill_id": bill_id}), 200
        else:
            return (
                jsonify({"status": "fail", "message": "Failed to insert this bills"}),
                500,
            )
    else:
        return jsonify({"status": "fail", "message": "Failed to add to DB"}), 500


@app.route("/add_notification", methods=["POST"])
def add_notification():
    data = request.get_json()
    group_id = data["group_id"]
    user_id = data["user_id"]
    notification_name = data["notification_name"]
    created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notification_id, success = server_assistent.query_db(
        "INSERT INTO notifications (group_id, user_id, notification_name, "
        "created_date) VALUES (?,?,?,?)",
        (group_id, user_id, notification_name, created_date),
        True,
    )
    if success:
        if notification_id:
            return (
                jsonify({"status": "success", "notification_id": notification_id}),
                200,
            )
        else:
            return (
                jsonify({"status": "fail", "message": "Failed to insert this bills"}),
                500,
            )
    else:
        return jsonify({"status": "fail", "message": "Failed to add to DB"}), 500


@app.route("/remove_bill", methods=["POST"])
def remove_bill():
    data = request.get_json()

    bill_id = data["bill_id"]

    deleted_row, success = server_assistent.query_db(
        "DELETE FROM bills WHERE bill_id = ?", (bill_id,), True
    )
    if success:
        if deleted_row:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "fail", "message": "no row deleted"}), 500
    else:
        return jsonify({"status": "fail", "message": "Failed to connect to DB"}), 500


@app.route("/remove_notification", methods=["POST"])
def remove_notification():
    data = request.get_json()

    notification_id = data["notification_id"]

    deleted_row, success = server_assistent.query_db(
        "DELETE FROM notifications WHERE notification_id = ?", (notification_id,), True
    )
    if success:
        if deleted_row:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "fail", "message": "no row deleted"}), 500
    else:
        return jsonify({"status": "fail", "message": "Failed to connect to DB"}), 500


@app.route("/missions_from_group_id", methods=["POST"])
def missions_from_group_id():
    data = request.get_json()
    group_id = data["group_id"]
    print("asdsad", group_id)
    table_data, success = server_assistent.query_db("PRAGMA table_info(missions)")
    column_names = [info[1] for info in table_data]
    rows, success = server_assistent.query_db(
        "SELECT * FROM missions WHERE group_id=?", (group_id,)
    )
    rows_as_dicts = [dict(zip(column_names, row)) for row in rows]

    json_data = json.dumps(rows_as_dicts)
    # return jsonify(json_data), 200
    return json_data, 200


@app.route("/outcomes_from_group_id", methods=["POST"])
def outcomes_from_group_id():
    data = request.get_json()
    group_id = data["group_id"]

    table_data, success = server_assistent.query_db("PRAGMA table_info(outcomes)")
    column_names = [info[1] for info in table_data]
    rows, success = server_assistent.query_db(
        "SELECT * FROM outcomes WHERE group_id=?", (group_id,)
    )
    rows_as_dicts = [dict(zip(column_names, row)) for row in rows]

    json_data = json.dumps(rows_as_dicts)
    return json_data, 200


@app.route("/notifications_from_group_id", methods=["POST"])
def notifications_from_group_id():
    data = request.get_json()
    group_id = data["group_id"]

    table_data, success = server_assistent.query_db("PRAGMA table_info(notifications)")
    column_names = [info[1] for info in table_data]
    rows, success = server_assistent.query_db(
        "SELECT * FROM notifications WHERE group_id=?", (group_id,)
    )
    rows_as_dicts = [dict(zip(column_names, row)) for row in rows]

    json_data = json.dumps(rows_as_dicts)
    return json_data, 200


@app.route("/faults_from_group_id", methods=["POST"])
def faults_from_group_id():
    data = request.get_json()
    group_id = data["group_id"]

    table_data, success = server_assistent.query_db("PRAGMA table_info(faults)")
    column_names = [info[1] for info in table_data]
    rows, success = server_assistent.query_db(
        "SELECT * FROM faults WHERE group_id=?", (group_id,)
    )
    rows_as_dicts = [dict(zip(column_names, row)) for row in rows]

    json_data = json.dumps(rows_as_dicts)
    return json_data, 200


@app.route("/user_name_from_id", methods=["POST"])
def user_name_from_id():
    data = request.get_json()
    user_id = data["user_id"]
    user_name, success = server_assistent.query_db(
        "SELECT fullName FROM users WHERE id=?", (user_id,), True
    )
    if success:
        if user_name:
            return jsonify({"status": "success", "user_name": user_name[0]}), 200
        else:
            return jsonify({"status": "fail"}), 400
    else:
        return jsonify({"status": "fail"}), 400


@app.route("/group_name_from_id", methods=["POST"])
def group_name_from_id():
    data = request.get_json()
    group_id = data["group_id"]
    group_name, success = server_assistent.query_db(
        "SELECT group_name FROM groups WHERE group_id=?", (group_id,), True
    )
    if success:
        if group_name:
            return jsonify({"status": "success", "group_name": group_name[0]}), 200
        else:
            return jsonify({"status": "fail"}), 400
    else:
        return jsonify({"status": "fail"}), 400


def validate_new_user(username, password, email, full_name, date_of_birth):
    if len(username) < 4:
        return jsonify({"status": "Username must be at least 4 characters"}), 400
    if len(password) < 8:
        return jsonify({"status": "Password must be at least 8 characters"}), 400
    if len(email) < 5:
        return jsonify({"status": "Email must be at least 5 characters"}), 400
    if "@" not in email:
        return jsonify({"status": "Email must contain @"}), 400
    if "." not in email:
        return jsonify({"status": "Email must contain ."}), 400
    if len(full_name) < 5:
        return jsonify({"status": "Full name must be at least 5 characters"}), 400
    if len(date_of_birth) < 5:
        return jsonify({"status": "Date of birth must be at least 5 characters"}), 400
    return True


@app.route("/members_from_group_id", methods=["POST"])
def members_from_group_id():
    data = request.get_json()
    group_id = data["group_id"]
    print("asdsad", group_id)
    table_data, success = server_assistent.query_db("PRAGMA table_info(users)")
    column_names = [info[1] for info in table_data]
    rows, success = server_assistent.query_db(
        "SELECT DISTINCT users.* FROM users JOIN group_members ON users.id = group_members.user_id AND group_members.group_id=?",
        (group_id,),
    )
    rows_as_dicts = [dict(zip(column_names, row)) for row in rows]
    rows_as_dicts = [
        {key: value.decode("utf-8") if isinstance(value, bytes) else value}
        for row in rows_as_dicts
        for key, value in row.items()
    ]

    json_data = json.dumps(rows_as_dicts)
    return json_data, 200


@app.route("/get_user_groups", methods=["POST"])
def get_user_groups():
    data = request.get_json()
    user_id = data["user_id"]
    print("asdsad", user_id)
    table_data, success = server_assistent.query_db("PRAGMA table_info(groups)")
    column_names = [info[1] for info in table_data]
    rows, success = server_assistent.query_db(
        "SELECT DISTINCT groups.* FROM groups JOIN group_members ON groups.group_id = group_members.group_id AND group_members.user_id=?",
        (user_id,),
    )
    rows_as_dicts = [dict(zip(column_names, row)) for row in rows]
    rows_as_dicts = [
        {key: value.decode("utf-8") if isinstance(value, bytes) else value}
        for row in rows_as_dicts
        for key, value in row.items()
    ]

    json_data = json.dumps(rows_as_dicts)
    return json_data, 200


@app.route("/remove_user_from_group_by_id", methods=["POST"])
def remove_user_from_group():
    data = request.get_json()

    id = data["id"]

    deleted_row, success = server_assistent.query_db(
        "DELETE FROM group_members WHERE user_id = ?", (id,), True
    )
    if success:
        if deleted_row:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "fail", "message": "no row deleted"}), 500
    else:
        return jsonify({"status": "fail", "message": "Failed to connect to DB"}), 500


@app.route("/get_user_details_by_id", methods=["POST"])
def get_user_details_by_id():
    data = request.get_json()
    user_id = data["user_id"]
    print("asdsad", user_id)
    table_data, success = server_assistent.query_db("PRAGMA table_info(users)")
    column_names = [info[1] for info in table_data]
    rows, success = server_assistent.query_db(
        "SELECT * FROM users WHERE id=?", (user_id,)
    )
    rows_as_dicts = [dict(zip(column_names, row)) for row in rows]
    rows_as_dicts = [
        {key: value.decode("utf-8") if isinstance(value, bytes) else value}
        for row in rows_as_dicts
        for key, value in row.items()
    ]

    json_data = json.dumps(rows_as_dicts)
    return json_data, 200


def is_available_group(group_id):
    delete_users_finished_contract()
    curr_members = get_curr_num_group_members(group_id)
    max_members = get_max_members(group_id)
    return (
        curr_members is not None
        and max_members is not None
        and curr_members < max_members
    )


# def delete_users_finished_contract():
#     curr_date = datetime.datetime.now()
#     rows, success = server_assistent.query_db(
#         "DELETE FROM group_members WHERE date_intended_contract_termination < ?", (curr_date,)
#     )

# def get_max_members(group_id):
#     group_id = group_id[0]
#     group_id = int(group_id)
#     res, success = server_assistent.query_db(
#         "SELECT group_max_members FROM groups WHERE group_id = ?", (group_id,))
#     return res[0][0] if res else None

# def get_curr_num_group_members(group_id):
#     group_id = group_id[0]
#     group_id = int(group_id)  # Convert group_id to an integer if needed
#     res, success = server_assistent.query_db(
#         "SELECT COUNT(DISTINCT user_id) FROM group_members WHERE group_id = ?", (group_id,))
#     return res[0][0] if res else None

# @app.route("/get_available_groups", methods=["POST"])
# def get_available_groups():
#     all_groups_id, success = server_assistent.query_db(
#         "SELECT group_id FROM groups")
#     rows = []  # Initialize rows as an empty list
#     for group in all_groups_id:
#         if is_available_group(group):
#             group_data = server_assistent.query_db(
#                 "SELECT * FROM groups WHERE group_id = ?", (group[0],))
#             rows += group_data[0]  # Append the fetched group data to rows

#     table_data, success = server_assistent.query_db("PRAGMA table_info(groups)")
#     column_names = [info[1] for info in table_data]
#     rows_as_dicts = [dict(zip(column_names, row)) for row in rows]
#     json_data = json.dumps(rows_as_dicts)
#     return json_data, 200


@app.route("/get_available_groups", methods=["POST"])
def get_finished_groups_details():
    # Find all the members whose 'is_finish' field value is 1
    finished_members, success = server_assistent.query_db(
        "SELECT group_id, user_id FROM group_members WHERE is_finish=1"
    )

    if not success or not finished_members:
        return jsonify({"status": "fail", "message": "No finished members found"}), 404

    group_details = []
    for member in finished_members:
        group_id, user_id = member

        # Fetch group details for each group_id from the 'groups' table
        group_detail, success = server_assistent.query_db(
            "SELECT * FROM groups WHERE group_id=?", (group_id,), one=True
        )

        if success and group_detail:
            # Fetch the username of the user_id from the 'users' table
            username, _ = server_assistent.query_db(
                "SELECT username FROM users WHERE id=?", (user_id,), one=True
            )

            # Append the relevant details to the list
            group_details.append(
                {
                    "group_id": group_id,
                    "group_name": group_detail[1],
                    "group_max_members": group_detail[2],
                    "group_description": group_detail[3],
                    "end_of_contract": group_detail[4],
                    "user_id": user_id,
                    "username": username,
                }
            )

    if group_details:
        return jsonify({"status": "success", "group_details": group_details}), 200
    else:
        return (
            jsonify(
                {
                    "status": "fail",
                    "message": "No group details found for finished members",
                }
            ),
            404,
        )


@app.route("/add_user_to_group", methods=["POST"])
def add_user_to_group():
    data = request.get_json()
    group_id = data["group_id"]
    user_id = data["user_id"]
    date_intended_contract_termination = data["date_intended_contract_termination"]
    is_landlord = "user"
    is_finish = False

    created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _, success = server_assistent.query_db(
        "INSERT INTO group_members (group_id, user_id, is_landlord, user_join_to_group, date_intended_contract_termination, is_finish) "
        "VALUES (?,?,?,?,?,?)",
        (
            group_id,
            user_id,
            is_landlord,
            created_date,
            date_intended_contract_termination,
            is_finish,
        ),
    )

    if success:
        return jsonify({"status": "success", "group_id": group_id}), 200
    else:
        return jsonify({"status": "fail"}), 500


@app.route("/add_event", methods=["POST"])
def add_event():
    data = request.get_json()
    user_creator_id = data["user_id"]
    event_name = data["event_name"]
    event_description = data["event_description"]
    event_date_string = data["event_date"]
    date_format = "%Y-%m-%d %H:%M:%S"
    event_date = datetime.datetime.strptime(event_date_string, date_format)
    created_date = datetime.datetime.now().strftime(date_format)
    event_id, success = server_assistent.query_db(
        "INSERT INTO events (user_creator_id, event_name, event_description, event_date, "
        "created_date) VALUES (?,?,?,?,?)",
        (user_creator_id, event_name, event_description, event_date, created_date),
        True,
    )
    if success:
        if event_id:
            return (
                jsonify({"status": "success", "event_id": event_id}),
                200,
            )
        else:
            return (
                jsonify({"status": "fail", "message": "Failed to insert this event"}),
                500,
            )
    else:
        return jsonify({"status": "fail", "message": "Failed to add to DB"}), 500


@app.route("/get_events", methods=["POST"])
def get_events():
    data = request.get_json()

    table_data, success = server_assistent.query_db("PRAGMA table_info(events)")
    column_names = [info[1] for info in table_data]
    curr_date = datetime.datetime.now()
    rows, success = server_assistent.query_db(
        "SELECT * FROM events WHERE event_date<=?", (curr_date,)
    )
    rows_as_dicts = [dict(zip(column_names, row)) for row in rows]

    json_data = json.dumps(rows_as_dicts)
    return json_data, 200


@app.route("/remove_event", methods=["POST"])
def remove_event():
    data = request.get_json()

    event_id = data["mission_id"]

    deleted_row, success = server_assistent.query_db(
        "DELETE FROM events WHERE event_id = ?", (event_id,), True
    )
    if success:
        if deleted_row:
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "fail", "message": "no row deleted"}), 500
    else:
        return jsonify({"status": "fail", "message": "Failed to connect to DB"}), 500


# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=5000, debug=True)
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, use_reloader=False)

