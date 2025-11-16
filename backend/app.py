# app.py
import os
import time
from flask import Flask, request, jsonify, session
from flask_cors import CORS
import requests
import openai
from functools import wraps
from datetime import datetime

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "razzysecretkey123")

# --- OpenAI config ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # change if needed
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

# --- Payment / external keys ---
PAYPAL_RETURN_URL = os.getenv("PAYPAL_RETURN_URL", "https://yourdomain.com/paypal-success")
PAYPAL_CANCEL_URL = os.getenv("PAYPAL_CANCEL_URL", "https://yourdomain.com/paypal-cancel")
NOWPAYMENTS_API_KEY = os.getenv("NOWPAYMENTS_API_KEY")  # NowPayments API key
NOWPAYMENTS_CALLBACK_URL = os.getenv("NOWPAYMENTS_CALLBACK_URL", PAYPAL_RETURN_URL)

# --- Admin credentials ---
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "adetolarazak567@gmail.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "@razzyadmin567")
# admin second-tier key for admin dashboard direct (optional)
ADMIN_DASH_KEY = os.getenv("ADMIN_DASH_KEY", "@razzyadminAI567")

# --- In-memory stores (replace with DB for production) ---
USERS = {}  # email -> {password, paid(bool), created_at, country}
# usage: per-user per-vm usage counts
USAGE = {}  # key -> { vm_name:int }
# vms list
VENDING_MACHINES = [
    "copywriting","freelance","resume","business","social","ebook","branding","dropshipping","summary","title"
]
# default free trials per vm
FREE_TRIALS = int(os.getenv("FREE_TRIALS_PER_VM", "3"))

# helper: get client key (email or ip)
def client_key():
    data = request.get_json(silent=True) or {}
    email = data.get("email") or request.args.get("email")
    if email:
        return f"email::{email.lower()}"
    # fallback to IP
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    return f"ip::{ip}"

def init_usage_for(key):
    if key not in USAGE:
        USAGE[key] = {vm:0 for vm in VENDING_MACHINES}
    return USAGE[key]

def trials_left_for(key, vm):
    usage = init_usage_for(key)
    used = usage.get(vm, 0)
    # if user has paid -> unlimited for the subscription month; we'll just check USERS map
    email = None
    if key.startswith("email::"):
        email = key.split("::",1)[1]
    paid = False
    if email and email in USERS:
        paid = USERS[email].get("paid", False)
    if paid:
        return 99999
    left = FREE_TRIALS - used
    return max(0, left)

def use_trial(key, vm):
    usage = init_usage_for(key)
    usage[vm] = usage.get(vm, 0) + 1

# Admin-required decorator (session-based)
def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if session.get("admin"):
            return f(*args, **kwargs)
        return jsonify({"error":"admin_required"}), 401
    return wrapped

# -------------------------
# Signup & Login (optional)
# -------------------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    email = (data.get("email") or "").lower().strip()
    password = data.get("password")
    if not email or not password:
        return jsonify({"status":"error","message":"email,password required"}), 400
    if email in USERS:
        return jsonify({"status":"error","message":"Email exists"}), 400
    USERS[email] = {"password":password, "paid": False, "created_at": time.time(), "country": data.get("country","")}
    return jsonify({"status":"success","message":"Account created"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").lower().strip()
    password = data.get("password")
    # admin shortcut
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session["admin"] = True
        session["admin_email"] = email
        return jsonify({"status":"success","admin":True})
    if email not in USERS or USERS[email]["password"] != password:
        return jsonify({"status":"error","message":"Invalid credentials"}), 401
    session["user"] = email
    return jsonify({"status":"success"})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status":"success"})

# -------------------------
# Admin routes
# -------------------------
@app.route("/admin-login", methods=["POST"])
def admin_login_api():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session["admin"] = True
        session["admin_email"] = email
        return jsonify({"status":"success"})
    return jsonify({"status":"error","message":"Invalid admin credentials"}), 401

@app.route("/admin-data", methods=["GET"])
@admin_required
def admin_data():
    # build stats
    total_users = len(USERS)
    active_24h = sum(1 for u in USERS.values() if time.time() - u["created_at"] < 86400)
    banned = 0  # placeholder
    earnings = "N/A"  # if integrated with payments, read db / accounting
    # serialize recent users
    recent_users = []
    for email,info in list(USERS.items())[-200:]:
        recent_users.append({
            "email": email,
            "country": info.get("country",""),
            "trial_uses_left": {vm: FREE_TRIALS - USAGE.get(f"email::{email}",{}).get(vm,0) for vm in VENDING_MACHINES},
            "usage_count": USAGE.get(f"email::{email}",{}),
            "created_at": int(info.get("created_at", time.time()))
        })
    recent_logs = []  # you can append logs to an array in production
    return jsonify({
        "total_users": total_users,
        "active_users_last_24h": active_24h,
        "banned_users": banned,
        "earnings": earnings,
        "recent_users": recent_users,
        "recent_logs": recent_logs,
        "usage_snapshot": USAGE
    })

# -------------------------
# Payments (simple)
# -------------------------
@app.route("/paypal-init", methods=["POST"])
def paypal_init():
    data = request.get_json() or {}
    amount = data.get("amount")
    # In production: use PayPal API (server SDK) to create order and return approve url.
    # Here we return a redirect URL to the configured return URL with amount query for client to continue.
    redirect = PAYPAL_RETURN_URL + f"?amount={amount}"
    return jsonify({"status":"success", "redirect_url": redirect})

@app.route("/payment-success", methods=["POST"])
def payment_success():
    # mark user as paid (client should POST email)
    data = request.get_json() or {}
    email = (data.get("email") or "").lower()
    if not email:
        return jsonify({"status":"error","message":"email required"}), 400
    if email not in USERS:
        USERS[email] = {"password":None, "paid": True, "created_at": time.time(), "country": ""}
    else:
        USERS[email]["paid"] = True
    return jsonify({"status":"success","message":"marked paid"})

@app.route("/btc-init", methods=["POST"])
def btc_init():
    # create invoice via NowPayments (requires NOWPAYMENTS_API_KEY)
    data = request.get_json() or {}
    amount = data.get("amount")
    email = (data.get("email") or "").lower()
    if not NOWPAYMENTS_API_KEY:
        return jsonify({"status":"error","message":"NowPayments API key not configured"}), 500
    payload = {
        "price_amount": amount,
        "price_currency": "usd",
        "pay_currency": "btc",
        "ipn_callback_url": NOWPAYMENTS_CALLBACK_URL,
        "order_id": email or f"guest-{int(time.time())}"
    }
    headers = {"x-api-key": NOWPAYMENTS_API_KEY, "Content-Type":"application/json"}
    try:
        r = requests.post("https://api.nowpayments.io/v1/invoice", json=payload, headers=headers, timeout=15)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@app.route("/nowpayments-webhook", methods=["POST"])
def nowpayments_webhook():
    # Called by NowPayments IPN - mark users paid when payment_status indicates success
    data = request.get_json() or {}
    if data.get("payment_status") == "finished":
        order_id = data.get("order_id")
        # if order_id is email, mark paid
        if order_id and order_id.startswith("email::"):
            email = order_id.split("::",1)[1]
            if email in USERS:
                USERS[email]["paid"] = True
        elif order_id and "@" in order_id:
            email = order_id
            if email in USERS:
                USERS[email]["paid"] = True
    return jsonify({"status":"ok"})

# -------------------------
# Utility: call OpenAI
# -------------------------
def call_openai_chat(prompt, system=None, temperature=0.7, max_tokens=600):
    if not OPENAI_API_KEY:
        # fallback: return prompt preview if no key
        return f"[OpenAI key missing] {prompt[:1000]}"
    messages = []
    if system:
        messages.append({"role":"system","content":system})
    messages.append({"role":"user","content":prompt})
    resp = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    # pick assistant reply
    return resp["choices"][0]["message"]["content"].strip()

# -------------------------
# Vending machines (realistic prompts)
# -------------------------
def generate_and_handle(vm_name, prompt, email_key=None):
    key = email_key or client_key()
    left = trials_left_for(key, vm_name)
    # if not paid and no trials left
    # note: trials_left_for returns 99999 if paid
    if left <= 0:
        return jsonify({"result":"Free trials used up. Please subscribe to continue."}), 402
    # call OpenAI
    try:
        out = call_openai_chat(prompt, system=f"You are an expert {vm_name} assistant. Produce a high-quality response.")
    except Exception as e:
        out = f"[OpenAI error] {str(e)}"
    # record usage if not paid
    # check if email in key and paid
    if key.startswith("email::"):
        email = key.split("::",1)[1]
        paid = USERS.get(email,{}).get("paid", False)
    else:
        paid = False
    if not paid:
        use_trial(key, vm_name)
    # increment global usage snapshot
    init_usage_for(key)  # ensures key present
    return jsonify({"result": out, "trials_left": trials_left_for(key, vm_name)})

@app.route("/copywriting", methods=["POST"])
def copywriting():
    d = request.get_json() or {}
    copy_type = d.get("copy_type","ad")
    tone = d.get("tone","friendly")
    name = d.get("name","Product")
    email = (d.get("email") or "").lower()
    prompt = (
        f"Write a high-converting {copy_type} for \"{name}\" in a {tone} tone. "
        "Include a short headline (1 line), 3 short bullets/benefits, and a 1-paragraph call-to-action. "
        "Keep it persuasive and concise."
    )
    key = f"email::{email}" if email else None
    return generate_and_handle("copywriting", prompt, key)

@app.route("/freelance", methods=["POST"])
def freelance():
    d = request.get_json() or {}
    job_type = d.get("job_type","web_dev")
    platform = d.get("platform","upwork")
    level = d.get("level","beginner")
    details = d.get("details","")
    email = (d.get("email") or "").lower()
    prompt = (
        f"Create a winning freelance proposal for a {job_type} job on {platform}. "
        f"Applicant level: {level}. Include: a short intro (2 lines), proposed scope, timeline, deliverables, and pricing guideline. {details}"
    )
    key = f"email::{email}" if email else None
    return generate_and_handle("freelance", prompt, key)

@app.route("/social", methods=["POST"])
def social():
    d = request.get_json() or {}
    platform = d.get("platform","TikTok")
    type_ = d.get("type","captions")
    topic = d.get("topic","")
    email = (d.get("email") or "").lower()
    prompt = (
        f"Generate {type_} for {platform} about '{topic}'. "
        "If captions, give 10 caption options. If hooks, give 10 short hooks. If hashtags, give 15 relevant hashtags."
    )
    key = f"email::{email}" if email else None
    return generate_and_handle("social", prompt, key)

@app.route("/ebook", methods=["POST"])
def ebook():
    d = request.get_json() or {}
    length = int(d.get("length",10))
    style = d.get("style","informative")
    topic = d.get("topic","")
    structure = d.get("structure","")
    email = (d.get("email") or "").lower()
    prompt = (
        f"Create an ebook of approximately {length} pages on '{topic}' in {style} style. "
        f"Return a structured outline with chapter titles and 3-6 bullet points per chapter. {structure}"
    )
    key = f"email::{email}" if email else None
    return generate_and_handle("ebook", prompt, key)

@app.route("/branding", methods=["POST"])
def branding():
    d = request.get_json() or {}
    style = d.get("style","minimalist")
    output = d.get("output","identity")
    name = d.get("name","Brand")
    description = d.get("description","")
    email = (d.get("email") or "").lower()
    prompt = f"Generate {output} for brand '{name}' described as: {description}. Style: {style}. Provide tone, slogan ideas, color palette suggestions, and 3 logo prompt ideas for AI image generator."
    key = f"email::{email}" if email else None
    return generate_and_handle("branding", prompt, key)

@app.route("/dropshipping", methods=["POST"])
def dropshipping():
    d = request.get_json() or {}
    type_ = d.get("type","product")
    platform = d.get("platform","tiktok")
    niche = d.get("niche","general")
    email = (d.get("email") or "").lower()
    prompt = f"Provide a {type_} for dropshipping in the '{niche}' niche on {platform}. Include product ideas, supplier hints, price range, and ad angle."
    key = f"email::{email}" if email else None
    return generate_and_handle("dropshipping", prompt, key)

@app.route("/resume", methods=["POST"])
def resume():
    d = request.get_json() or {}
    purpose = d.get("purpose","resume")
    experience = d.get("experience","")
    skills = d.get("skills","")
    title = d.get("title","")
    email = (d.get("email") or "").lower()
    prompt = f"Optimize a {purpose} for job title '{title}'. Experience: {experience}. Skills: {skills}. Return a polished resume summary, 3 bullet achievements, and a LinkedIn headline."
    key = f"email::{email}" if email else None
    return generate_and_handle("resume", prompt, key)

@app.route("/business", methods=["POST"])
def business():
    d = request.get_json() or {}
    output = d.get("output","business plan")
    niche = d.get("niche","general")
    email = (d.get("email") or "").lower()
    prompt = f"Generate {output} for niche '{niche}'. Include concept, target audience, revenue streams, basic marketing plan, and quick MVP steps."
    key = f"email::{email}" if email else None
    return generate_and_handle("business", prompt, key)

@app.route("/summary", methods=["POST"])
def summary_route():
    d = request.get_json() or {}
    text = d.get("text","")
    email = (d.get("email") or "").lower()
    prompt = f"Summarize the following text into a concise paragraph:\n\n{text}"
    key = f"email::{email}" if email else None
    return generate_and_handle("summary", prompt, key)

@app.route("/title", methods=["POST"])
def title_route():
    d = request.get_json() or {}
    content = d.get("content","")
    email = (d.get("email") or "").lower()
    prompt = f"Suggest 10 catchy titles for the following content: {content}"
    key = f"email::{email}" if email else None
    return generate_and_handle("title", prompt, key)

# -------------------------
# Trials endpoint (frontend uses this)
# -------------------------
@app.route("/user-trials", methods=["GET"])
def user_trials():
    # frontend may pass email as query param
    email = (request.args.get("email") or "").lower()
    key = f"email::{email}" if email else client_key()
    trials = { vm: trials_left_for(key, vm) for vm in VENDING_MACHINES }
    paid = False
    if email and email in USERS:
        paid = USERS[email].get("paid", False)
    return jsonify({"trials": trials, "paid": paid})

# -------------------------
# Run app
# -------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
