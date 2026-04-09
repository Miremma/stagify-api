from sqlalchemy.ext.asyncio import (
    AsyncSession,           # type de session asynchrone
    create_async_engine,    # crée la connexion à MySQL
    async_sessionmaker      # fabrique de sessions
)
from sqlalchemy.orm import DeclarativeBase  # classe de base pour les modèles
from app.config import settings             # importe nos variables .env

# ── Construire l'URL de connexion à MySQL ──
DATABASE_URL = (
    f"mysql+asyncmy://"           # driver MySQL async
    f"{settings.DB_USER}:"        # utilisateur : stagify_user
    f"{settings.DB_PASSWORD}@"    # mot de passe : Stagify123!
    f"{settings.DB_HOST}:"        # hôte : localhost
    f"{settings.DB_PORT}/"        # port : 3306
    f"{settings.DB_NAME}"         # base : stagify_db
)

# ── Créer le moteur de connexion ──
engine = create_async_engine(
    DATABASE_URL,        # l'URL qu'on vient de construire
    echo=settings.DEBUG, # si DEBUG=True, affiche les requêtes SQL
    pool_pre_ping=True,  # vérifie que la connexion est active
)

# ── Fabrique de sessions ──
AsyncSessionLocal = async_sessionmaker(
    bind=engine,              # utilise notre moteur
    class_=AsyncSession,      # type de session
    expire_on_commit=False,   # garde les données après commit
)

# ── Classe de base pour tous les modèles (tables) ──
class Base(DeclarativeBase):
    pass  # vide, mais SQLAlchemy en a besoin

# ── Fonction qui fournit une session à chaque requête ──
async def get_db() -> AsyncSession:
    # ouvre une session
    async with AsyncSessionLocal() as session:
        try:
            yield session            # donne la session à la route
            await session.commit()   # sauvegarde si tout va bien
        except Exception:
            await session.rollback() # annule si erreur
            raise                    # remonte l'erreur