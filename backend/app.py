from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
import os

app = Flask(__name__, static_folder='static')
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "razzysecretkey123")

# -----------------------------
# In-Memory Data
# -----------------------------
users = {}  # email -> {password, country, currency, trials, paid, banned}
admin_password = os.getenv("ADMIN_PASSWORD", "@razzyadmin567")
admin_email = os.getenv("ADMIN_EMAIL", "adetolarazak567@gmail.com")
vending_machines = ["copywriting","freelance","resume","business","social","ebook","branding","dropshipping"]
usage_tracker = {vm: 0 for vm in vending_machines}
user_usage = {}  # email -> {vm_name -> count}

# -----------------------------
# Utils
# -----------------------------
def can_use_vm(email, vm):
    if users[email].get("banned"): 
        return False, "Your account is banned."
    trials_left = 3 - user_usage.get(email, {}).get(vm, 0)
    if trials_left > 0:
        return True, f"Free trial remaining: {trials_left}"
    if users[email].get("paid", False):
        return True, "Paid access"
    return False, "Please subscribe to use this vending machine"

def increment_usage(email, vm):
    usage_tracker[vm] += 1
    user_usage.setdefault(email, {})
    user_usage[email][vm] = user_usage[email].get(vm, 0) + 1

# -----------------------------
# Serve static HTML
# -----------------------------
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/login.html')
def login_html():
    return send_from_directory(app.static_folder, 'login.html')

@app.route('/signup.html')
def signup_html():
    return send_from_directory(app.static_folder, 'signup.html')

@app.route('/admin.html')
def admin_html():
    return send_from_directory(app.static_folder, 'admin.html')

# -----------------------------
# Signup/Login
# -----------------------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    country = data.get("country", "Nigeria")
    if email in users:
        return jsonify({"status":"error","message":"Email exists"})
    users[email] = {"password": password, "country": country, "currency":"$", "paid":False, "banned":False}
    return jsonify({"status":"success","message":"Account created"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    
    # Admin login
    if email == admin_email and password == admin_password:
        token = "admin_token_123"  # Simple token for frontend
        session["admin"] = True
        return jsonify({"status":"success","token": token, "message":"Admin logged in"})
    
    if email not in users or users[email]["password"] != password:
        return jsonify({"status":"error","message":"Invalid credentials"})
    
    session["user"] = email
    return jsonify({"status":"success","message":"Logged in"})

# -----------------------------
# Admin endpoints
# -----------------------------
@app.route("/admin_data", methods=["GET"])
def admin_data():
    token = request.headers.get('Authorization', '').replace('Bearer ','')
    if not session.get("admin") or token != "admin_token_123":
        return jsonify({"error":"Unauthorized"}), 401
    return jsonify({
        "total_users": len(users),
        "active_users_last_24h": len(users),  # simplified
        "banned_users": sum(u.get("banned", False) for u in users.values()),
        "earnings": sum(u.get("paid", False) for u in users.values()),
        "recent_users": [
            {"email": email, "country": u.get("country"), "trial_uses_left": 3 - sum(user_usage.get(email, {}).values()),
             "usage_count": sum(user_usage.get(email, {}).values()), "created_at": 0} 
            for email, u in users.items()
        ],
        "recent_logs": ["User log placeholder"]
    })

@app.route("/ban_user", methods=["POST"])
def ban_user():
    token = request.headers.get('Authorization', '').replace('Bearer ','')
    if not session.get("admin") or token != "admin_token_123":
        return jsonify({"error":"Unauthorized"}), 401
    email = request.json.get("email")
    if email in users:
        users[email]["banned"] = True
    return jsonify({"status":"ok"})

@app.route("/unban_user", methods=["POST"])
def unban_user():
    token = request.headers.get('Authorization', '').replace('Bearer ','')
    if not session.get("admin") or token != "admin_token_123":
        return jsonify({"error":"Unauthorized"}), 401
    email = request.json.get("email")
    if email in users:
        users[email]["banned"] = False
    return jsonify({"status":"ok"})

@app.route("/delete_user", methods=["POST"])
def delete_user():
    token = request.headers.get('Authorization', '').replace('Bearer ','')
    if not session.get("admin") or token != "admin_token_123":
        return jsonify({"error":"Unauthorized"}), 401
    email = request.json.get("email")
    if email in users:
        users.pop(email)
        user_usage.pop(email, None)
    return jsonify({"status":"ok"})

# -----------------------------
# Vending machine endpoints
# -----------------------------
def vending_response(email, vm, message):
    allowed, msg = can_use_vm(email, vm)
    if not allowed: return {"result": msg}
    increment_usage(email, vm)
    return {"result": message}

@app.route("/<vm>", methods=["POST"])
def vending(vm):
    email = session.get("user")
    if not email: 
        return jsonify({"result":"Login required"}), 401
    if vm not in vending_machines:
        return jsonify({"result":"Invalid vending machine"}), 404
    data = request.json
    message = f"Generated {vm} output with data {data}"
    return jsonify(vending_response(email, vm, message))

# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
