from fastapi import FastAPI, Request, Form, UploadFile, File, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models import Base, Staff

import os, shutil, uuid, hashlib, socket
import qrcode

# ---------------- APP ----------------
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

Base.metadata.create_all(bind=engine)

VALID_PSID_LIST = {"45105676", "12345678", "87654321", "11223344"}

# ---------------- DATABASE ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- NETWORK ----------------
def get_lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

BASE_URL = f"http://{get_lan_ip()}:8000"

# ---------------- ROUTES ----------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register", response_class=HTMLResponse)
def register_staff(
    request: Request,
    name: str = Form(...),
    psid: str = Form(...),
    rank: str = Form(...),
    department: str = Form(...),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # VALIDATION
    if not psid.isdigit() or len(psid) != 8:
        return HTMLResponse("PSID must be exactly 8 digits")

    if psid not in VALID_PSID_LIST:
        return HTMLResponse("Invalid PSID")

    if db.query(Staff).filter(Staff.psid == psid).first():
        return HTMLResponse("PSID already registered")

    if photo.content_type not in ["image/jpeg", "image/jpg"]:
        return HTMLResponse("JPEG only")

    # FILE SAVE
    upload_dir = os.path.join(BASE_DIR, "static/uploads")
    qr_dir = os.path.join(BASE_DIR, "static/qrcodes")
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs(qr_dir, exist_ok=True)

    photo_path = os.path.join(upload_dir, f"{psid}.jpg")
    with open(photo_path, "wb") as f:
        shutil.copyfileobj(photo.file, f)

    # QR
    qr_hash = hashlib.sha256((str(uuid.uuid4()) + psid).encode()).hexdigest()
    qr_url = f"{BASE_URL}/verify/{qr_hash}"
    qrcode.make(qr_url).save(os.path.join(qr_dir, f"{psid}.png"))

    staff = Staff(
        name=name,
        psid=psid,
        rank=rank,
        department=department,
        photo=f"/static/uploads/{psid}.jpg",
        qr_hash=qr_hash,
        status="ACTIVE"
    )

    db.add(staff)
    db.commit()

    return templates.TemplateResponse(
        "qr_admin_result.html",
        {
            "request": request,
            "staff": staff,
            "qr_url": f"/static/qrcodes/{psid}.png"
        }
    )

@app.get("/verify/{qr_hash}", response_class=HTMLResponse)
def verify(qr_hash: str, request: Request, db: Session = Depends(get_db)):
    staff = db.query(Staff).filter(Staff.qr_hash == qr_hash).first()
    if not staff:
        return HTMLResponse("<h2>INVALID QR</h2>")
    return templates.TemplateResponse(
        "qr_scan_result.html",
        {"request": request, "staff": staff}
    )
