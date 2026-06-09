import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from Ai_Real_Estate_Agent.utils.predictor import predict_price
from Ai_Real_Estate_Agent.utils.osm import *

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

# IDF departments: 75,77,78,91,92,93,94,95
IDF_DEPARTMENTS = {"75", "77", "78", "91", "92", "93", "94", "95"}

def is_in_idf(insee_code: str) -> bool:
    """Check if INSEE code belongs to Île-de-France."""
    dept = insee_code[:2] if insee_code.startswith("97") else insee_code[:2]
    return dept in IDF_DEPARTMENTS

def validate_idf(insee_code: str) -> bool:
    """Validate that request is limited to Île-de-France."""
    if not is_in_idf(insee_code):
        raise ValueError(f"Request limited to Île-de-France. INSEE {insee_code} not in IDF.")
    return True

def truncate_output(data, max_items: int = 5):
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

# TOOLS

@tool
def tool_get_insee_code(city: str) -> list:
    """
    Convert city name to INSEE code(s).
    Input: city name (ex: 'Paris') or postal code (ex: '75000')
    Output: list of dicts with {city, insee_code, postal_codes}
    """
    try:
        result = get_insee_code(city)
        return truncate_output(result) if result else None
    except Exception as e:
        return {"error": f"Failed to get INSEE code: {str(e)}"}

@tool
def tool_osm_location(lat: float, lon: float, radius: int = 1000) -> dict:
    """
    Analyze points of interest around GPS coordinates via OpenStreetMap.
    Input: latitude (ex: 48.8566), longitude (ex: 2.3522), radius in meters (default 1000)
    Output: dict with {input: {lat, lon, radius}, features: [list of POIs with name, type, distance, lat, lon], location_score: float (0-100)}
    Features include: restaurants, shops, schools, hospitals, parks, cultural sites, sports facilities, etc.
    """
    try:
        return truncate_output(osm_location_tool(lat, lon, radius))
    except Exception as e:
        return {"error": f"OSM location failed: {str(e)}"}

@tool
def tool_get_department_activities(dept_code: str) -> list:
    """
    Get all activities and POIs in a French department.
    Input: department code (ex: '75' for Paris, '92' for Hauts-de-Seine)
    Output: list of dicts with {type (restaurant/school/hospital/shop/park), lat, lon, name}
    Activities include: restaurants, schools, hospitals, shops, parks, cultural venues, sports facilities, places of worship, public services
    """
    try:
        validate_idf(dept_code + "000")
        result = get_department_activities(dept_code)
        return truncate_output(result) if result else None
    except Exception as e:
        return {"error": str(e)}

@tool
def tool_get_commune_activities(insee_code: str) -> dict:
    """
    Get all activities and POIs in a specific commune.
    Input: 5-digit INSEE code (ex: '75056' for Paris, '92050' for Nanterre)
    Output: dict with activities grouped by type with {type: [list of {name, lat, lon}]}
    Activities include: restaurants, fast food, cafes, schools (kindergarten/elementary/high), hospitals (clinic/hospital), shops (supermarket/bakery/butcher), parks, cultural (cinema/theater/museum), sports (gym/stadium/pool), public services (post office/police/town hall)
    """
    try:
        validate_idf(insee_code)
        return truncate_output(get_commune_activities(insee_code))
    except Exception as e:
        return {"error": str(e)}

@tool
def tool_get_transport_stops(lat: float, lon: float, radius: int = 1000) -> dict:
    """
    Get public transport stops around GPS point.
    Input: latitude (ex: 48.8566), longitude (ex: 2.3522), radius in meters (default 1000)
    Output: dict with {counts: {bus_stop, metro, rail_station}, stops: [{name, type, line, lat, lon, distance}]}
    """
    try:
        return truncate_output(get_transport_stops(lat, lon, radius))
    except Exception as e:
        return {"error": f"Transport stops failed: {str(e)}"}

@tool
def tool_get_commune_transport(insee_code: str) -> dict:
    """
    Get all public transport stops in a commune.
    Input: 5-digit INSEE code (ex: '75056' for Paris, '92050' for Nanterre)
    Output: dict with {insee_code, counts: {bus_stop, metro, rail_station, tram}, stops: [{name, type, lat, lon}]}
    """
    try:
        validate_idf(insee_code)
        return truncate_output(get_commune_transport(insee_code))
    except Exception as e:
        return {"error": str(e)}

@tool
def tool_get_commune_centroid(insee_code: str) -> dict:
    """
    Get geographic center coordinates of a commune.
    Input: 5-digit INSEE code (ex: '75056' for Paris)
    Output: dict with {insee, lat, lon, name}
    """
    try:
        validate_idf(insee_code)
        result = get_commune_centroid(insee_code)
        return result if result else {"error": "Commune not found"}
    except Exception as e:
        return {"error": str(e)}

@tool
def tool_get_green_spaces(lat: float, lon: float, radius: int = 1000) -> dict:
    """
    Get green spaces around GPS point.
    Input: latitude (ex: 48.8566), longitude (ex: 2.3522), radius in meters (default 1000)
    Output: dict with {count, greens: [{name, type, lat, lon, distance}]}
    Green space types: park, garden, nature_reserve, forest, grass, meadow, wood
    """
    try:
        return truncate_output(get_green_spaces(lat, lon, radius))
    except Exception as e:
        return {"error": f"Green spaces failed: {str(e)}"}

@tool
def tool_get_commune_greenspaces(insee_code: str) -> dict:
    """
    Get all green spaces in a commune.
    Input: 5-digit INSEE code (ex: '75056' for Paris)
    Output: dict with {insee_code, counts: {park, garden, nature_reserve, forest, grass, meadow, wood, scrub, heath}, greenspaces: [{name, type, lat, lon, osm_id}]}
    """
    try:
        validate_idf(insee_code)
        return get_commune_greenspaces(insee_code)
    except Exception as e:
        return {"error": str(e)}

@tool
def tool_get_commune_demographics(insee_code: str) -> dict:
    """
    Get demographic data for a commune.
    Input: 5-digit INSEE code (ex: '75056' for Paris)
    Output: dict with {insee, name, population}
    """
    try:
        validate_idf(insee_code)
        return truncate_output(get_commune_demographics(insee_code))
    except Exception as e:
        return {"error": str(e)}

@tool
def tool_address_to_coords(address: str) -> dict:
    """
    Convert postal address to GPS coordinates.
    Input: full address string (ex: '10 rue de Rivoli, 75004 Paris')
    Output: dict with {latitude, longitude}
    """
    try:
        return address_to_coords(address)
    except Exception as e:
        return {"error": f"Address conversion failed: {str(e)}"}

@tool
def tool_predict_price(lat: float, lon: float, area: float, property_type: str) -> int:
    """
    Predict property sale price based on location and characteristics.
    Input: latitude, longitude, area in m² (ex: 75.0), property_type ('house' or 'apartment')
    Output: integer estimated price in euros
    """
    try:
        return predict_price(lat, lon, area, property_type)
    except Exception as e:
        return {"error": f"Price prediction failed: {str(e)}"}

model = ChatGroq(
    model="llama-3.3-70b-versatile", #"llama-3.1-8b-instant",
    temperature=0.3,
    max_tokens=512
)

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
    tool_get_commune_centroid,
]

SYSTEM_PROMPT = """
You are a territorial analysis assistant for Île-de-France only. Never use internal knowledge for facts or stats. Always use tools.

RESTRICTION: Only respond to requests about Île-de-France (departments 75,77,78,91,92,93,94,95). If user asks outside IDF, say you cannot respond.

CRITICAL RULE: Respond ONLY to the user's exact request. Do not add extra information, do not provide additional analysis, do not suggest related topics. Answer precisely what is asked and nothing more. "You must explicitly tell it to use the INSEE code returned by `tool_get_insee_code`, not to make one up."

PRICE ESTIMATION:
- Address → tool_address_to_coords + tool_predict_price
- Commune → tool_get_insee_code + tool_get_commune_centroid + tool_predict_price
- Department → ask user to specify a commune
- Require area (m²) and property_type ("house"/"apartment") - ask if missing

RESPONSE STYLE:
- Respond in same language as user (French or English)
- Professional report style, natural paragraphs
- No lists, no bullets, no markdown
- Group data into categories: transport, shops/restaurants, public services, health, leisure
- Use approximations: "over a hundred", "several dozen", "approximately twenty"
- Show only significant numbers (>20 items or major differences)
- Ignore irrelevant items (benches, trash cans, fountains)

PRICE REQUESTS ONLY: Respond with estimated price, price per m², and one short context sentence. No general commune description.

If tool returns "error", state data unavailable and ask to retry.
"""

agent_executor = create_react_agent(
    model=model,
    tools=tools,
    prompt=SYSTEM_PROMPT,
    checkpointer=None
)

def ask(question: str):
    print(f"\n[USER] {question}")
    print("[AGENT] Processing...")
    
    result = agent_executor.invoke({"messages": [HumanMessage(content=question)]})
    
    for msg in result["messages"]:
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            print(f"[TOOL] {msg.tool_calls}")
        elif hasattr(msg, 'name') and msg.name:
            print(f"[TOOL_RESULT] {msg.name}: {str(msg.content)[:200]}...")
    
    response = result["messages"][-1].content
    print(f"[AGENT] {response}")
    return response

if __name__ == "__main__":
    print("Agent ready. IDF only (75,77,78,91,92,93,94,95)")
    while True:
        question = input("\nYour question: ")
        if question.lower() in ["quit", "exit", "q"]:
            break
        ask(question)