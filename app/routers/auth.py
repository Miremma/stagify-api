from fastapi import APIRouter, Depends, HTTPException  # outils FastAPI
from sqlalchemy.ext.asyncio import AsyncSession        # session base de données
from sqlalchemy import select                          # pour faire des requêtes
from app.database import get_db                        # fonction session BDD
from app.models import Utilisateur                     # modèle utilisateur
from app.schemas import (                              # schémas de validation
    UtilisateurCreate,    # schéma pour créer un compte
    UtilisateurResponse,  # schéma pour répondre avec un utilisateur
    LoginRequest,         # schéma pour se connecter
    TokenResponse         # schéma pour répondre avec un token
)
from app.auth import (                                 # fonctions de sécurité
    hash_password,         # pour hacher le mot de passe
    verify_password,       # pour vérifier le mot de passe
    create_access_token,   # pour créer le token JWT
    get_current_user       # pour récupérer l'utilisateur connecté
)

# crée le router — groupe de routes pour l'authentification
router = APIRouter()


# ════════════════════════════════════════
# ROUTE 1 : S'INSCRIRE
# POST /api/v1/auth/register
# ════════════════════════════════════════

@router.post(
    "/register",
    response_model=UtilisateurResponse,  # format de la réponse
    status_code=201                       # code 201 = créé avec succès
)
async def register(
    data: UtilisateurCreate,             # données reçues et validées par Pydantic
    db: AsyncSession = Depends(get_db)   # session BDD injectée automatiquement
):
    # vérifie si l'email existe déjà dans la base de données
    result = await db.execute(
        select(Utilisateur).where(
            Utilisateur.email == data.email  # cherche l'email
        )
    )
    if result.scalar_one_or_none():
        # si l'email existe déjà → erreur 400
        raise HTTPException(
            status_code=400,
            detail="Cet email est déjà utilisé"
        )

    # crée le nouvel utilisateur
    user = Utilisateur(
        email=data.email,                          # email
        nom=data.nom,                              # nom
        prenom=data.prenom,                        # prénom
        hashed_password=hash_password(data.password),  # mot de passe hashé
        role=data.role,                            # rôle (étudiant par défaut)
    )

    db.add(user)          # ajoute l'utilisateur à la session
    await db.flush()      # sauvegarde dans la base de données
    await db.refresh(user) # relit l'utilisateur depuis la BDD (pour avoir l'id)
    return user            # retourne l'utilisateur créé


# ════════════════════════════════════════
# ROUTE 2 : SE CONNECTER
# POST /api/v1/auth/login
# ════════════════════════════════════════

@router.post(
    "/login",
    response_model=TokenResponse  # format de la réponse
)
async def login(
    data: LoginRequest,              # données reçues (email + password)
    db: AsyncSession = Depends(get_db)  # session BDD injectée automatiquement
):
    # cherche l'utilisateur par email dans la base de données
    result = await db.execute(
        select(Utilisateur).where(
            Utilisateur.email == data.email  # cherche par email
        )
    )
    user = result.scalar_one_or_none()  # récupère l'utilisateur ou None

    # vérifie que l'utilisateur existe ET que le mot de passe est correct
    if not user or not verify_password(
        data.password,          # mot de passe tapé par l'utilisateur
        user.hashed_password    # mot de passe hashé dans la BDD
    ):
        # si email ou mot de passe incorrect → erreur 401
        raise HTTPException(
            status_code=401,
            detail="Email ou mot de passe incorrect"
        )

    # vérifie que le compte est actif
    if not user.est_actif:
        raise HTTPException(
            status_code=403,
            detail="Compte désactivé"
        )

    # crée le token JWT avec l'id de l'utilisateur
    token = create_access_token(
        {"sub": str(user.id)}  # "sub" = subject = id utilisateur
    )

    # retourne le token et les infos de l'utilisateur
    return TokenResponse(
        access_token=token,  # le token JWT
        utilisateur=user     # les infos de l'utilisateur
    )


# ════════════════════════════════════════
# ROUTE 3 : VOIR SON PROFIL
# GET /api/v1/auth/me
# ════════════════════════════════════════

@router.get(
    "/me",
    response_model=UtilisateurResponse  # format de la réponse
)
async def get_me(
    # récupère automatiquement l'utilisateur connecté via le token JWT
    current_user: Utilisateur = Depends(get_current_user)
):
    return current_user  # retourne le profil de l'utilisateur connecté