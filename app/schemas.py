from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from app.models import (
    TypeContrat, NiveauEtudes,
    StatutCandidature, RoleUtilisateur
)


class UtilisateurCreate(BaseModel):
    email: EmailStr
    nom: str
    prenom: str
    password: str = Field(min_length=8, max_length=72)
    role: RoleUtilisateur = RoleUtilisateur.ETUDIANT


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UtilisateurResponse(BaseModel):
    id: int
    email: EmailStr
    nom: str
    prenom: str
    role: RoleUtilisateur
    est_actif: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    utilisateur: UtilisateurResponse


class AnnonceCreate(BaseModel):
    titre: str = Field(min_length=5)
    description: str = Field(min_length=20)
    type_contrat: TypeContrat
    niveau_etudes: Optional[NiveauEtudes] = None
    duree: Optional[str] = None
    remuneration: Optional[float] = None
    ville: Optional[str] = None
    teletravail: bool = False
    competences: Optional[List[str]] = []
    entreprise_id: Optional[int] = None


class AnnonceUpdate(BaseModel):
    titre: Optional[str] = None
    description: Optional[str] = None
    ville: Optional[str] = None
    remuneration: Optional[float] = None
    est_active: Optional[bool] = None


class AnnonceResponse(BaseModel):
    id: int
    titre: str
    description: str
    type_contrat: TypeContrat
    niveau_etudes: Optional[NiveauEtudes] = None
    duree: Optional[str] = None
    remuneration: Optional[float] = None
    ville: Optional[str] = None
    teletravail: bool
    competences: Optional[List[str]] = None
    est_active: bool
    source_externe: Optional[str] = None
    url_externe: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class AnnonceListResponse(BaseModel):
    total: int
    page: int
    limit: int
    annonces: List[AnnonceResponse]


class CandidatureCreate(BaseModel):
    annonce_id: int
    lettre_motivation: Optional[str] = None
    cv_url: Optional[str] = None


class CandidatureUpdate(BaseModel):
    statut: Optional[StatutCandidature] = None
    note_recruteur: Optional[str] = None


class CandidatureResponse(BaseModel):
    id: int
    statut: StatutCandidature
    lettre_motivation: Optional[str] = None
    cv_url: Optional[str] = None
    annonce_id: int
    etudiant_id: int
    created_at: datetime
    model_config = {"from_attributes": True}