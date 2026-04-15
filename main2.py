import hmac
import hashlib
import qrcode
import io
import time
import csv

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse

# 🔐 secret key
SECRET_KEY = "kousayanousa"

app = FastAPI()

# 👥 users
USERS = ["ahmad", "icaro", "soufian"]

# 📝 attendance storage
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


# 📝 register attendance (مع منع التكرار)
def register_attendance(username, method):
    today = time.strftime("%Y-%m-%d")

    for record in attendance:
        if record["user"] == username and record["date"] == today:
            return

    attendance.append({
        "user": username,
        "date": today,
        "time": time.strftime("%H:%M:%S"),
        "method": method
    })


# 🔳 QR
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


# 📱 badge
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

        <br><br>

        <button onclick="checkin()">Remote Check-in</button>

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


# 🟢 scan
@app.get("/scan/{code}")
def scan(code: str):
    user = verify_code(code)

    if not user:
        return {"status": "INVALID QR ❌"}

    register_attendance(user, "qr")

    return {"status": f"{user} checked in via QR ✅"}


# 🔵 remote
@app.get("/checkin/{username}")
def checkin(username: str):
    username = username.lower()

    if username not in USERS:
        return {"status": "User not found ❌"}

    register_attendance(username, "remote")

    return {"status": f"{username} checked in remotely ✅"}


# 📊 show attendance
@app.get("/attendance")
def get_attendance():
    return attendance


# 📥 EXPORT TO EXCEL (CSV)
@app.get("/export")
def export_csv():
    today = time.strftime("%Y-%m-%d")
    filename = f"attendance_{today}.csv"

    with open(filename, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["user", "date", "time", "method"])
        writer.writeheader()
        writer.writerows(attendance)

    return FileResponse(filename, media_type='text/csv', filename=filename)
