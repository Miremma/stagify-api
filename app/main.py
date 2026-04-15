from fastapi import FastAPI                              # framework principal
from fastapi.middleware.cors import CORSMiddleware       # pour autoriser React
from fastapi.staticfiles import StaticFiles              # pour servir les fichiers
from contextlib import asynccontextmanager               # pour le démarrage
from app.database import engine, Base                    # connexion BDD
from app.routers import auth, annonces, candidatures, external_apis  # routers
import os                                                # pour les dossiers


# ════════════════════════════════════════
# DÉMARRAGE DE L'APPLICATION
# ════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    # crée les tables MySQL au démarrage
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


# ════════════════════════════════════════
# CRÉATION DE L'APPLICATION
# ════════════════════════════════════════

app = FastAPI(
    title="Stagify API",
    version="1.0.0",
    description="API pour la plateforme de stages et alternances Stagify",
    lifespan=lifespan
)
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://stagify-front-production.up.railway.app"],  # ton front
    allow_credentials=True,
    allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],


# ════════════════════════════════════════
# DOSSIER UPLOADS
# ════════════════════════════════════════

# crée le dossier uploads/cvs si inexistant
os.makedirs("uploads/cvs", exist_ok=True)

# permet d'accéder aux CVs via /uploads/cvs/fichier.pdf
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ════════════════════════════════════════
# CONFIGURATION CORS
# ════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000",
    "http://localhost:5173",
    "https://stagify-front-production.up.railway.app"
],
    allow_credentials=True,        # autorise les cookies et tokens
    allow_methods=["*"],           # tous les méthodes HTTP
    allow_headers=["*"],           # tous les headers
)

# ════════════════════════════════════════
# BRANCHEMENT DES ROUTERS
# ════════════════════════════════════════

# routes authentification
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Auth"]
)

# routes annonces
app.include_router(
    annonces.router,
    prefix="/api/v1/annonces",
    tags=["Annonces"]
)

# routes candidatures
app.include_router(
    candidatures.router,
    prefix="/api/v1/candidatures",
    tags=["Candidatures"]
)

# routes APIs externes
app.include_router(
    external_apis.router,
    prefix="/api/v1/external",
    tags=["APIs Externes"]
)


# ════════════════════════════════════════
# ROUTE DE TEST
# ════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "message": "Stagify API fonctionne !",
        "version": "1.0.0",
        "docs": "/docs"
    }