import requests
import pandas as pd
import time
from collections import defaultdict
import math


# =========================
# HELPERS
# =========================

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

OVERPASS_HEADERS = {
    "User-Agent": "DVF-Agent/1.0 (real-estate analysis tool)",
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
}


def _post_overpass(query: str, timeout: int = 60, max_retries: int = 3):
    """
    Envoie une requête Overpass en essayant plusieurs serveurs.
    Retourne le JSON parsé ou None en cas d'échec.
    """
    for url in OVERPASS_URLS:
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    data={"data": query},
                    headers=OVERPASS_HEADERS,
                    timeout=timeout,
                )
                if response.status_code == 200 and response.text.strip():
                    return response.json()
                time.sleep(2)
            except Exception:
                time.sleep(2)
    return None


def _build_area_filter(insee_code: str) -> str:
    """
    Construit le filtre de zone Overpass le plus compatible possible
    en testant ref:INSEE:commune puis ref:INSEE comme fallback.
    """
    # On essaie les deux tags possibles dans la même requête via union
    return f"""
    (
      area["ref:INSEE:commune"="{insee_code}"];
      area["ref:INSEE"="{insee_code}"];
    )->.searchArea;
    """


# =========================
# 1. API OSM — ACTIVITÉS & COMMERCES
# =========================

def osm_location_tool(lat, lon, radius=1000, max_retries=3):
    """
    Récupère les activités, commerces et loisirs autour d'un point.
    Retourne un dict {type: count}.
    """
    query = f"""
    [out:json][timeout:60];
    (
      node(around:{radius},{lat},{lon})["amenity"];
      node(around:{radius},{lat},{lon})["shop"];
      node(around:{radius},{lat},{lon})["leisure"];
    );
    out body;
    """
    data = _post_overpass(query, timeout=60, max_retries=max_retries)
    if not data or "elements" not in data:
        return {}

    stats = defaultdict(int)
    for el in data["elements"]:
        tags = el.get("tags", {})
        if "amenity" in tags:
            stats[tags["amenity"]] += 1
        if "shop" in tags:
            stats["shops"] += 1
        if "leisure" in tags:
            stats[tags["leisure"]] += 1

    return dict(stats)


# =========================
# 2. DEPARTMENT ACTIVITIES
# =========================

def get_department_activities(dept_code):
    query = f"""
    [out:json][timeout:120];
    area["ref:INSEE:departement"="{dept_code}"]->.searchArea;
    (
      node(area.searchArea)["amenity"];
      node(area.searchArea)["shop"];
      node(area.searchArea)["leisure"];
      node(area.searchArea)["tourism"];
      node(area.searchArea)["public_transport"];
      node(area.searchArea)["railway"];
    );
    out body;
    """

    data = _post_overpass(query, timeout=120)
    if not data:
        return None

    results = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        results.append({
            "type": tags.get("amenity") or tags.get("shop") or tags.get("leisure") or tags.get("tourism"),
            "lat": el.get("lat"),
            "lon": el.get("lon"),
            "name": tags.get("name"),
        })

    return results


# =========================
# 3. COMMUNE ACTIVITIES
# =========================

def get_commune_activities(insee_code):
    area_filter = _build_area_filter(insee_code)
    query = f"""
    [out:json][timeout:90];
    {area_filter}
    (
      node(area.searchArea)["amenity"];
      node(area.searchArea)["shop"];
      node(area.searchArea)["leisure"];
      node(area.searchArea)["tourism"];
      node(area.searchArea)["public_transport"];
      node(area.searchArea)["railway"];
    );
    out body;
    """

    data = _post_overpass(query, timeout=90)
    if not data:
        return {"insee": insee_code, "counts": {}, "items": []}

    counts = defaultdict(int)
    items = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        activity_type = tags.get("amenity") or tags.get("shop") or tags.get("leisure") or tags.get("tourism")
        if activity_type:
            counts[activity_type] += 1
        items.append({
            "type": activity_type,
            "name": tags.get("name"),
            "lat": el.get("lat"),
            "lon": el.get("lon"),
        })

    return {
        "insee": insee_code,
        "counts": dict(counts),
        "items": items[:10],
    }


# =========================
# 4. HAVERSINE
# =========================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# =========================
# 5. TRANSPORT STOPS (around lat/lon)
# =========================

def get_transport_stops(lat, lon, radius=1000):
    query = f"""
    [out:json][timeout:60];
    (
      node(around:{radius},{lat},{lon})["highway"="bus_stop"];
      node(around:{radius},{lat},{lon})["railway"="station"];
      node(around:{radius},{lat},{lon})["public_transport"];
      node(around:{radius},{lat},{lon})["railway"="subway_entrance"];
      node(around:{radius},{lat},{lon})["railway"="tram_stop"];
    );
    out body;
    """

    data = _post_overpass(query, timeout=60)
    if not data:
        return {"counts": {}, "stops": []}

    elements = data.get("elements", [])
    bus, metro, rail, tram = 0, 0, 0, 0
    stops = []

    for el in elements:
        tags = el.get("tags", {})
        el_lat, el_lon = el.get("lat"), el.get("lon")
        if not el_lat or not el_lon:
            continue

        name = tags.get("name")
        ref = tags.get("ref") or tags.get("route_ref") or tags.get("line")
        stop_type = None

        if tags.get("highway") == "bus_stop":
            #stop_type = "bus_stop"
            bus += 1
        elif tags.get("railway") == "subway_entrance" or tags.get("station") == "subway":
            #stop_type = "metro"
            metro += 1
        elif tags.get("railway") == "tram_stop":
            #stop_type = "tram"
            tram += 1
        elif tags.get("railway") == "station":
            #stop_type = "rail_station"
            rail += 1
        # elif "public_transport" in tags:
        #     #stop_type = "transport"

        # if stop_type:
        #     dist = haversine(lat, lon, el_lat, el_lon)
        #     stops.append({
        #         "name": name,
        #         "type": stop_type,
        #         "line": ref,
        #         "lat": el_lat,
        #         "lon": el_lon,
        #         "distance_m": round(dist),
        #     })

    #stops = sorted(stops, key=lambda x: x["distance_m"])
    return {
        "counts": {"bus_stop": bus, "metro": metro, "rail_station": rail, "tram": tram}
    }

    


# =========================
# 6. COMMUNE TRANSPORT
# =========================

def get_commune_transport(insee_code):
    area_filter = _build_area_filter(insee_code)
    query = f"""
    [out:json][timeout:90];
    {area_filter}
    (
      node(area.searchArea)["highway"="bus_stop"];
      node(area.searchArea)["railway"="station"];
      node(area.searchArea)["railway"="subway_entrance"];
      node(area.searchArea)["railway"="tram_stop"];
    );
    out body;
    """

    data = _post_overpass(query, timeout=90)
    if not data:
        return {"insee_code": insee_code, "counts": {}, "stops": []}

    def classify_stop(tags):
        highway = tags.get("highway")
        railway = tags.get("railway")
        station = tags.get("station")
        if highway == "bus_stop":
            return "bus_stop"
        if railway == "subway_entrance" or station == "subway":
            return "metro"
        if railway == "tram_stop":
            return "tram"
        if railway == "station":
            return "rail_station"
        return None

    bus, metro, rail, tram = 0, 0, 0, 0
    stops = []

    for el in data.get("elements", []):
        tags = el.get("tags", {})
        lat, lon = el.get("lat"), el.get("lon")
        if not lat or not lon:
            continue

        stop_type = classify_stop(tags)
        if not stop_type:
            continue

        if stop_type == "bus_stop":
            bus += 1
        elif stop_type == "metro":
            metro += 1
        elif stop_type == "rail_station":
            rail += 1
        elif stop_type == "tram":
            tram += 1

        stops.append({"name": tags.get("name"), "type": stop_type, "lat": lat, "lon": lon})

    return {
        "insee_code": insee_code,
        "counts": {"bus_stop": bus, "metro": metro, "rail_station": rail, "tram": tram},
        #"stops": stops,
    }


# =========================
# 7. COMMUNE GREEN SPACES
# =========================

def get_commune_greenspaces(insee_code):
    area_filter = _build_area_filter(insee_code)
    query = f"""
    [out:json][timeout:90];
    {area_filter}
    (
      way(area.searchArea)["leisure"="park"];
      way(area.searchArea)["leisure"="garden"];
      way(area.searchArea)["leisure"="nature_reserve"];
      way(area.searchArea)["landuse"="forest"];
      way(area.searchArea)["landuse"="grass"];
      way(area.searchArea)["landuse"="meadow"];
      way(area.searchArea)["natural"="wood"];
      way(area.searchArea)["natural"="scrub"];
      way(area.searchArea)["natural"="heath"];
    );
    out body;
    >;
    out skel qt;
    """

    data = _post_overpass(query, timeout=90)
    if not data:
        return {"insee_code": insee_code, "counts": {}, "greenspaces": []}

    elements = data.get("elements", [])
    ways, nodes = [], {}

    for el in elements:
        if el["type"] == "node":
            nodes[el["id"]] = (el.get("lat"), el.get("lon"))
        elif el["type"] == "way":
            ways.append(el)

    counts = {
        "park": 0, "garden": 0, "nature_reserve": 0,
        "forest": 0, "grass": 0, "meadow": 0,
        "wood": 0, "scrub": 0, "heath": 0,
    }
    greenspaces = []

    for way in ways:
        tags = way.get("tags", {})
        gs_type = tags.get("leisure") or tags.get("landuse") or tags.get("natural")
        if gs_type not in counts:
            continue

        counts[gs_type] += 1

        coords = [nodes[n] for n in way.get("nodes", []) if n in nodes and nodes[n][0] is not None]
        if coords:
            lat = sum(c[0] for c in coords) / len(coords)
            lon = sum(c[1] for c in coords) / len(coords)
        else:
            lat, lon = None, None

        greenspaces.append({
            "name": tags.get("name"),
            "type": gs_type,
            "lat": lat,
            "lon": lon,
            "osm_id": way["id"],
        })

    return {"insee_code": insee_code, "counts": counts, "greenspaces": greenspaces[:5]}


# =========================
# 8. GET INSEE CODE
# =========================

def get_insee_code(city_or_postal):
    if str(city_or_postal).isdigit():
        url = f"https://geo.api.gouv.fr/communes?codePostal={city_or_postal}&fields=nom,code,codesPostaux"
    else:
        url = f"https://geo.api.gouv.fr/communes?nom={city_or_postal}&fields=nom,code,codesPostaux&limit=10"

    r = requests.get(url, timeout=15)
    if r.status_code != 200 or not r.json():
        return None

    return [
        {"city": item.get("nom"), "insee_code": item.get("code"), "postal_codes": item.get("codesPostaux", [])}
        for item in r.json()
    ]


# =========================
# 9. GREEN SPACES (around lat/lon)
# =========================

def get_green_spaces(lat, lon, radius=1000):
    query = f"""
    [out:json][timeout:60];
    (
      node(around:{radius},{lat},{lon})["leisure"~"park|garden|nature_reserve"];
      way(around:{radius},{lat},{lon})["leisure"~"park|garden|nature_reserve"];
      relation(around:{radius},{lat},{lon})["leisure"~"park|garden|nature_reserve"];
      node(around:{radius},{lat},{lon})["landuse"="grass"];
      way(around:{radius},{lat},{lon})["landuse"="grass"];
      relation(around:{radius},{lat},{lon})["landuse"="grass"];
      node(around:{radius},{lat},{lon})["natural"="wood"];
      way(around:{radius},{lat},{lon})["natural"="wood"];
      relation(around:{radius},{lat},{lon})["natural"="wood"];
    );
    out center;
    """

    data = _post_overpass(query, timeout=60)
    if not data:
        return {"count": 0, "greens": []}

    greens = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        lat_ = el.get("lat") or el.get("center", {}).get("lat")
        lon_ = el.get("lon") or el.get("center", {}).get("lon")
        if not lat_ or not lon_:
            continue
        greens.append({
            "name": tags.get("name"),
            "type": tags.get("leisure") or tags.get("landuse") or tags.get("natural"),
            "lat": lat_,
            "lon": lon_,
        })

    return {"count": len(greens), "greens": greens[:5]}


# =========================
# 10. COMMUNE CENTROID
# =========================

def get_commune_centroid(insee_code):
    url = f"https://geo.api.gouv.fr/communes/{insee_code}?fields=centre,nom,code"
    r = requests.get(url, headers={"Accept": "application/json"}, timeout=15)
    if r.status_code != 200:
        return None

    data = r.json()
    coords = data.get("centre", {}).get("coordinates")
    if not coords:
        return None

    lon, lat = coords
    return {"insee": insee_code, "lat": lat, "lon": lon, "name": data.get("nom")}


# =========================
# 11. COMMUNE DEMOGRAPHICS
# =========================

def get_commune_demographics(insee_code):
    url = f"https://geo.api.gouv.fr/communes/{insee_code}?fields=nom,code,population,centre,contour"
    r = requests.get(url, timeout=15)
    if r.status_code != 200:
        return None

    data = r.json()
    return {
        "insee": data.get("code"),
        "name": data.get("nom"),
        "population": data.get("population"),
    }


# =========================
# 12. ADDRESS TO COORDS
# =========================

def address_to_coords(address: str):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 3, "addressdetails": 1}
    headers = {"User-Agent": "DVF-Agent/1.0 (real-estate analysis tool)"}

    r = requests.get(url, params=params, headers=headers, timeout=15)
    data = r.json()
    if not data:
        return None

    return {
        "latitude": float(data[0]["lat"]),
        "longitude": float(data[0]["lon"]),
    }