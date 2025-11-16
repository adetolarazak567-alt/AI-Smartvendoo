from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow frontend requests

# ------------------------
# VENDING MACHINE BACKEND
# ------------------------

# Copywriting Generator
@app.route("/copywriting", methods=["POST"])
def copywriting():
    data = request.get_json()
    copy_type = data.get("copy_type")
    tone = data.get("tone")
    name = data.get("name")
    result_text = f"Generated {copy_type} for '{name}' in a {tone} tone."
    return jsonify({"result": result_text})

# Summary Generator
@app.route("/summary", methods=["POST"])
def summary():
    data = request.get_json()
    text = data.get("text", "")
    summary_text = text[:100] + "..." if len(text) > 100 else text
    return jsonify({"result": summary_text})

# Title Generator
@app.route("/title", methods=["POST"])
def title_generator():
    data = request.get_json()
    content = data.get("content", "")
    title_text = content.split(".")[0][:50] + "..."
    return jsonify({"result": title_text})

# User Trials (always unlimited for frontend)
@app.route("/user-trials", methods=["GET"])
def user_trials():
    return jsonify({
        "trials": {
            "copywriting": 100,
            "summary": 100,
            "title": 100
        },
        "paid": True
    })

# Dummy PayPal endpoint
@app.route("/paypal-init", methods=["POST"])
def paypal_init():
    data = request.get_json()
    amount = data.get("amount")
    return jsonify({"status": "success", "redirect_url": "https://www.paypal.com/checkout"})

# Run server
if __name__ == "__main__":
    app.run(debug=True)
