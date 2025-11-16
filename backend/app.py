from flask import Flask, request, jsonify, session
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import requests

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "SUPER_SECRET_KEY")

# ------------------------
# Admin Credentials
# ------------------------
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "youremail@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "YourSecurePassword123")

# ------------------------
# User Database (In-Memory Example)
# ------------------------
# In production, use a real database like Postgres, MongoDB, etc.
users = {}  # { email: {paid_until, trials: {service_name: count}} }

FREE_TRIALS = {
    "copywriting": 3,
    "freelance": 3,
    "business": 3,
    "resume": 3,
    "summary": 3,
    "title": 3
}

# ------------------------
# Utility Functions
# ------------------------
def get_user(email):
    if email not in users:
        users[email] = {
            "paid_until": None,
            "trials": FREE_TRIALS.copy()
        }
    return users[email]

def can_use_service(user, service):
    if user["paid_until"] and datetime.now() <= user["paid_until"]:
        return True
    return user["trials"].get(service, 0) > 0

def decrement_trial(user, service):
    if user["trials"].get(service, 0) > 0:
        user["trials"][service] -= 1

# ------------------------
# ADMIN ROUTES
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
        return jsonify({"users": users})
    return "Unauthorized", 401

# ------------------------
# USER TRIALS ROUTE
# ------------------------
@app.route("/user-trials", methods=["GET"])
def user_trials():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400
    user = get_user(email)
    paid = user["paid_until"] and datetime.now() <= user["paid_until"]
    return jsonify({
        "trials": user["trials"],
        "paid": bool(paid),
        "paid_until": user["paid_until"].isoformat() if user["paid_until"] else None
    })

# ------------------------
# PAYMENT ROUTE (PayPal)
# ------------------------
@app.route("/paypal-init", methods=["POST"])
def paypal_init():
    data = request.get_json()
    email = data.get("email")
    amount = data.get("amount")
    user = get_user(email)

    # Mark paid for 30 days
    user["paid_until"] = datetime.now() + timedelta(days=30)

    return jsonify({
        "status": "success",
        "message": f"{email} has access for 30 days",
        "paid_until": user["paid_until"].isoformat(),
        "redirect_url": "https://www.paypal.com/checkout"
    })

# ------------------------
# PAYMENT ROUTE (NowPayments - Crypto)
# ------------------------
@app.route("/crypto-init", methods=["POST"])
def crypto_init():
    data = request.get_json()
    email = data.get("email")
    amount = data.get("amount")  # USD amount
    user = get_user(email)

    api_key = os.environ.get("NOWPAYMENTS_API_KEY")
    if not api_key:
        return jsonify({"error": "Crypto API key missing"}), 500

    payload = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "bnb",
        "ipn_callback_url": os.environ.get("NOWPAYMENTS_IPN_URL", ""),
        "order_id": f"{email}-{datetime.now().timestamp()}"
    }
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    r = requests.post("https://api.nowpayments.io/v1/invoice", json=payload, headers=headers)
    resp = r.json()

    # Mark paid for 30 days (simulate until IPN callback)
    user["paid_until"] = datetime.now() + timedelta(days=30)

    return jsonify({
        "status": "success",
        "message": f"{email} has access for 30 days",
        "paid_until": user["paid_until"].isoformat(),
        "payment_link": resp.get("invoice_url", "")
    })

# ------------------------
# VENDING MACHINE ENDPOINTS
# ------------------------
def service_response(email, service_name, result_text):
    user = get_user(email)
    if not can_use_service(user, service_name):
        return jsonify({"error": "Free trials finished! Please subscribe."}), 403
    if not (user["paid_until"] and datetime.now() <= user["paid_until"]):
        decrement_trial(user, service_name)
    return jsonify({"result": result_text})

@app.route("/copywriting", methods=["POST"])
def copywriting():
    data = request.get_json()
    email = data.get("email")
    copy_type = data.get("copy_type")
    tone = data.get("tone")
    name = data.get("name")
    result_text = f"Elite {copy_type} for '{name}' in a {tone} tone."
    return service_response(email, "copywriting", result_text)

@app.route("/freelance", methods=["POST"])
def freelance():
    data = request.get_json()
    email = data.get("email")
    job_type = data.get("job_type")
    platform = data.get("platform")
    level = data.get("level")
    result_text = f"Elite {level} {job_type} proposal for {platform}."
    return service_response(email, "freelance", result_text)

@app.route("/business", methods=["POST"])
def business():
    data = request.get_json()
    email = data.get("email")
    niche = data.get("niche")
    output_type = data.get("output")
    result_text = f"Elite {output_type} for niche '{niche}'."
    return service_response(email, "business", result_text)

@app.route("/resume", methods=["POST"])
def resume():
    data = request.get_json()
    email = data.get("email")
    purpose = data.get("purpose")
    experience = data.get("experience")
    skills = data.get("skills")
    job_title = data.get("job_title")
    result_text = f"Elite {purpose} for '{job_title}' with skills {skills}."
    return service_response(email, "resume", result_text)

@app.route("/summary", methods=["POST"])
def summary():
    data = request.get_json()
    email = data.get("email")
    text = data.get("text", "")
    summary_text = text[:100] + "..." if len(text) > 100 else text
    return service_response(email, "summary", summary_text)

@app.route("/title", methods=["POST"])
def title():
    data = request.get_json()
    email = data.get("email")
    content = data.get("content", "")
    title_text = content.split(".")[0][:50] + "..."
    return service_response(email, "title", title_text)

# ------------------------
# RUN SERVER
# ------------------------
if __name__ == "__main__":
    app.run(debug=True)
