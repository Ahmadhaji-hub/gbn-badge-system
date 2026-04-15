import hmac
import hashlib
import qrcode
import io
import time

from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse

# 🔐 secret key (غيرها لاحقاً)
SECRET_KEY = "kousayanousa"

app = FastAPI()

# 👥 users (مؤقتاً - لاحقاً database)
USERS = ["Ahmad", "Icaro", "Soufian"]


# 🔑 generate dynamic + secure QR
def generate_code(user_id):
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
        timestamp = int(timestamp)
    except:
        return False

    current_time = int(time.time() / 30)

    for t in [current_time, current_time - 1]:
        message = f"{user_id}:{t}"

        expected_signature = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if signature == expected_signature:
            return True

    return False


# 🔳 QR لكل user
@app.get("/qr/{username}")
def get_qr(username: str):
    if username not in USERS:
        return {"error": "User not found ❌"}

    code = generate_code(username)

    img = qrcode.make(code)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


# 📱 صفحة badge لكل user
@app.get("/my-badge/{username}", response_class=HTMLResponse)
def badge_page(username: str):
    if username not in USERS:
        return "User not found ❌"

    return f"""
    <html>
    <body style="text-align:center; font-family:Arial;">
        <h2>{username} Badge</h2>
        <img id="qr" src="/qr/{username}" width="300">
        <p>QR changes every 30 seconds</p>

        <script>
        setInterval(() => {{
            document.getElementById("qr").src = "/qr/{username}?" + new Date().getTime();
        }}, 30000);
        </script>
    </body>
    </html>
    """


# 🧪 endpoint للتحقق (اختياري)
@app.get("/verify/{code}")
def verify(code: str):
    if verify_code(code):
        return {"status": "VALID ✅"}
    else:
        return {"status": "INVALID ❌"}
