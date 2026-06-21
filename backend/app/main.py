"""FastAPI-Einstieg. Phase 0: nur Health-Check und Grundgerüst.

Die fachlichen Router (auth, sitzungen, suche, themen, matching, tags, admin)
kommen in den jeweiligen Phasen hinzu und werden hier registriert.
"""
from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from .routers import search, sitzungen

app = FastAPI(title="BL-Protokollbuch", version="0.1.0")

# Im Dev läuft das Frontend (Vite) auf einem anderen Port -> CORS erlauben.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(search.router, prefix="/api/search", tags=["suche"])
app.include_router(sitzungen.router, prefix="/api/sitzungen", tags=["sitzungen"])

# Folgephasen:
# from .routers import auth, sitzungen, themen, matching, tags, admin
# app.include_router(auth.router, prefix="/api/auth")
# ...
