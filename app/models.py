import enum  # pour créer des listes de valeurs fixes
from sqlalchemy import (
    Column, Integer, String, Text,   # types de colonnes
    Boolean, Float, DateTime, Enum,  # autres types
    ForeignKey, JSON                 # clé étrangère et JSON
)
from sqlalchemy.orm import relationship  # pour lier les tables entre elles
from sqlalchemy.sql import func          # pour la date automatique
from app.database import Base            # classe mère de tous les modèles


# ════════════════════════════════════════
# LES TYPES FIXES (valeurs autorisées)
# ════════════════════════════════════════

class RoleUtilisateur(str, enum.Enum):
    ETUDIANT  = "etudiant"   # peut postuler aux annonces
    RECRUTEUR = "recruteur"  # peut publier des annonces
    ADMIN     = "admin"      # accès total

class TypeContrat(str, enum.Enum):
    STAGE         = "stage"         # stage classique
    ALTERNANCE    = "alternance"    # contrat alternance
    APPRENTISSAGE = "apprentissage" # contrat apprentissage

class NiveauEtudes(str, enum.Enum):
    BAC  = "bac"    # niveau baccalauréat
    BAC2 = "bac+2"  # BTS, DUT
    BAC3 = "bac+3"  # licence
    BAC5 = "bac+5"  # master

class StatutCandidature(str, enum.Enum):
    EN_ATTENTE = "en_attente" # candidature envoyée
    VU         = "vu"         # recruteur a vu
    ENTRETIEN  = "entretien"  # entretien proposé
    ACCEPTE    = "accepte"    # candidature acceptée
    REFUSE     = "refuse"     # candidature refusée


# ════════════════════════════════════════
# TABLE 1 : utilisateurs
# ════════════════════════════════════════

class Utilisateur(Base):
    __tablename__ = "utilisateurs"  # nom de la table dans MySQL

    # colonnes de la table
    id              = Column(Integer, primary_key=True, index=True)  # identifiant unique auto
    email           = Column(String(255), unique=True, nullable=False)  # email unique obligatoire
    nom             = Column(String(100), nullable=False)  # nom obligatoire
    prenom          = Column(String(100), nullable=False)  # prénom obligatoire
    hashed_password = Column(String(255), nullable=False)  # mot de passe hashé (jamais en clair)
    role            = Column(Enum(RoleUtilisateur), default=RoleUtilisateur.ETUDIANT)  # rôle par défaut
    est_actif       = Column(Boolean, default=True)  # compte actif par défaut
    created_at      = Column(DateTime(timezone=True), server_default=func.now())  # date création auto
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())  # date modification auto

    # relations avec les autres tables
    annonces     = relationship("Annonce",     back_populates="recruteur")  # annonces publiées
    candidatures = relationship("Candidature", back_populates="etudiant")   # candidatures envoyées


# ════════════════════════════════════════
# TABLE 2 : entreprises
# ════════════════════════════════════════

class Entreprise(Base):
    __tablename__ = "entreprises"  # nom de la table dans MySQL

    # colonnes de la table
    id          = Column(Integer, primary_key=True, index=True)  # identifiant unique auto
    nom         = Column(String(255), nullable=False)  # nom de l'entreprise obligatoire
    secteur     = Column(String(100))   # secteur d'activité optionnel
    description = Column(Text)          # description optionnelle
    site_web    = Column(String(255))   # site web optionnel
    logo_url    = Column(String(500))   # lien vers le logo optionnel
    ville       = Column(String(100))   # ville optionnelle
    code_postal = Column(String(10))    # code postal optionnel
    created_at  = Column(DateTime(timezone=True), server_default=func.now())  # date création auto

    # relation avec les annonces
    annonces = relationship("Annonce", back_populates="entreprise")  # annonces de cette entreprise


# ════════════════════════════════════════
# TABLE 3 : annonces
# ════════════════════════════════════════

class Annonce(Base):
    __tablename__ = "annonces"  # nom de la table dans MySQL

    # colonnes de la table
    id            = Column(Integer, primary_key=True, index=True)  # identifiant unique auto
    titre         = Column(String(255), nullable=False)  # titre obligatoire
    description   = Column(Text, nullable=False)         # description obligatoire
    type_contrat  = Column(Enum(TypeContrat), nullable=False)  # stage/alternance obligatoire
    niveau_etudes = Column(Enum(NiveauEtudes))  # niveau requis optionnel
    duree         = Column(String(50))   # durée ex: "6 mois" optionnel
    remuneration  = Column(Float)        # salaire en euros optionnel
    ville         = Column(String(100))  # ville optionnelle
    code_postal   = Column(String(10))   # code postal optionnel
    teletravail   = Column(Boolean, default=False)  # télétravail possible ou non
    competences   = Column(JSON)         # liste de compétences ex: ["Python","SQL"]
    date_debut    = Column(DateTime(timezone=True))   # date de début optionnelle
    date_limite   = Column(DateTime(timezone=True))   # date limite candidature
    est_active    = Column(Boolean, default=True)     # annonce visible ou non

    # colonnes pour les annonces venant des APIs externes
    source_externe = Column(String(50))   # ex: "france_travail" ou "adzuna"
    id_externe     = Column(String(100))  # identifiant sur le site externe
    url_externe    = Column(String(500))  # lien vers l'annonce originale

    # clés étrangères (liens vers d'autres tables)
    recruteur_id  = Column(Integer, ForeignKey("utilisateurs.id"))  # qui a publié
    entreprise_id = Column(Integer, ForeignKey("entreprises.id"))   # quelle entreprise

    # dates automatiques
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # date création
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())        # date modification

    # relations avec les autres tables
    recruteur    = relationship("Utilisateur", back_populates="annonces")    # le recruteur
    entreprise   = relationship("Entreprise",  back_populates="annonces")    # l'entreprise
    candidatures = relationship("Candidature", back_populates="annonce")     # les candidatures


# ════════════════════════════════════════
# TABLE 4 : candidatures
# ════════════════════════════════════════

class Candidature(Base):
    __tablename__ = "candidatures"  # nom de la table dans MySQL

    # colonnes de la table
    id                = Column(Integer, primary_key=True, index=True)  # identifiant unique auto
    lettre_motivation = Column(Text)          # lettre de motivation optionnelle
    cv_url            = Column(String(500))   # lien vers le CV optionnel
    statut            = Column(Enum(StatutCandidature), default=StatutCandidature.EN_ATTENTE)  # statut par défaut
    note_recruteur    = Column(Text)          # note privée du recruteur optionnelle

    # clés étrangères (liens vers d'autres tables)
    etudiant_id = Column(Integer, ForeignKey("utilisateurs.id"), nullable=False)  # qui postule
    annonce_id  = Column(Integer, ForeignKey("annonces.id"),     nullable=False)  # à quelle annonce

    # dates automatiques
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # date candidature
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())        # date modification

    # relations avec les autres tables
    etudiant = relationship("Utilisateur", back_populates="candidatures")  # l'étudiant
    annonce  = relationship("Annonce",     back_populates="candidatures")  # l'annonce