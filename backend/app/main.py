"""FastAPI-Einstieg. Phase 0: nur Health-Check und Grundgerüst.

Die fachlichen Router (auth, sitzungen, suche, themen, matching, tags, admin)
kommen in den jeweiligen Phasen hinzu und werden hier registriert.
"""
from fastapi import FastAPI

app = FastAPI(title="BL-Protokollbuch", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# Phase 1+:
# from .routers import auth, sitzungen, suche, themen, matching, tags, admin
# app.include_router(auth.router, prefix="/api/auth")
# ...
