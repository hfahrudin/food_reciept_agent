from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from routers import v1, v2, v3
from dotenv import load_dotenv

load_dotenv()

# Initialize FastAPI app
app = FastAPI(redirect_slashes=False)

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