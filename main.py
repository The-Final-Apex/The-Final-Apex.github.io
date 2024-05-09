from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
import secrets
import sqlite3

# Create the SQLite database and the chat_rooms table if it doesn't exist
conn = sqlite3.connect('chatroometh.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS chat_rooms
             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, password TEXT, code TEXT)''')
conn.commit()
conn.close()


app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdafhhhds"
socketio = SocketIO(app)

rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)
        
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)
        
        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")

def check_user_data(name, password):
    conn = sqlite3.connect('chatroometh.db')
    cursor = conn.cursor()

    # Check if the user with the provided name and password exists in the database
    cursor.execute('''
        SELECT * FROM chat_rooms WHERE name = ? AND password = ?
    ''', (name, password))

    user_data = cursor.fetchone()

    conn.close()

    return user_data


@app.route('/login', methods=['POST'])
def login():
    name = request.form.get('name')
    password = request.form.get('password')

    # Check the database for the user's information
    user_data = check_user_data(name, password)

    if user_data:
        # User exists in the database, retrieve the chat room information
        chat_room_name = user_data[1]
        chat_room_code = user_data[3]
        session['room'] = chat_room_code
        session['name'] = name
        return redirect(url_for('room'))
    else:
        # User does not exist in the database, create a new user
        room_code = insert_user_data(name, password)
        session['room'] = room_code
        session['name'] = name
        return redirect(url_for('room'))


        
        # User does not exist in
def insert_user_data(name, password):
    conn = sqlite3.connect('chatroometh.db')
    cursor = conn.cursor()

    # Generate a unique room code
    room_code = generate_unique_code(5)

    # Insert user data into the database
    cursor.execute('''
        INSERT INTO chat_rooms (name, password, code) VALUES (?, ?, ?)
    ''', (name, password, room_code))

    conn.commit()
    conn.close()

    return room_code


@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
