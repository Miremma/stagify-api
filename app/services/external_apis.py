import httpx
from app.config import settings


# ════════════════════════════════════════
# SERVICE FRANCE TRAVAIL
# ════════════════════════════════════════

class FranceTravailService:
    TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
    API_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"

    async def get_token(self) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": settings.FRANCE_TRAVAIL_CLIENT_ID,
                        "client_secret": settings.FRANCE_TRAVAIL_CLIENT_SECRET,
                        "scope": "api_offresdemploiv2 o2dsoffre"
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if response.status_code == 200:
                    return response.json().get("access_token", "")
                print(f"Erreur token FT : {response.status_code} — {response.text}")
                return ""
        except Exception as e:
            print(f"Erreur get_token FT : {e}")
            return ""

    async def rechercher(self, mots_cles=None, ville=None, type_contrat=None) -> list:
        try:
            token = await self.get_token()
            if not token:
                return []

            params = {"range": "0-9"}
            if mots_cles:
                params["motsCles"] = mots_cles
            if ville:
                params["commune"] = ville
            if type_contrat == "stage":
                params["typeContrat"] = "ST"
            elif type_contrat == "alternance":
                params["typeContrat"] = "E2"

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self.API_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    },
                    params=params
                )
                print(f"FT status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"FT keys: {list(data.keys())}")
                    # France Travail retourne les résultats dans "resultats"
                    resultats = data.get("resultats", [])
                    print(f"FT nb resultats: {len(resultats)}")
                    return [
                        {
                            "id": o.get("id", ""),
                            "titre": o.get("intitule", ""),
                            "description": o.get("description", ""),
                            "ville": o.get("lieuTravail", {}).get("libelle", ""),
                            "type_contrat": o.get("typeContratLibelle", ""),
                            "entreprise": o.get("entreprise", {}).get("nom", ""),
                            "source": "france_travail",
                            "url": o.get("origineOffre", {}).get("urlOrigine", "")
                        }
                        for o in resultats
                    ]
                elif response.status_code == 206:
                    # 206 = résultats partiels, aussi valide !
                    data = response.json()
                    resultats = data.get("resultats", [])
                    print(f"FT 206 nb resultats: {len(resultats)}")
                    return [
                        {
                            "id": o.get("id", ""),
                            "titre": o.get("intitule", ""),
                            "description": o.get("description", ""),
                            "ville": o.get("lieuTravail", {}).get("libelle", ""),
                            "type_contrat": o.get("typeContratLibelle", ""),
                            "entreprise": o.get("entreprise", {}).get("nom", ""),
                            "source": "france_travail",
                            "url": o.get("origineOffre", {}).get("urlOrigine", "")
                        }
                        for o in resultats
                    ]
                print(f"FT erreur: {response.status_code}")
                return []
        except Exception as e:
            print(f"Erreur France Travail : {e}")
            return []

# ════════════════════════════════════════
# SERVICE LA BONNE ALTERNANCE
# ════════════════════════════════════════

class LaBonneAlternanceService:
    # Nouvelle URL correcte de l'API
    API_URL = "https://labonnealternance.apprentissage.beta.gouv.fr/api/v1/jobs"

    async def rechercher(self, mots_cles=None, ville=None, type_contrat=None) -> list:
        try:
            # LBA = uniquement alternance, pas les stages
            if type_contrat == "stage":
                return []

            params = {
                "caller": "stagify",   # identifiant app obligatoire
                "romes": "M1805",      # code ROME informatique par défaut
                "longitude": "2.3488", # Paris par défaut
                "latitude": "48.8534",
                "radius": "60",        # rayon 60km
                "limit": "10",         # 10 résultats max
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self.API_URL,
                    params=params
                )
                print(f"LBA status: {response.status_code}")
                print(f"LBA response: {response.text[:500]}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"LBA data keys: {list(data.keys())}")

                    # essaie différentes clés possibles
                    resultats = (
                        data.get("jobs", []) or
                        data.get("results", []) or
                        data.get("data", []) or
                        []
                    )

                    return [
                        {
                            "id": str(o.get("id", "")),
                            "titre": o.get("title", o.get("label", "Offre alternance")),
                            "description": o.get("description", "Offre d'alternance disponible"),
                            "ville": o.get("place", {}).get("city", "") if isinstance(o.get("place"), dict) else "",
                            "type_contrat": "Alternance",
                            "entreprise": o.get("company", {}).get("name", "") if isinstance(o.get("company"), dict) else "",
                            "source": "la_bonne_alternance",
                            "url": o.get("url", "https://labonnealternance.apprentissage.beta.gouv.fr")
                        }
                        for o in resultats[:10]
                    ]
                return []
        except Exception as e:
            print(f"Erreur LBA : {e}")
            return []

# ════════════════════════════════════════
# SERVICE ADZUNA
# ════════════════════════════════════════

class AdzunaService:
    API_URL = "https://api.adzuna.com/v1/api/jobs/fr/search/1"

    async def rechercher(self, mots_cles=None, ville=None, type_contrat=None) -> list:
        try:
            if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
                return []

            # adapte les mots clés selon le type
            what = mots_cles or ""
            if type_contrat == "stage":
                what = f"stage {mots_cles}" if mots_cles else "stage"
            elif type_contrat == "alternance":
                what = f"alternance {mots_cles}" if mots_cles else "alternance apprentissage"

            params = {
                "app_id": settings.ADZUNA_APP_ID,
                "app_key": settings.ADZUNA_APP_KEY,
                "results_per_page": 10,
                "content-type": "application/json",
                "what": what,
            }
            if ville:
                params["where"] = ville

            async with httpx.AsyncClient() as client:
                response = await client.get(self.API_URL, params=params)
                if response.status_code == 200:
                    resultats = response.json().get("results", [])
                    return [
                        {
                            "id": o.get("id"),
                            "titre": o.get("title", ""),
                            "description": o.get("description", ""),
                            "ville": o.get("location", {}).get("display_name", ""),
                            "type_contrat": o.get("contract_type", ""),
                            "entreprise": o.get("company", {}).get("display_name", ""),
                            "remuneration": o.get("salary_min"),
                            "source": "adzuna",
                            "url": o.get("redirect_url", "")
                        }
                        for o in resultats
                    ]
                return []
        except Exception as e:
            print(f"Erreur Adzuna : {e}")
            return []


# ════════════════════════════════════════
# INSTANCES GLOBALES
# ════════════════════════════════════════

france_travail_service = FranceTravailService()
lba_service = LaBonneAlternanceService()
adzuna_service = AdzunaService()