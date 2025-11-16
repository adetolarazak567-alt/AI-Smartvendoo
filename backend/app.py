from flask import Flask, request, jsonify, session
from flask_cors import CORS
from dotenv import load_dotenv
import os
import datetime

# ----------------------
# Load Environment Variables
# ----------------------
load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
BNB_ADDRESS = os.getenv("BNB_ADDRESS")
NOWPAYMENTS_KEY = os.getenv("NOWPAYMENTS_KEY")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY")  # fallback key
CORS(app)

# ------------------------
# Simple in-memory user/sub tracking
# ------------------------
user_trials = {}  # {email: {"copywriting": 3, "freelance": 3, "business": 3, "paid_until": datetime}}

FREE_TRIAL_COUNT = 1  # 1 free trial per service
SUB_DURATION_DAYS = 30  # paid subscription lasts 30 days

# ------------------------
# Admin Login
# ------------------------
@app.route("/admin-login", methods=["POST"])
def admin_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "error": "Invalid email or password"}), 401

@app.route("/admin-dashboard", methods=["GET"])
def admin_dashboard():
    if session.get("admin_logged_in"):
        return jsonify({"status": "success", "users": user_trials})
    return "Unauthorized", 401

# ------------------------
# User Trials Check
# ------------------------
@app.route("/user-trials", methods=["GET"])
def user_trials_endpoint():
    email = request.args.get("email", "guest@example.com")
    now = datetime.datetime.now()
    user = user_trials.get(email, {})
    paid_until = user.get("paid_until")
    paid = paid_until and now < paid_until
    trials = {
        "copywriting": user.get("copywriting", FREE_TRIAL_COUNT),
        "freelance": user.get("freelance", FREE_TRIAL_COUNT),
        "business": user.get("business", FREE_TRIAL_COUNT),
    }
    return jsonify({"trials": trials, "paid": paid})

# ------------------------
# Vending Machine Endpoints
# ------------------------
@app.route("/copywriting", methods=["POST"])
def copywriting():
    data = request.get_json()
    email = data.get("email", "guest@example.com")
    service = "copywriting"
    user = user_trials.setdefault(email, {})
    # Check free trial or paid
    now = datetime.datetime.now()
    paid_until = user.get("paid_until")
    paid = paid_until and now < paid_until
    if not paid and user.get(service, FREE_TRIAL_COUNT) <= 0:
        return jsonify({"error": "Free trials finished. Subscribe to continue."}), 403
    # Deduct trial if not paid
    if not paid:
        user[service] = user.get(service, FREE_TRIAL_COUNT) - 1

    copy_type = data.get("copy_type")
    tone = data.get("tone")
    name = data.get("name")
    result_text = f"Elite copywriting for '{name}' in a {tone} tone. ({copy_type})"
    return jsonify({"result": result_text})

@app.route("/freelance", methods=["POST"])
def freelance():
    data = request.get_json()
    email = data.get("email", "guest@example.com")
    service = "freelance"
    user = user_trials.setdefault(email, {})
    now = datetime.datetime.now()
    paid_until = user.get("paid_until")
    paid = paid_until and now < paid_until
    if not paid and user.get(service, FREE_TRIAL_COUNT) <= 0:
        return jsonify({"error": "Free trials finished. Subscribe to continue."}), 403
    if not paid:
        user[service] = user.get(service, FREE_TRIAL_COUNT) - 1

    job_type = data.get("job_type")
    platform = data.get("platform")
    level = data.get("level")
    result_text = f"Elite freelance proposal for {job_type} ({level}) on {platform}."
    return jsonify({"result": result_text})

@app.route("/business-plan", methods=["POST"])
def business_plan():
    data = request.get_json()
    email = data.get("email", "guest@example.com")
    service = "business"
    user = user_trials.setdefault(email, {})
    now = datetime.datetime.now()
    paid_until = user.get("paid_until")
    paid = paid_until and now < paid_until
    if not paid and user.get(service, FREE_TRIAL_COUNT) <= 0:
        return jsonify({"error": "Free trials finished. Subscribe to continue."}), 403
    if not paid:
        user[service] = user.get(service, FREE_TRIAL_COUNT) - 1

    niche = data.get("niche")
    output = data.get("output")
    result_text = f"Elite {output} generated for {niche} niche."
    return jsonify({"result": result_text})

# ------------------------
# Dummy Payment Endpoints
# ------------------------
@app.route("/paypal-init", methods=["POST"])
def paypal_init():
    data = request.get_json()
    email = data.get("email", "guest@example.com")
    amount = data.get("amount")
    # Mark user as paid for 30 days
    user = user_trials.setdefault(email, {})
    user["paid_until"] = datetime.datetime.now() + datetime.timedelta(days=SUB_DURATION_DAYS)
    return jsonify({"status": "success", "redirect_url": "https://www.paypal.com/checkout"})

@app.route("/crypto-init", methods=["POST"])
def crypto_init():
    data = request.get_json()
    email = data.get("email", "guest@example.com")
    coin = data.get("coin")  # e.g., BNB
    amount = data.get("amount")
    # Mark user as paid for 30 days
    user = user_trials.setdefault(email, {})
    user["paid_until"] = datetime.datetime.now() + datetime.timedelta(days=SUB_DURATION_DAYS)
    return jsonify({"status": "success", "address": BNB_ADDRESS})

@app.route("/nowpayments-init", methods=["POST"])
def nowpayments_init():
    data = request.get_json()
    email = data.get("email", "guest@example.com")
    amount = data.get("amount")
    # Mark user as paid for 30 days
    user = user_trials.setdefault(email, {})
    user["paid_until"] = datetime.datetime.now() + datetime.timedelta(days=SUB_DURATION_DAYS)
    return jsonify({"status": "success", "checkout_url": "https://nowpayments.io/checkout"})

# ------------------------
# Run Server
# ------------------------
if __name__ == "__main__":
    app.run(debug=True)
