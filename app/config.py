from pydantic_settings import BaseSettings  # importe l'outil qui lit le .env

class Settings(BaseSettings):
    # ── Paramètres de la base de données MySQL ──
    DB_HOST: str = "localhost"       # adresse du serveur MySQL
    DB_PORT: int = 3306              # port MySQL (toujours 3306)
    DB_USER: str = "stagify_user"    # utilisateur MySQL qu'on a créé
    DB_PASSWORD: str = ""            # mot de passe MySQL
    DB_NAME: str = "stagify_db"      # nom de la base de données

    # ── Paramètres de sécurité JWT ──
    SECRET_KEY: str = ""             # clé secrète pour signer les tokens
    ALGORITHM: str = "HS256"         # algorithme de chiffrement
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # durée du token = 24h

    # ── Paramètres des APIs externes ──
    FRANCE_TRAVAIL_CLIENT_ID: str = ""      # clé France Travail
    FRANCE_TRAVAIL_CLIENT_SECRET: str = ""  # secret France Travail
    ADZUNA_APP_ID: str = ""                 # clé Adzuna
    ADZUNA_APP_KEY: str = ""                # secret Adzuna

    # ── Mode debug ──
    DEBUG: bool = False  # False = mode production

    class Config:
        env_file = ".env"  # dit à pydantic de lire le fichier .env

# Crée une instance globale accessible partout dans le projet
settings = Settings()