from datetime import datetime, timedelta    # pour calculer l'expiration du token
from jose import JWTError, jwt             # pour créer et vérifier les tokens JWT
from passlib.context import CryptContext   # pour hacher les mots de passe
from fastapi import Depends, HTTPException, status  # outils FastAPI
from fastapi.security import OAuth2PasswordBearer   # pour lire le token dans les requêtes
from sqlalchemy.ext.asyncio import AsyncSession     # session base de données
from sqlalchemy import select              # pour faire des requêtes SQL
from app.config import settings            # nos variables .env
from app.database import get_db            # fonction qui donne la session BDD
from app.models import Utilisateur         # le modèle utilisateur


# ── Outil pour hacher les mots de passe avec bcrypt ──
pwd_context = CryptContext(
    schemes=["bcrypt"],   # algorithme de hachage
    deprecated="auto"     # gère automatiquement les anciennes versions
)

# ── Outil pour lire le token JWT dans les requêtes ──
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"  # URL de connexion
)


# ════════════════════════════════════════
# FONCTIONS DE SÉCURITÉ
# ════════════════════════════════════════

def hash_password(password: str) -> str:
    # transforme "monmdp123" en "$2b$12$xyz..." (irréversible)
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    # vérifie que le mot de passe correspond au hash
    # retourne True si correct, False sinon
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    # crée un token JWT signé qui expire dans 24h
    to_encode = data.copy()  # copie les données à encoder

    # calcule la date d'expiration
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES  # 1440 minutes = 24h
    )

    # ajoute l'expiration aux données
    to_encode.update({"exp": expire})

    # crée et retourne le token signé
    return jwt.encode(
        to_encode,           # données à encoder (id utilisateur + expiration)
        settings.SECRET_KEY, # clé secrète pour signer
        algorithm=settings.ALGORITHM  # algorithme HS256
    )


# ════════════════════════════════════════
# FONCTIONS DE VÉRIFICATION
# ════════════════════════════════════════

async def get_current_user(
    token: str = Depends(oauth2_scheme),  # lit le token dans le header
    db: AsyncSession = Depends(get_db)    # ouvre une session BDD
) -> Utilisateur:
    # vérifie le token JWT et retourne l'utilisateur connecté

    # erreur à retourner si le token est invalide
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,  # erreur 401
        detail="Token invalide ou expiré",          # message d'erreur
        headers={"WWW-Authenticate": "Bearer"},     # header de sécurité
    )

    try:
        # décode le token avec la clé secrète
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        # récupère l'id utilisateur depuis le token
        user_id: int = payload.get("sub")

        # si pas d'id dans le token → erreur
        if user_id is None:
            raise error

    except JWTError:
        # si le token est invalide ou expiré → erreur
        raise error

    # cherche l'utilisateur dans la base de données
    result = await db.execute(
        select(Utilisateur).where(
            Utilisateur.id == int(user_id)  # cherche par id
        )
    )
    user = result.scalar_one_or_none()  # récupère l'utilisateur ou None

    # si utilisateur introuvable ou compte désactivé → erreur
    if user is None or not user.est_actif:
        raise error

    return user  # retourne l'utilisateur connecté


async def get_current_recruteur(
    user: Utilisateur = Depends(get_current_user)  # vérifie d'abord la connexion
) -> Utilisateur:
    # vérifie que l'utilisateur connecté est bien un recruteur ou admin
    from app.models import RoleUtilisateur

    # si l'utilisateur n'est pas recruteur ni admin → erreur 403
    if user.role not in [RoleUtilisateur.RECRUTEUR, RoleUtilisateur.ADMIN]:
        raise HTTPException(
            status_code=403,                      # erreur 403 = accès interdit
            detail="Réservé aux recruteurs"       # message d'erreur
        )
    return user  # retourne le recruteur confirmé