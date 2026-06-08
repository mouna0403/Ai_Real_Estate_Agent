import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from Ai_Real_Estate_Agent.utils.predictor import predict_price
from Ai_Real_Estate_Agent.utils.osm import *

# =========================
# 1. API KEY
# =========================
load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# =========================
# 2. MODEL
# =========================

model = ChatGroq(
    model="llama-3.3-70b-versatile", #"llama-3.1-8b-instant", 
    temperature=0.3,
    max_tokens=512
)
# ─────────────────────────────────────────────
# HELPER TRUNCATION
# ─────────────────────────────────────────────

def truncate_output(data, max_items: int = 5):
    """Tronque les listes pour ne pas exploser le contexte LLM."""
    if isinstance(data, list):
        return data[:max_items]
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if isinstance(v, list) and len(v) > max_items:
                result[k] = v[:max_items]
                result[f"{k}_total"] = len(v)
            else:
                result[k] = v
        return result
    return data

# ─────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────

@tool
def tool_get_insee_code(city: str) -> list:
    """
    Convertit un nom de ville en code(s) INSEE officiel(s).
    Input: nom de ville (ex: 'Lille') ou code postal (ex: '59000').
    Retourne une liste de dicts avec pour chaque commune trouvée:
      - city: nom de la commune
      - insee_code: code INSEE sur 5 chiffres
      - postal_codes: liste des codes postaux associés
    Retourne None si aucune commune trouvée.
    TOUJOURS utiliser ce tool en premier quand l'utilisateur donne un nom de ville avant d'appeler les autres tools qui nécessitent un code INSEE.
    Exemple: city='Lille'
    """
    result = get_insee_code(city)
    return truncate_output(result) if result else None


@tool
def tool_osm_location(lat: float, lon: float, radius: int = 1000) -> dict:
    """
    Analyse les points d'intérêt autour d'une coordonnée GPS via OpenStreetMap.
    Input: latitude, longitude, rayon en mètres (défaut 1000m).
    Retourne:
      - input: les paramètres utilisés {lat, lon, radius}
      - features: liste des POI parsés autour du point (commerces, services, loisirs...)
      - location_score: score calculé de la qualité de localisation
    Utiliser quand on veut analyser un point géographique précis par ses coordonnées.
    Exemple: lat=50.6292, lon=3.0573, radius=500 pour analyser le centre de Lille
    """
    return truncate_output(osm_location_tool(lat, lon, radius))


@tool
def tool_get_department_activities(dept_code: str) -> list:
    """
    Récupère toutes les activités et points d'intérêt d'un département français.
    Input: code département sur 2 chiffres (ex: '59' pour le Nord, '75' pour Paris).
    Retourne une liste de dicts contenant pour chaque activité:
      - type: catégorie de l'activité (restaurant, école, hôpital, commerce...)
      - lat: latitude
      - lon: longitude
      - name: nom de l'établissement
    Retourne None si le département est introuvable.
    Exemple: dept_code='59' pour toutes les activités du Nord
    """
    result = get_department_activities(dept_code)
    return truncate_output(result) if result else None


@tool
def tool_get_commune_activities(insee_code: str) -> dict:
    """
    Récupère toutes les activités et points d'intérêt d'une commune française.
    Input: code INSEE de la commune sur 5 chiffres.
    Retourne un dict avec les activités:
      - type: catégorie de l'activité
      - name: nom de l'établissement
      - lat / lon: coordonnées GPS
    Plus précis que tool_get_department_activities car limité à une seule commune.
    Exemple: insee_code='59350' pour les activités de Lille
    """
    return truncate_output(get_commune_activities(insee_code))


@tool
def tool_get_transport_stops(lat: float, lon: float, radius: int = 1000) -> dict:
    """
    Récupère les arrêts de transport en commun autour d'un point GPS.
    Input: latitude, longitude, rayon en mètres (défaut 1000m).
    Retourne:
      - counts: comptage par type {bus_stop, metro, rail_station}
      - stops: liste des arrêts avec:
          * name: nom de l'arrêt
          * type: bus_stop / metro / rail_station
          * line: ligne desservant l'arrêt
          * lat / lon: coordonnées GPS
          * distance: distance formatée depuis le point central
    Utiliser quand on a des coordonnées GPS précises.
    Exemple: lat=50.6292, lon=3.0573, radius=800
    """
    return truncate_output(get_transport_stops(lat, lon, radius))


@tool
def tool_get_commune_transport(insee_code: str) -> dict:
    """
    Récupère tous les arrêts de transport en commun d'une commune via son code INSEE.
    Input: code INSEE sur 5 chiffres.
    Retourne:
      - insee_code: le code INSEE utilisé
      - counts: comptage par type {bus_stop, metro, rail_station, tram}
      - stops: liste des arrêts avec name, type, lat, lon
    Couvre toute la commune (pas un rayon autour d'un point), inclut les trams.
    Exemple: insee_code='59350' pour tous les transports de Lille
    """
    return truncate_output(get_commune_transport(insee_code))

@tool
def tool_get_commune_centroid(insee_code: str) -> dict:
    """Retourne les coordonnées GPS du centre géographique d'une commune. Input: INSEE 5 chiffres. Retourne {insee, lat, lon, name}. Utiliser avant tool_predict_price quand l'utilisateur donne une commune (pas une adresse précise)."""
    from Ai_Real_Estate_Agent.utils.osm import get_commune_centroid
    result = get_commune_centroid(insee_code)
    return result if result else {"error": "Commune introuvable"}

@tool
def tool_get_green_spaces(lat: float, lon: float, radius: int = 1000) -> dict:
    """
    Récupère les espaces verts autour d'un point GPS dans un rayon donné.
    Input: latitude, longitude, rayon en mètres (défaut 1000m).
    Retourne:
      - count: nombre total d'espaces verts trouvés
      - greens: liste des espaces verts avec leurs détails (nom, type, coordonnées)
    Utiliser quand on a des coordonnées précises.
    Exemple: lat=50.6292, lon=3.0573, radius=500
    """
    return truncate_output(get_green_spaces(lat, lon, radius))


@tool
def tool_get_commune_greenspaces(insee_code: str) -> dict:
    """
    Récupère tous les espaces verts d'une commune via son code INSEE.
    Input: code INSEE sur 5 chiffres.
    Retourne:
      - insee_code: le code INSEE utilisé
      - counts: comptage par catégorie {park, garden, nature_reserve, forest,
                grass, meadow, wood, scrub, heath}
      - greenspaces: liste avec name, type, lat, lon, osm_id pour chaque espace
    Couvre toute la commune, détaille par catégorie d'espace vert.
    Exemple: insee_code='59350' pour tous les espaces verts de Lille
    """
    return get_commune_greenspaces(insee_code)


@tool
def tool_get_commune_demographics(insee_code: str) -> dict:
    """
    Récupère les données démographiques d'une commune via son code INSEE.
    Input: code INSEE sur 5 chiffres.
    Retourne:
      - insee: code INSEE de la commune
      - name: nom de la commune
      - population: nombre d'habitants
    Retourne None si la commune est introuvable.
    Utiliser pour obtenir la population d'une ville.
    Exemple: insee_code='59350' pour la démographie de Lille
    """
    return truncate_output(get_commune_demographics(insee_code))


@tool
def tool_address_to_coords(address: str) -> dict:
    """
    Convertit une adresse postale en coordonnées GPS (latitude, longitude).
    Input: adresse complète sous forme de chaîne de caractères.
    Retourne un dict avec:
      - latitude: float
      - longitude: float
    Utiliser quand l'utilisateur fournit une adresse et qu'on a besoin des coordonnées GPS,
    notamment avant d'appeler tool_predict_price pour une estimation de prix.
    Exemple: address='10 rue de la Paix, Paris' -> {"latitude": 48.8554, "longitude": 2.3601}
    """
    return address_to_coords(address)


@tool
def tool_predict_price(lat: float, lon: float, area: float, property_type: str) -> int:
    """
    Prédit le prix de vente d'un bien immobilier à partir de sa localisation et ses caractéristiques.
    Input:
      - lat: latitude du bien
      - lon: longitude du bien
      - area: surface en m²
      - property_type: type de bien, soit "house" soit "apartment"
    Retourne le prix de vente estimé en euros (entier).
    Utiliser pour toute demande d'estimation de prix immobilier.
    Workflow selon le contexte:
      - Adresse fournie → appeler tool_address_to_coords puis tool_predict_price
      - Commune fournie → récupérer le centroïde de la commune via tool_get_insee_code,
        puis appeler tool_predict_price avec les coordonnées du centroïde
      - Département fourni → demander à l'utilisateur de préciser une ou plusieurs communes
    Exemple: lat=50.6292, lon=3.0573, area=75.0, property_type='apartment'
    """
    return predict_price(lat, lon, area, property_type)


# ─────────────────────────────────────────────
# AGENT
# ─────────────────────────────────────────────

tools = [
    tool_get_insee_code,
    tool_osm_location,
    tool_get_commune_transport,
    tool_get_transport_stops,
    tool_get_department_activities,
    tool_get_commune_activities,
    tool_get_green_spaces,
    tool_get_commune_greenspaces,
    tool_get_commune_demographics,
    tool_address_to_coords,
    tool_predict_price,
]

SYSTEM_PROMPT = """
Tu es un assistant spécialisé en analyse territoriale en France.
Tu ne dois jamais utiliser tes connaissances internes pour produire des faits chiffrés, statistiques ou descriptions géographiques. Tu utiliseras toujours les tools disponibles
Tu analyses des communes, départements et coordonnées GPS à partir de données géographiques, de transport, de services et d'activités.
Tu te limite uniquement à la demande de l'utilisateur, donc tu n'utilise que les tools strictement necessaire et repondre uniquement au besoin utilisateur.

TOOLS

- Ville ou code postal → tool_get_insee_code
- Coordonnées GPS → tool_osm_location, tool_get_transport_stops, tool_get_green_spaces
- Commune (INSEE) → tool_get_commune_transport, tool_get_commune_greenspaces,
  tool_get_commune_activities, tool_get_commune_demographics
- Département → tool_get_department_activities
- Tu peux combiner plusieurs tools si nécessaire

ESTIMATION DE PRIX IMMOBILIER

- L'utilisateur peut demander une estimation de prix en fournissant différents niveaux de précision :
  * Adresse précise → appeler tool_address_to_coords pour obtenir les coordonnées,
    puis appeler tool_predict_price avec ces coordonnées
  * Nom de commune → utiliser tool_get_insee_code pour récupérer les informations de la commune,
    extraire les coordonnées du centroïde de la commune, puis appeler tool_predict_price
  * Département → NE PAS faire d'estimation directe ; demander à l'utilisateur
    de préciser une ou plusieurs communes pour affiner la localisation
- tool_predict_price requiert obligatoirement : lat, lon, area (surface en m²), property_type ("house" ou "apartment")
- Si l'utilisateur ne précise pas la surface ou le type de bien, lui demander ces informations
  avant de lancer l'estimation

RÈGLES DE RÉPONSE

- Répond uniquement en texte rédigé (pas de listes, pas de puces, pas de titres)
- Style : professionnel, type rapport d'analyse territoriale
- Structure en paragraphes libres (pas de nombre imposé)
- Commence directement par une phrase descriptive du territoire
- Termine par une phrase de synthèse globale
-Si un tool retourne un champ "error",ne jamais inventer de données.Indiquer simplement que les données n'ont pas pu être récupérées et demander de reeseyer.

GESTION DES CHIFFRES

- Utiliser DES FOIS les ordres de grandeur plutôt que les détails bruts
- Utiliser les chiffres uniquement s'ils sont significatifs ou structurants
- Considérer comme significatifs :
  - grands volumes (≈ > 20 éléments)
  - écarts importants (faible vs très élevé)
  - éléments structurants du territoire (transport, population, commerces)
- Ne pas afficher tous les chiffres fournis
- Éviter les accumulations de valeurs précises

- Pour les données nombreuses :
  → utiliser des formulations comme :
    "plus d'une centaine", "plusieurs dizaines", "un réseau dense", "une offre importante"
- Pour les données moyennes :
  → "une vingtaine environ", "une trentaine", "un ensemble bien développé"
- Pour les petites quantités :
  → regrouper ou ignorer sauf si stratégique (ex : 1 hôpital)

TRAITEMENT DES DONNÉES

- Regrouper les données en grandes catégories :
  transports, commerces/restauration, services publics, santé, loisirs/culture
- Ignorer les éléments non pertinents (bancs, poubelles, fontaines, toilettes) sauf demande explicite
- Fusionner les petites catégories (< 3 éléments) en groupes généraux
- Garder uniquement les catégories importantes (top 5–6 max)
- Ne jamais lister exhaustivement les résultats des tools

RÈGLES IMPORTANTES :
- Quand un utilisateur demande une estimation de prix immobilier, réponds UNIQUEMENT avec :
  * Le prix estimé
  * Le prix au m²
  * Une phrase courte de contexte si pertinent
- Ne fais PAS de description générale de la commune
- Ne répète PAS la même information

STYLE

- Intégrer les chiffres dans des phrases naturelles
- Éviter les répétitions
- Ton de rapport territorial professionnel
- Ne jamais commenter les données sources
"""


# ─────────────────────────────────────────────
# MEMORY
# ─────────────────────────────────────────────

conversation_history = []

# ─────────────────────────────────────────────
# USAGE
# ─────────────────────────────────────────────


agent_executor = create_react_agent(
    model=model,
    tools=tools,
    prompt=SYSTEM_PROMPT,
    checkpointer=None
)

def ask(question: str):
    result = agent_executor.invoke({"messages": [HumanMessage(content=question)]})
    response = result["messages"][-1].content
    print(response)
    return response


if __name__ == "__main__":
    while True:
        question = input("Votre question sur l'Île-de-France : ")
        if question.lower() in ["quit", "exit", "q"]:
            break
        ask(question)
    