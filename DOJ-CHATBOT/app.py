import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import google.generativeai as genai
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import logging
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_socketio import SocketIO

app = Flask(__name__)
CORS(app)  # Allow all origins by default
socketio = SocketIO(app, cors_allowed_origins="http://127.0.0.1:5500")

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure Google Generative AI with the API key
api_key = "AIzaSyCEiK50hKfN6YI6LROVi2-yzxEC9A4gJ9c"  # Use environment variable for security
if not api_key:
    logging.error("GOOGLE_API_KEY is not set. Exiting.")
    exit(1)

try:
    genai.configure(api_key=api_key)
except Exception as e:
    logging.error(f"Error configuring Generative AI: {e}")
    exit(1)

# Load the Gemini Pro model
try:
    model = genai.GenerativeModel("gemini-pro")
    chat = model.start_chat(history=[])
except Exception as e:
    logging.error(f"Error loading Gemini Pro model: {e}")
    exit(1)

bcrypt = Bcrypt(app)

# In-memory user storage with predefined users and admin credentials
users = {
    "admin": {
        "email": "admin@example.com",
        "password": bcrypt.generate_password_hash("admin123").decode('utf-8'),
        "role": "admin"
    },
    "user1": {
        "email": "user1@example.com",
        "password": bcrypt.generate_password_hash("user123").decode('utf-8'),
        "role": "user"
    },
    "user2": {
        "email": "user2@example.com",
        "password": bcrypt.generate_password_hash("user456").decode('utf-8'),
        "role": "user"
    }
}

@app.route('/')
def index():
    """Render the login page."""
    if 'username' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('user_home'))
    return render_template('login.html')

@app.route('/admin')
def admin():
    """Render the admin dashboard if the user is an admin."""
    if 'username' in session and session['role'] == 'admin':
        return render_template('admin.html')
    return redirect(url_for('index'))

@app.route('/admin/<section>')
def admin_section(section):
    """Render dynamic sections of the admin page."""
    valid_sections = ['dashboard', 'live-consultancy', 'chat-room', 'user-management', 'settings', 'reports']
    
    if 'username' in session and session['role'] == 'admin':
        if section in valid_sections:
            return render_template(f'admin_{section}.html')
        else:
            return "Section not found", 404
    
    return redirect(url_for('index'))

@app.route('/user_home')
def user_home():
    """Render the user dashboard if the user is authenticated."""
    if 'username' in session and session['role'] == 'user':
        return render_template('index.html')
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    """Handle user login."""
    data = request.get_json()  # Get JSON data
    username = data.get('username')
    password = data.get('password')

    if username in users and bcrypt.check_password_hash(users[username]['password'], password):
        session['username'] = username
        session['role'] = users[username]['role']
        if users[username]['role'] == 'admin':
            return jsonify({'success': True, 'redirect': url_for('admin')})
        else:
            return jsonify({'success': True, 'redirect': url_for('user_home')})
    else:
        return jsonify({'success': False, 'message': "Invalid username or password"})

@app.route('/logout')
def logout():
    """Log the user out and redirect to the login page."""
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    """Handle user registration."""
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if username in users:
        return jsonify({'success': False, 'message': 'Username already exists'}), 400

    if any(user['email'] == email for user in users.values()):
        return jsonify({'success': False, 'message': 'Email already exists'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    users[username] = {'email': email, 'password': hashed_password, 'role': 'user'}

    return jsonify({'success': True}), 200

@app.route('/chat', methods=['POST'])
def chat_response():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"response": "Please provide a message to get a response."})

    try:
        response = chat.send_message(user_message, stream=False)
        bot_message = " ".join([chunk.text for chunk in response])
        return jsonify({"response": bot_message})
    except Exception as e:
        logging.error(f"Error getting response from Gemini Pro: {e}")
        return jsonify({"response": "Sorry, there was an error processing your request."})

@app.route('/live_stream')
def live_stream():
    """Render the live court streaming page."""
    return render_template('live_stream.html')

@socketio.on('create')
def on_create(data):
    room = data['room']
    join_room(room)  # Join the room
    emit('status', {'msg': f"{data['username']} created and joined the room."}, room=room)
    emit('status', {'msg': f"Room {room} has been created."}, room=room)

@socketio.on('join')
def on_join(data):
    room = data['room']
    join_room(room)  # Join the room
    emit('status', {'msg': f"{data['username']} has entered the room."}, room=room)

@socketio.on('leave')
def on_leave(data):
    room = data['room']
    leave_room(room)  # Leave the room
    emit('status', {'msg': f"{data['username']} has left the room."}, room=room)

@socketio.on('offer')
def handle_offer(data):
    emit('offer', data, room=data['to'])

@socketio.on('answer')
def handle_answer(data):
    emit('answer', data, room=data['to'])

@socketio.on('ice-candidate')
def handle_ice_candidate(data):
    emit('ice-candidate', data, room=data['to'])

if __name__ == "__main__":
    logger.debug("Starting application...")
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_secret_key')
    logger.debug("Running socketio server...")
    socketio.run(app, host='127.0.0.1', port=5002, debug=True, use_reloader=False)
