import requests
import pandas as pd
import time
from collections import defaultdict
import math


# =========================
# 1. API OSM SAFE CALL
# =========================

def get_osm_data(lat, lon, radius=1000, max_retries=3):
    query = f"""
    [out:json];
    (
      node(around:{radius},{lat},{lon})["amenity"];
      node(around:{radius},{lat},{lon})["shop"];
      node(around:{radius},{lat},{lon})["leisure"];
      node(around:{radius},{lat},{lon})["railway"];
      node(around:{radius},{lat},{lon})["public_transport"];
    );
    out body;
    """

    urls = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter"
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; DVF-Agent/1.0)",
        "Accept": "application/json"
    }

    for url in urls:
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    data={"data": query},
                    headers=headers,
                    timeout=60
                )

                if response.status_code != 200:
                    time.sleep(2)
                    continue

                if not response.text.strip():
                    time.sleep(2)
                    continue

                return response.json()

            except Exception:
                time.sleep(2)

    return None


# =========================
# 2. PARSER OSM
# =========================

def parse_osm(data):
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

        if "railway" in tags:
            stats["stations"] += 1

        if "public_transport" in tags:
            stats["transport"] += 1

    return dict(stats)


# =========================
# 3. LOCATION SCORE
# =========================

def compute_location_score(stats):
    if not stats:
        return 0

    score = 0

    score += stats.get("school", 0) * 3
    score += stats.get("kindergarten", 0) * 2
    score += stats.get("hospital", 0) * 4
    score += stats.get("clinic", 0) * 2
    score += stats.get("station", 0) * 5
    score += stats.get("transport", 0) * 1
    score += stats.get("park", 0) * 3
    score += stats.get("shops", 0) * 0.5

    return min(100, round(score, 2))


# =========================
# 4. MAIN TOOL FUNCTION
# =========================

def osm_location_tool(lat, lon, radius=1000):
    raw = get_osm_data(lat, lon, radius)
    stats = parse_osm(raw)
    score = compute_location_score(stats)

    return {
        "input": {
            "lat": lat,
            "lon": lon,
            "radius": radius
        },
        "features": stats,
        "location_score": score
    }


def get_department_activities(dept_code):

    query = f"""
    [out:json];

    area["ref:INSEE"="{dept_code}"]->.searchArea;

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

    url = "https://overpass-api.de/api/interpreter"

    headers = {"User-Agent": "Mozilla/5.0 (DVF-Agent)"}

    r = requests.post(url, data={"data": query}, headers=headers, timeout=120)

    if r.status_code != 200:
        return None

    data = r.json()

    results = []

    for el in data.get("elements", []):
        tags = el.get("tags", {})

        results.append({
            "type": tags.get("amenity") or tags.get("shop") or tags.get("leisure") or tags.get("tourism"),
            "lat": el.get("lat"),
            "lon": el.get("lon"),
            "name": tags.get("name")
        })

    return results


def get_commune_activities(insee_code):

    query = f"""
    [out:json];

    area["ref:INSEE"="{insee_code}"]->.searchArea;

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

    url = "https://overpass-api.de/api/interpreter"

    headers = {"User-Agent": "Mozilla/5.0 (DVF-Agent)"}

    r = requests.post(url, data={"data": query}, headers=headers, timeout=120)

    if r.status_code != 200:
        return pd.DataFrame()

    data = r.json()

    results = []

    for el in data.get("elements", []):
        tags = el.get("tags", {})

        results.append({
            "type": tags.get("amenity") or tags.get("shop") or tags.get("leisure") or tags.get("tourism"),
            "lat": el.get("lat"),
            "lon": el.get("lon"),
            "name": tags.get("name"),
            "insee": insee_code
        })

    return results


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)

    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def get_transport_stops(lat, lon, radius=1000):

    query = f"""
    [out:json];
    (
      node(around:{radius},{lat},{lon})["highway"="bus_stop"];
      node(around:{radius},{lat},{lon})["railway"="station"];
      node(around:{radius},{lat},{lon})["public_transport"];
      node(around:{radius},{lat},{lon})["railway"="subway_entrance"];
    );
    out body;
    """

    url = "https://overpass-api.de/api/interpreter"

    headers = {"User-Agent": "Mozilla/5.0 (DVF-Agent)"}

    r = requests.post(url, data={"data": query}, headers=headers, timeout=60)

    if r.status_code != 200:
        return {"counts": {}, "stops": []}

    elements = r.json().get("elements", [])

    bus = 0
    metro = 0
    rail = 0

    stops = []

    for el in elements:
        tags = el.get("tags", {})

        name = tags.get("name")
        ref = tags.get("ref")
        route = tags.get("route_ref")
        line = tags.get("line")

        stop_type = None

        if tags.get("highway") == "bus_stop":
            stop_type = "bus_stop"
            bus += 1

        elif tags.get("railway") == "station":
            stop_type = "rail_station"
            rail += 1

        elif tags.get("railway") == "subway_entrance" or "subway" in str(tags):
            stop_type = "metro"
            metro += 1

        elif "public_transport" in tags:
            stop_type = "transport"

        if stop_type:
            stops.append({
                "name": name,
                "type": stop_type,
                "line": ref or route or line,
                "lat": el.get("lat"),
                "lon": el.get("lon"),
                "distance": f"{haversine(lat, lon, el.get('lat'), el.get('lon'))}m"
            })

    stops = sorted(stops, key=lambda x: float(x["distance"].replace("m", "")))

    return {
        "counts": {
            "bus_stop": bus,
            "metro": metro,
            "rail_station": rail
        },
        "stops": stops
    }


def get_commune_transport(insee_code):

    query = f"""
    [out:json][timeout:60];

    relation["admin_level"="8"]["ref:INSEE"="{insee_code}"]->.commune;
    .commune map_to_area -> .a;

    (
      node(area.a)["highway"="bus_stop"];
      node(area.a)["railway"="station"];
      node(area.a)["railway"="subway_entrance"];
      node(area.a)["railway"="tram_stop"];
    );

    out body;
    """

    url = "https://overpass-api.de/api/interpreter"
    headers = {"User-Agent": "Mozilla/5.0 (DVF-Agent)"}

    r = requests.post(url, data={"data": query}, headers=headers, timeout=90)

    if r.status_code != 200:
        print(f"Erreur HTTP {r.status_code}: {r.text[:300]}")
        return {"counts": {}, "stops": []}

    elements = r.json().get("elements", [])

    def classify_stop(tags):
        highway = tags.get("highway")
        railway = tags.get("railway")
        station = tags.get("station")

        if highway == "bus_stop":
            return "bus_stop"

        if railway == "subway_entrance":
            return "metro"

        if railway == "station" and station == "subway":
            return "metro"

        if railway == "tram_stop":
            return "tram"

        if railway == "station" and station not in ("subway", "light_rail", "monorail"):
            return "rail_station"

        return None

    bus, metro, rail, tram = 0, 0, 0, 0
    stops = []

    for el in elements:
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

        stops.append({
            "name": tags.get("name"),
            "type": stop_type,
            "lat": lat,
            "lon": lon
        })

    return {
        "insee_code": insee_code,
        "counts": {
            "bus_stop": bus,
            "metro": metro,
            "rail_station": rail,
            "tram": tram
        },
        "stops": stops
    }


def get_insee_code(city_or_postal):

    if str(city_or_postal).isdigit():
        url = f"https://geo.api.gouv.fr/communes?codePostal={city_or_postal}&fields=nom,code,codesPostaux"
    else:
        url = f"https://geo.api.gouv.fr/communes?nom={city_or_postal}&fields=nom,code,codesPostaux&limit=10"

    r = requests.get(url)

    if r.status_code != 200:
        return None

    data = r.json()

    if not data:
        return None

    result = []

    for item in data:
        result.append({
            "city": item.get("nom"),
            "insee_code": item.get("code"),
            "postal_codes": item.get("codesPostaux", [])
        })

    return result


def get_green_spaces(lat, lon, radius=1000):

    query = f"""
    [out:json];
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

    url = "https://overpass-api.de/api/interpreter"

    headers = {"User-Agent": "DVF-Agent"}

    r = requests.post(url, data={"data": query}, headers=headers, timeout=60)

    if r.status_code != 200:
        return {"count": 0, "greens": []}

    elements = r.json().get("elements", [])

    greens = []

    for el in elements:

        tags = el.get("tags", {})

        lat_ = el.get("lat") or el.get("center", {}).get("lat")
        lon_ = el.get("lon") or el.get("center", {}).get("lon")

        if not lat_ or not lon_:
            continue

        greens.append({
            "name": tags.get("name"),
            "type": tags.get("leisure") or tags.get("landuse") or tags.get("natural"),
            "lat": lat_,
            "lon": lon_
        })

    return {
        "count": len(greens),
        "greens": greens
    }


def get_commune_centroid(insee_code):
    url = f"https://geo.api.gouv.fr/communes/{insee_code}?fields=centre,nom,code"

    r = requests.get(url, headers={"Accept": "application/json"})

    if r.status_code != 200:
        return None

    data = r.json()

    coords = data.get("centre", {}).get("coordinates", None)

    if not coords:
        return None

    lon, lat = coords

    return {
        "insee": insee_code,
        "lat": lat,
        "lon": lon,
        "name": data.get("nom")
    }


def get_commune_demographics(insee_code):

    url = f"https://geo.api.gouv.fr/communes/{insee_code}?fields=nom,code,population,centre,contour"

    r = requests.get(url)

    if r.status_code != 200:
        return None

    data = r.json()

    return {
        "insee": data.get("code"),
        "name": data.get("nom"),
        "population": data.get("population"),
    }


def address_to_coords(address: str):

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": address,
        "format": "json",
        "limit": 3,
        "addressdetails": 1
    }

    headers = {
        "User-Agent": "ai-real-estate-agent"
    }

    r = requests.get(url, params=params, headers=headers)
    data = r.json()

    if not data:
        return None

    return {
        "latitude": float(data[0]["lat"]),
        "longitude": float(data[0]["lon"])
    }



def get_commune_greenspaces(insee_code):

    headers = {
        "User-Agent": "Mozilla/5.0 (DVF-Agent)",
        "Accept": "application/json"
    }

    query = f"""
    [out:json][timeout:60];

    relation["admin_level"="8"]["ref:INSEE"="{insee_code}"]->.commune;
    .commune map_to_area -> .a;

    (
      way(area.a)["leisure"="park"];
      way(area.a)["leisure"="garden"];
      way(area.a)["leisure"="nature_reserve"];
      way(area.a)["landuse"="forest"];
      way(area.a)["landuse"="grass"];
      way(area.a)["landuse"="meadow"];
      way(area.a)["natural"="wood"];
      way(area.a)["natural"="scrub"];
      way(area.a)["natural"="heath"];
    );

    out body;
    >;
    out skel qt;
    """

    r = requests.post(
        "https://overpass-api.de/api/interpreter",
        data={"data": query},
        headers=headers,
        timeout=90
    )

    if r.status_code != 200:
        print(f"Erreur HTTP {r.status_code}: {r.text[:300]}")
        return {"counts": {}, "greenspaces": []}

    try:
        elements = r.json().get("elements", [])
    except Exception:
        return {"counts": {}, "greenspaces": []}

    ways = []
    nodes = {}

    for el in elements:
        if el["type"] == "node":
            nodes[el["id"]] = (el.get("lat"), el.get("lon"))
        elif el["type"] == "way":
            ways.append(el)

    counts = {
        "park": 0,
        "garden": 0,
        "nature_reserve": 0,
        "forest": 0,
        "grass": 0,
        "meadow": 0,
        "wood": 0,
        "scrub": 0,
        "heath": 0,
    }

    greenspaces = []

    for way in ways:
        tags = way.get("tags", {})
        leisure = tags.get("leisure")
        landuse = tags.get("landuse")
        natural = tags.get("natural")

        gs_type = leisure or landuse or natural

        if gs_type not in counts:
            continue

        counts[gs_type] += 1

        way_nodes = way.get("nodes", [])
        coords = [nodes[n] for n in way_nodes if n in nodes and nodes[n][0] is not None]

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
            "osm_id": way["id"]
        })

    return {
        "insee_code": insee_code,
        "counts": counts,
        "greenspaces": greenspaces
    }