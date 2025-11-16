# app.py
import os
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()  # Load .env file

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
CORS(app, supports_credentials=True)

# ------------------------
# ENV VARIABLES
# ------------------------
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")
BNB_WALLET = os.getenv("BNB_WALLET")

# ------------------------
# ADMIN CREDENTIALS
# ------------------------
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# ------------------------
# USER DATA (mock)
# ------------------------
users = {}  # format: {email: {"trials": {"copywriting":3, "freelance":3, "business":3}, "paid_until": datetime}}

FREE_TRIALS = 3
SUB_DURATION_DAYS = 30  # Paid subscription duration

# ------------------------
# ADMIN LOGIN
# ------------------------
@app.route("/admin-login", methods=["POST"])
def admin_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session["admin_logged_in"] = True
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "error": "Invalid email or password"}), 401

@app.route("/admin-dashboard", methods=["GET"])
def admin_dashboard():
    if session.get("admin_logged_in"):
        return jsonify({"status":"success", "users": users})
    else:
        return "Unauthorized", 401

# ------------------------
# USER TRIALS CHECK
# ------------------------
@app.route("/user-trials", methods=["GET"])
def user_trials():
    email = request.args.get("email")
    if email not in users:
        # Create new user with free trials
        users[email] = {
            "trials": {"copywriting": FREE_TRIALS, "freelance": FREE_TRIALS, "business": FREE_TRIALS},
            "paid_until": None
        }
    user = users[email]

    paid = user["paid_until"] and datetime.utcnow() < user["paid_until"]
    return jsonify({"trials": user["trials"], "paid": paid})

# ------------------------
# PAYPAL PAYMENT INIT
# ------------------------
@app.route("/paypal-init", methods=["POST"])
def paypal_init():
    data = request.get_json()
    email = data.get("email")
    amount = data.get("amount")
    # Here you'd normally call PayPal API with PAYPAL_CLIENT_ID + PAYPAL_SECRET
    # After successful payment, update user's paid_until
    users[email]["paid_until"] = datetime.utcnow() + timedelta(days=SUB_DURATION_DAYS)
    return jsonify({"status": "success", "redirect_url": "https://www.paypal.com/checkout"})

# ------------------------
# CRYPTO PAYMENT INIT (NowPayments)
# ------------------------
@app.route("/crypto-pay", methods=["POST"])
def crypto_pay():
    data = request.get_json()
    email = data.get("email")
    amount = data.get("amount")
    # Here you'd normally call NowPayments API with NOWPAYMENTS_API_KEY
    users[email]["paid_until"] = datetime.utcnow() + timedelta(days=SUB_DURATION_DAYS)
    return jsonify({"status": "success", "invoice_url": "https://nowpayments.io/invoice/xyz"})

# ------------------------
# VENDING MACHINE ENDPOINTS
# ------------------------
@app.route("/copywriting", methods=["POST"])
def copywriting():
    data = request.get_json()
    email = data.get("email")
    user = users[email]
    # Check trials or subscription
    if (user["trials"]["copywriting"] <= 0) and (not user["paid_until"] or datetime.utcnow() > user["paid_until"]):
        return jsonify({"error": "Free trials over. Subscribe to continue."}), 403
    # Deduct trial if not paid
    if not user["paid_until"] or datetime.utcnow() > user["paid_until"]:
        user["trials"]["copywriting"] -= 1

    copy_type = data.get("copy_type")
    tone = data.get("tone")
    name = data.get("name")
    result_text = f"Elite {copy_type} for '{name}' in a {tone} tone."
    return jsonify({"result": result_text})

@app.route("/freelance", methods=["POST"])
def freelance():
    data = request.get_json()
    email = data.get("email")
    user = users[email]
    if (user["trials"]["freelance"] <= 0) and (not user["paid_until"] or datetime.utcnow() > user["paid_until"]):
        return jsonify({"error": "Free trials over. Subscribe to continue."}), 403
    if not user["paid_until"] or datetime.utcnow() > user["paid_until"]:
        user["trials"]["freelance"] -= 1
    result_text = f"Elite proposal for {data.get('job_type')} on {data.get('platform')} at {data.get('level')} level."
    return jsonify({"result": result_text})

@app.route("/business-plan", methods=["POST"])
def business_plan():
    data = request.get_json()
    email = data.get("email")
    user = users[email]
    if (user["trials"]["business"] <= 0) and (not user["paid_until"] or datetime.utcnow() > user["paid_until"]):
        return jsonify({"error": "Free trials over. Subscribe to continue."}), 403
    if not user["paid_until"] or datetime.utcnow() > user["paid_until"]:
        user["trials"]["business"] -= 1
    result_text = f"Elite business idea for {data.get('niche')} in {data.get('output')} format."
    return jsonify({"result": result_text})

# ------------------------
# RUN SERVER
# ------------------------
if __name__ == "__main__":
    app.run(debug=True)
