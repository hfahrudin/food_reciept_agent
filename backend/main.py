from fastapi import FastAPI, Request,  File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from dotenv import load_dotenv
from agent import AgentPawcha
from tools import ReceiptDB
import os
load_dotenv()

# Initialize FastAPI app
app = FastAPI(redirect_slashes=False)

receipt_db = ReceiptDB("media/receipts.db")

agent_pawcha = AgentPawcha(reciept_db = receipt_db)

# Ensure the upload directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Health check route
@app.get("/")
def read_root():
    return PlainTextResponse(content="Healthy", status_code=200)

@app.post("/chat")
async def stream(request: Request):
    return StreamingResponse((), media_type="text/event-stream")


@app.post("/receipt/add")
async def add_receipt(file: UploadFile = File(...), date: str = Form(...)):
    # Only accept images
    if not file.content_type.startswith("image/"):
        return PlainTextResponse(content="Invalid file type", status_code=400)
    
    # Save the uploaded image
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        receipt_db.add(date=date, image_path=file_path)
    except ValueError as e:
        os.remove(file_path)  # cleanup
        return PlainTextResponse(content=f"{str(e)}", status_code=400)

    os.remove(file_path)  # cleanup
    return PlainTextResponse(content="Receipt processed and saved", status_code=200)