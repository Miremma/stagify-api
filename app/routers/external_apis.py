from fastapi import APIRouter, Query
from typing import Optional
import asyncio
from app.services.external_apis import (
    france_travail_service,  # service France Travail
    lba_service,             # service La Bonne Alternance
    adzuna_service           # service Adzuna
)

router = APIRouter()


# ════════════════════════════════════════
# ROUTE 1 : FRANCE TRAVAIL
# ════════════════════════════════════════

@router.get("/france-travail")
async def recherche_france_travail(
    mots_cles: Optional[str] = Query(None),
    ville: Optional[str] = Query(None),
    type_contrat: Optional[str] = Query(None)
):
    resultats = await france_travail_service.rechercher(
        mots_cles=mots_cles,
        ville=ville,
        type_contrat=type_contrat
    )
    return {
        "source": "France Travail",
        "total": len(resultats),
        "resultats": resultats
    }


# ════════════════════════════════════════
# ROUTE 2 : LA BONNE ALTERNANCE
# ════════════════════════════════════════

@router.get("/la-bonne-alternance")
async def recherche_lba(
    mots_cles: Optional[str] = Query(None),
    ville: Optional[str] = Query(None),
    type_contrat: Optional[str] = Query(None)
):
    resultats = await lba_service.rechercher(
        mots_cles=mots_cles,
        ville=ville,
        type_contrat=type_contrat
    )
    return {
        "source": "La Bonne Alternance",
        "total": len(resultats),
        "resultats": resultats
    }


# ════════════════════════════════════════
# ROUTE 3 : ADZUNA
# ════════════════════════════════════════

@router.get("/adzuna")
async def recherche_adzuna(
    mots_cles: Optional[str] = Query(None),
    ville: Optional[str] = Query(None),
    type_contrat: Optional[str] = Query(None)
):
    resultats = await adzuna_service.rechercher(
        mots_cles=mots_cles,
        ville=ville,
        type_contrat=type_contrat
    )
    return {
        "source": "Adzuna",
        "total": len(resultats),
        "resultats": resultats
    }


# ════════════════════════════════════════
# ROUTE 4 : TOUTES LES SOURCES
# ════════════════════════════════════════

@router.get("/toutes-sources")
async def toutes_sources(
    mots_cles: Optional[str] = Query(None),
    ville: Optional[str] = Query(None),
    type_contrat: Optional[str] = Query(None)
):
    # lance les 3 recherches EN PARALLÈLE
    ft, lba, adzuna = await asyncio.gather(
        france_travail_service.rechercher(
            mots_cles=mots_cles, ville=ville, type_contrat=type_contrat
        ),
        lba_service.rechercher(
            mots_cles=mots_cles, ville=ville, type_contrat=type_contrat
        ),
        adzuna_service.rechercher(
            mots_cles=mots_cles, ville=ville, type_contrat=type_contrat
        ),
        return_exceptions=True  # ne plante pas si une source échoue
    )

    # si une source a planté → liste vide
    if isinstance(ft, Exception):
        ft = []
    if isinstance(lba, Exception):
        lba = []
    if isinstance(adzuna, Exception):
        adzuna = []

    # combine tous les résultats
    tous = ft + lba + adzuna

    return {
        "total": len(tous),
        "france_travail": len(ft),
        "la_bonne_alternance": len(lba),
        "adzuna": len(adzuna),
        "resultats": tous
    }