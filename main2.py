import hmac
import hashlib
import qrcode
import io
import time

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse

# 🔐 secret key
SECRET_KEY = "kousayanousa"

app = FastAPI()

# 👥 users (always lowercase)
USERS = ["ahmad", "icaro", "soufian"]

# 📝 attendance storage (temporary)
attendance = []


# 🔑 generate QR
def generate_code(user_id):
    user_id = user_id.lower()
    timestamp = int(time.time() / 30)
    message = f"{user_id}:{timestamp}"

    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{user_id}:{timestamp}:{signature}"


# ✅ verify QR
def verify_code(code):
    try:
        user_id, timestamp, signature = code.split(":")
        user_id = user_id.lower()
        timestamp = int(timestamp)
    except:
        return None

    current_time = int(time.time() / 30)

    for t in [current_time, current_time - 1]:
        message = f"{user_id}:{t}"

        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if signature == expected_signature:
            return user_id

    return None


# 📝 register attendance
def register_attendance(username, method):
    attendance.append({
        "user": username,
        "time": time.strftime("%H:%M:%S"),
        "method": method
    })


# 🔳 QR endpoint
@app.get("/qr/{username}")
def get_qr(username: str):
    username = username.lower()

    if username not in USERS:
        return {"error": "User not found ❌"}

    code = generate_code(username)

    img = qrcode.make(code)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


# 📱 badge page
@app.get("/my-badge/{username}", response_class=HTMLResponse)
def badge_page(username: str):
    username = username.lower()

    if username not in USERS:
        return "User not found ❌"

    return f"""
    <html>
    <body style="text-align:center; font-family:Arial;">
        <h2>{username.upper()} Badge</h2>

        <img id="qr" src="/qr/{username}" width="300">
        <p>QR changes every 30 seconds</p>

        <br><br>

        <button onclick="checkin()" style="padding:10px 20px; font-size:16px;">
            Remote Check-in
        </button>

        <script>
        setInterval(() => {{
            document.getElementById("qr").src = "/qr/{username}?" + new Date().getTime();
        }}, 30000);

        function checkin() {{
            fetch("/checkin/{username}")
            .then(res => res.json())
            .then(data => alert(data.status));
        }}
        </script>
    </body>
    </html>
    """


# 🟢 QR scan (simulate kiosk)
@app.get("/scan/{code}")
def scan(code: str):
    user = verify_code(code)

    if not user:
        return {"status": "INVALID QR ❌"}

    register_attendance(user, "qr")

    return {"status": f"{user} checked in via QR ✅"}


# 🔵 Remote check-in
@app.get("/checkin/{username}")
def checkin(username: str):
    username = username.lower()

    if username not in USERS:
        return {"status": "User not found ❌"}

    register_attendance(username, "remote")

    return {"status": f"{username} checked in remotely ✅"}


# 📊 attendance list
@app.get("/attendance")
def get_attendance():
    return attendance
