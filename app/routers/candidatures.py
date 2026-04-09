from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession        # session BDD
from sqlalchemy import select                          # requêtes SQL
from app.database import get_db                        # fonction session BDD
from app.models import (                               # modèles
    Candidature,      # modèle candidature
    Annonce,          # modèle annonce
    Utilisateur,      # modèle utilisateur
    RoleUtilisateur   # rôles utilisateur
)
from app.schemas import (                              # schémas
    CandidatureUpdate,   # schéma pour modifier
    CandidatureResponse  # schéma pour répondre
)
from app.auth import get_current_user  # vérifie la connexion
from typing import List, Optional      # types Python
import shutil                          # pour copier les fichiers
import os                              # pour gérer les dossiers

# crée le router
router = APIRouter()

# dossier où les CVs seront stockés sur le serveur
CV_FOLDER = "uploads/cvs"
os.makedirs(CV_FOLDER, exist_ok=True)  # crée le dossier si inexistant


# ════════════════════════════════════════
# ROUTE 1 : POSTULER AVEC UPLOAD CV
# POST /api/v1/candidatures/
# ════════════════════════════════════════

@router.post(
    "/",
    response_model=CandidatureResponse,
    status_code=201
)
async def postuler(
    annonce_id: int = Form(...),                     # id annonce depuis formulaire
    lettre_motivation: Optional[str] = Form(None),   # lettre optionnelle
    cv: Optional[UploadFile] = File(None),           # fichier CV optionnel
    current_user: Utilisateur = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # vérifie que c'est bien un étudiant
    if current_user.role != RoleUtilisateur.ETUDIANT:
        raise HTTPException(
            status_code=403,
            detail="Seuls les étudiants peuvent postuler"
        )

    # vérifie que l'annonce existe
    result = await db.execute(
        select(Annonce).where(Annonce.id == annonce_id)
    )
    annonce = result.scalar_one_or_none()
    if not annonce:
        raise HTTPException(status_code=404, detail="Annonce non trouvée")

    # vérifie que l'annonce est encore active
    if not annonce.est_active:
        raise HTTPException(
            status_code=400,
            detail="Cette annonce n'est plus active"
        )

    # vérifie que l'étudiant n'a pas déjà postulé
    result = await db.execute(
        select(Candidature).where(
            Candidature.etudiant_id == current_user.id,
            Candidature.annonce_id == annonce_id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Vous avez déjà postulé à cette annonce"
        )

    # sauvegarde le CV si un fichier a été fourni
    cv_url = None
    if cv and cv.filename:
        # récupère l'extension du fichier (.pdf, .docx…)
        extension = cv.filename.split(".")[-1]

        # crée un nom de fichier unique
        nom_fichier = f"cv_{current_user.id}_{annonce_id}.{extension}"
        chemin = f"{CV_FOLDER}/{nom_fichier}"

        # sauvegarde le fichier sur le serveur
        with open(chemin, "wb") as buffer:
            shutil.copyfileobj(cv.file, buffer)

        # URL pour accéder au CV
        cv_url = f"/uploads/cvs/{nom_fichier}"

    # crée la candidature en base de données
    candidature = Candidature(
        annonce_id=annonce_id,
        etudiant_id=current_user.id,
        lettre_motivation=lettre_motivation,
        cv_url=cv_url
    )

    db.add(candidature)           # ajoute à la session
    await db.flush()               # sauvegarde en BDD
    await db.refresh(candidature)  # relit depuis la BDD

    # retourne uniquement les champs simples (sans relations)
    return {
        "id": candidature.id,
        "statut": candidature.statut,
        "lettre_motivation": candidature.lettre_motivation,
        "cv_url": candidature.cv_url,
        "annonce_id": candidature.annonce_id,
        "etudiant_id": candidature.etudiant_id,
        "created_at": candidature.created_at,
    }


# ════════════════════════════════════════
# ROUTE 2 : MES CANDIDATURES (ÉTUDIANT)
# GET /api/v1/candidatures/mes-candidatures
# ════════════════════════════════════════

@router.get(
    "/mes-candidatures",
    response_model=List[CandidatureResponse]
)
async def mes_candidatures(
    current_user: Utilisateur = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # récupère toutes les candidatures de l'étudiant connecté
    result = await db.execute(
        select(Candidature).where(
            Candidature.etudiant_id == current_user.id
        ).order_by(Candidature.created_at.desc())
    )
    candidatures = result.scalars().all()

    # retourne les données sans les relations
    return [
        {
            "id": c.id,
            "statut": c.statut,
            "lettre_motivation": c.lettre_motivation,
            "cv_url": c.cv_url,
            "annonce_id": c.annonce_id,
            "etudiant_id": c.etudiant_id,
            "created_at": c.created_at,
        }
        for c in candidatures
    ]


# ════════════════════════════════════════
# ROUTE 3 : CANDIDATURES REÇUES (RECRUTEUR)
# GET /api/v1/candidatures/recues
# ════════════════════════════════════════

@router.get(
    "/recues",
    response_model=List[CandidatureResponse]
)
async def candidatures_recues(
    current_user: Utilisateur = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # vérifie que c'est bien un recruteur
    if current_user.role != RoleUtilisateur.RECRUTEUR:
        raise HTTPException(
            status_code=403,
            detail="Réservé aux recruteurs"
        )

    # récupère les candidatures des annonces du recruteur
    result = await db.execute(
        select(Candidature).join(
            Annonce,
            Candidature.annonce_id == Annonce.id
        ).where(
            Annonce.recruteur_id == current_user.id
        ).order_by(Candidature.created_at.desc())
    )
    candidatures = result.scalars().all()

    # retourne les données sans les relations
    return [
        {
            "id": c.id,
            "statut": c.statut,
            "lettre_motivation": c.lettre_motivation,
            "cv_url": c.cv_url,
            "annonce_id": c.annonce_id,
            "etudiant_id": c.etudiant_id,
            "created_at": c.created_at,
        }
        for c in candidatures
    ]


# ════════════════════════════════════════
# ROUTE 4 : MODIFIER STATUT CANDIDATURE
# PUT /api/v1/candidatures/{candidature_id}
# ════════════════════════════════════════

@router.put(
    "/{candidature_id}",
    response_model=CandidatureResponse
)
async def modifier_candidature(
    candidature_id: int,
    data: CandidatureUpdate,
    current_user: Utilisateur = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # cherche la candidature
    result = await db.execute(
        select(Candidature).where(Candidature.id == candidature_id)
    )
    candidature = result.scalar_one_or_none()

    # si candidature inexistante → erreur 404
    if not candidature:
        raise HTTPException(
            status_code=404,
            detail="Candidature non trouvée"
        )

    # vérifie que c'est le recruteur de l'annonce
    result = await db.execute(
        select(Annonce).where(Annonce.id == candidature.annonce_id)
    )
    annonce = result.scalar_one_or_none()

    if annonce.recruteur_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Accès refusé"
        )

    # met à jour les champs envoyés
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(candidature, field, value)

    await db.flush()
    await db.refresh(candidature)

    return {
        "id": candidature.id,
        "statut": candidature.statut,
        "lettre_motivation": candidature.lettre_motivation,
        "cv_url": candidature.cv_url,
        "annonce_id": candidature.annonce_id,
        "etudiant_id": candidature.etudiant_id,
        "created_at": candidature.created_at,
    }