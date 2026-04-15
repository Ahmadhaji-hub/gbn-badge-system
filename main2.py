import hmac
import hashlib
import qrcode
import io
import time
import csv
import smtplib
from email.mime.text import MIMEText

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


# 📨 EMAIL (MailHog safe)
def send_email(to_email, subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = "test@local.com"
        msg["To"] = to_email

        server = smtplib.SMTP("localhost", 1026)
        server.send_message(msg)
        server.quit()

        print("Email sent ✅")

    except Exception as e:
        print("Email skipped (MailHog not available)")


# 📝 register attendance
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

    send_email(
        "test@email.com",
        "Check-in confirmé",
        f"{username} checked in via {method}"
    )


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


# 📱 badge (🔥 UI جديد)
@app.get("/my-badge/{username}", response_class=HTMLResponse)
def badge_page(username: str):
    username = username.lower()

    if username not in USERS:
        return "User not found ❌"

    return f"""
    <html>
    <head>
    <style>
        body {{
            font-family: Arial;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }}

        .card {{
            background: white;
            padding: 30px;
            border-radius: 20px;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.2);
            width: 320px;
        }}

        h2 {{
            color: #333;
        }}

        button {{
            margin-top: 20px;
            padding: 12px 20px;
            border: none;
            border-radius: 10px;
            background: #667eea;
            color: white;
            font-size: 16px;
            cursor: pointer;
            transition: 0.3s;
        }}

        button:hover {{
            background: #5a67d8;
            transform: scale(1.05);
        }}

        p {{
            color: #777;
        }}
    </style>
    </head>

    <body>

    <div class="card">
        <h2>{username.upper()} Badge</h2>

        <img id="qr" src="/qr/{username}" width="220">

        <p>QR updates every 30 seconds</p>

        <button onclick="checkin()">✅ Remote Check-in</button>
    </div>

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


# 📥 EXPORT CSV
@app.get("/export")
def export_csv():
    today = time.strftime("%Y-%m-%d")
    filename = f"attendance_{today}.csv"

    with open(filename, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["user", "date", "time", "method"])
        writer.writeheader()
        writer.writerows(attendance)

    return FileResponse(filename, media_type='text/csv', filename=filename)


# 🧪 TEST EMAIL
@app.get("/test-email")
def test_email():
    send_email(
        "test@email.com",
        "Test MailHog",
        "MailHog works 🔥"
    )
    return {"status": "email triggered"}
