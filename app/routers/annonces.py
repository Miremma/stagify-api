from fastapi import APIRouter, Depends, HTTPException, Query  # outils FastAPI
from sqlalchemy.ext.asyncio import AsyncSession               # session BDD
from sqlalchemy import select, func                           # requêtes SQL
from sqlalchemy.orm import selectinload                       # pour charger les relations
from typing import Optional                                   # pour les paramètres optionnels
from app.database import get_db                               # fonction session BDD
from app.models import Annonce, TypeContrat, Utilisateur      # modèles
from app.schemas import (                                     # schémas de validation
    AnnonceCreate,       # schéma pour créer une annonce
    AnnonceUpdate,       # schéma pour modifier une annonce
    AnnonceResponse,     # schéma pour répondre avec une annonce
    AnnonceListResponse  # schéma pour répondre avec une liste
)
from app.auth import (                    # fonctions de sécurité
    get_current_user,       # vérifie que l'utilisateur est connecté
    get_current_recruteur   # vérifie que l'utilisateur est recruteur
)

# crée le router — groupe de routes pour les annonces
router = APIRouter()


# ════════════════════════════════════════
# ROUTE 1 : LISTER LES ANNONCES
# GET /api/v1/annonces/
# ════════════════════════════════════════

@router.get(
    "/",
    response_model=AnnonceListResponse  # format de la réponse
)
async def lister_annonces(
    # paramètres de filtrage optionnels dans l'URL
    type_contrat: Optional[TypeContrat] = None,  # filtrer par type de contrat
    ville: Optional[str] = None,                  # filtrer par ville
    mots_cles: Optional[str] = None,              # rechercher par mots clés
    page: int = Query(1, ge=1),                   # numéro de page (minimum 1)
    limit: int = Query(20, ge=1, le=100),         # nombre par page (max 100)
    db: AsyncSession = Depends(get_db)            # session BDD
):
    # construit la requête de base — uniquement les annonces actives
    query = select(Annonce).where(Annonce.est_active == True)

    # ajoute les filtres si renseignés
    if type_contrat:
        # filtre par type de contrat (stage ou alternance)
        query = query.where(Annonce.type_contrat == type_contrat)

    if ville:
        # filtre par ville (recherche partielle, insensible à la casse)
        query = query.where(Annonce.ville.ilike(f"%{ville}%"))

    if mots_cles:
        # recherche dans le titre (insensible à la casse)
        query = query.where(Annonce.titre.ilike(f"%{mots_cles}%"))

    # compte le nombre total d'annonces (pour la pagination)
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()  # récupère le nombre total

    # applique la pagination et trie par date (plus récent en premier)
    query = query.offset(
        (page - 1) * limit  # calcule le décalage selon la page
    ).limit(limit).order_by(
        Annonce.created_at.desc()  # trie du plus récent au plus ancien
    )

    # exécute la requête
    result = await db.execute(query)
    annonces = result.scalars().all()  # récupère toutes les annonces

    # retourne la liste avec les infos de pagination
    return AnnonceListResponse(
        total=total,       # nombre total d'annonces
        page=page,         # page actuelle
        limit=limit,       # nombre par page
        annonces=annonces  # liste des annonces
    )


# ════════════════════════════════════════
# ROUTE 2 : VOIR UNE ANNONCE
# GET /api/v1/annonces/{annonce_id}
# ════════════════════════════════════════

@router.get(
    "/{annonce_id}",
    response_model=AnnonceResponse  # format de la réponse
)
async def get_annonce(
    annonce_id: int,                    # id de l'annonce dans l'URL
    db: AsyncSession = Depends(get_db)  # session BDD
):
    # cherche l'annonce par son id
    result = await db.execute(
        select(Annonce).where(Annonce.id == annonce_id)
    )
    annonce = result.scalar_one_or_none()  # récupère l'annonce ou None

    # si l'annonce n'existe pas → erreur 404
    if not annonce:
        raise HTTPException(
            status_code=404,
            detail="Annonce non trouvée"
        )

    return annonce  # retourne l'annonce


# ════════════════════════════════════════
# ROUTE 3 : CRÉER UNE ANNONCE
# POST /api/v1/annonces/
# ════════════════════════════════════════

@router.post(
    "/",
    response_model=AnnonceResponse,  # format de la réponse
    status_code=201                   # code 201 = créé avec succès
)
async def creer_annonce(
    data: AnnonceCreate,             # données reçues et validées par Pydantic
    current_user: Utilisateur = Depends(get_current_recruteur),  # recruteur uniquement
    db: AsyncSession = Depends(get_db)  # session BDD
):
    # crée l'annonce avec les données reçues
    annonce = Annonce(
        **data.model_dump(),          # décompresse toutes les données du schéma
        recruteur_id=current_user.id  # ajoute l'id du recruteur connecté
    )

    db.add(annonce)           # ajoute l'annonce à la session
    await db.flush()           # sauvegarde dans la BDD
    await db.refresh(annonce)  # relit depuis la BDD pour avoir l'id
    return annonce             # retourne l'annonce créée


# ════════════════════════════════════════
# ROUTE 4 : MODIFIER UNE ANNONCE
# PUT /api/v1/annonces/{annonce_id}
# ════════════════════════════════════════

@router.put(
    "/{annonce_id}",
    response_model=AnnonceResponse  # format de la réponse
)
async def modifier_annonce(
    annonce_id: int,                 # id de l'annonce dans l'URL
    data: AnnonceUpdate,             # données à modifier
    current_user: Utilisateur = Depends(get_current_recruteur),  # recruteur uniquement
    db: AsyncSession = Depends(get_db)  # session BDD
):
    # cherche l'annonce par son id
    result = await db.execute(
        select(Annonce).where(Annonce.id == annonce_id)
    )
    annonce = result.scalar_one_or_none()

    # si l'annonce n'existe pas → erreur 404
    if not annonce:
        raise HTTPException(
            status_code=404,
            detail="Annonce non trouvée"
        )

    # vérifie que le recruteur est bien le propriétaire de l'annonce
    if annonce.recruteur_id != current_user.id:
        raise HTTPException(
            status_code=403,  # erreur 403 = accès interdit
            detail="Vous ne pouvez pas modifier cette annonce"
        )

    # met à jour seulement les champs envoyés
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(annonce, field, value)  # modifie chaque champ

    await db.flush()           # sauvegarde dans la BDD
    await db.refresh(annonce)  # relit depuis la BDD
    return annonce             # retourne l'annonce modifiée


# ════════════════════════════════════════
# ROUTE 5 : SUPPRIMER UNE ANNONCE
# DELETE /api/v1/annonces/{annonce_id}
# ════════════════════════════════════════

@router.delete(
    "/{annonce_id}",
    status_code=204  # code 204 = supprimé avec succès (pas de contenu)
)
async def supprimer_annonce(
    annonce_id: int,                 # id de l'annonce dans l'URL
    current_user: Utilisateur = Depends(get_current_recruteur),  # recruteur uniquement
    db: AsyncSession = Depends(get_db)  # session BDD
):
    # cherche l'annonce par son id
    result = await db.execute(
        select(Annonce).where(Annonce.id == annonce_id)
    )
    annonce = result.scalar_one_or_none()

    # si l'annonce n'existe pas → erreur 404
    if not annonce:
        raise HTTPException(
            status_code=404,
            detail="Annonce non trouvée"
        )

    # vérifie que le recruteur est bien le propriétaire
    if annonce.recruteur_id != current_user.id:
        raise HTTPException(
            status_code=403,  # erreur 403 = accès interdit
            detail="Vous ne pouvez pas supprimer cette annonce"
        )

    # soft delete = on désactive l'annonce sans la supprimer de la BDD
    annonce.est_active = False  # l'annonce disparaît de la liste
    await db.flush()            # sauvegarde dans la BDD