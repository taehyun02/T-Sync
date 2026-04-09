from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import routes, stations, vehicles, predictions

app = FastAPI(title="T-Sync Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 나중에 프론트 주소로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(routes.router)
app.include_router(stations.router)
app.include_router(vehicles.router)
app.include_router(predictions.router)