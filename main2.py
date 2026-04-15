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

SECRET_KEY = "kousayanousa"

app = FastAPI()

USERS = ["ahmad", "icaro", "soufian"]
attendance = []


# 🔑 QR
def generate_code(user_id):
    timestamp = int(time.time() / 30)
    message = f"{user_id}:{timestamp}"

    signature = hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return f"{user_id}:{timestamp}:{signature}"


# ✅ verify
def verify_code(code):
    try:
        user_id, timestamp, signature = code.split(":")
        timestamp = int(timestamp)
    except:
        return None

    current_time = int(time.time() / 30)

    for t in [current_time, current_time - 1]:
        message = f"{user_id}:{t}"
        expected = hmac.new(
            SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        if signature == expected:
            return user_id

    return None


# 📨 Email
def send_email(to_email, subject, body):
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = "test@local.com"
        msg["To"] = to_email

        server = smtplib.SMTP("localhost", 1026)
        server.send_message(msg)
        server.quit()
    except:
        pass


# 📝 attendance
def register_attendance(username, method):
    today = time.strftime("%Y-%m-%d")

    for r in attendance:
        if r["user"] == username and r["date"] == today:
            return

    attendance.append({
        "user": username,
        "date": today,
        "time": time.strftime("%H:%M:%S"),
        "method": method
    })

    send_email("test@email.com", "Check-in", f"{username} via {method}")


# 🔳 QR
@app.get("/qr/{username}")
def get_qr(username: str):
    code = generate_code(username)
    img = qrcode.make(code)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


# 📱 Badge UI 🔥🔥🔥
@app.get("/my-badge/{username}", response_class=HTMLResponse)
def badge_page(username: str):

    return f"""
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body {{
    font-family: Arial;
    background: linear-gradient(135deg, #667eea, #764ba2);
    display:flex;
    justify-content:center;
    align-items:center;
    height:100vh;
    margin:0;
}}

.card {{
    background:white;
    padding:30px;
    border-radius:20px;
    text-align:center;
    width:340px;
    box-shadow:0 10px 25px rgba(0,0,0,0.2);
}}

button {{
    padding:12px;
    border:none;
    border-radius:10px;
    background:#667eea;
    color:white;
    cursor:pointer;
}}

#popup {{
    position:fixed;
    top:20px;
    right:20px;
    background:green;
    color:white;
    padding:10px;
    border-radius:10px;
    display:none;
}}

</style>
</head>

<body>

<div class="card">
    <h2>{username.upper()}</h2>

    <img id="qr" src="/qr/{username}" width="200">

    <p>Refresh in <span id="count">30</span>s</p>

    <button onclick="checkin()">Check-in</button>

    <canvas id="chart" width="300"></canvas>
</div>

<div id="popup">✔ Done</div>

<audio id="sound" src="https://www.soundjay.com/buttons/sounds/button-3.mp3"></audio>

<script>
let counter = 30;

setInterval(() => {{
    counter--;
    document.getElementById("count").innerText = counter;

    if(counter === 0) {{
        document.getElementById("qr").src = "/qr/{username}?"+Date.now();
        counter = 30;
    }}
}},1000);


function checkin() {{
    fetch("/checkin/{username}")
    .then(res=>res.json())
    .then(data=>{{
        showPopup(data.status);
        document.getElementById("sound").play();
        loadChart();
    }});
}}

function showPopup(msg) {{
    let p=document.getElementById("popup");
    p.innerText=msg;
    p.style.display="block";
    setTimeout(()=>p.style.display="none",2000);
}}


// 📊 Chart
function loadChart() {{
    fetch("/attendance")
    .then(r=>r.json())
    .then(data=>{{
        let qr=0, remote=0;
        data.forEach(x=>{{
            if(x.method=="qr") qr++;
            else remote++;
        }});

        new Chart(document.getElementById("chart"), {{
            type: 'bar',
            data: {{
                labels: ['QR', 'Remote'],
                datasets: [{{
                    label: 'Attendance',
                    data: [qr, remote]
                }}]
            }}
        }});
    }});
}}

loadChart();
</script>

</body>
</html>
"""


# 🟢 scan
@app.get("/scan/{code}")
def scan(code: str):
    user = verify_code(code)
    if not user:
        return {"status": "invalid"}

    register_attendance(user, "qr")
    return {"status": "QR OK"}


# 🔵 remote
@app.get("/checkin/{username}")
def checkin(username: str):
    register_attendance(username, "remote")
    return {"status": "done"}


# 📊 attendance
@app.get("/attendance")
def get_attendance():
    return attendance


# 📥 export
@app.get("/export")
def export_csv():
    filename="attendance.csv"
    with open(filename,"w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=["user","date","time","method"])
        writer.writeheader()
        writer.writerows(attendance)

    return FileResponse(filename)
