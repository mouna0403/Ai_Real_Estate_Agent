<p align="center">
  <img src="image/ai_real_estate_agent.png" width="100%" />
</p>

## **Overview**

Interactive **Streamlit** application for **territorial analysis** and **real estate estimation** in **Île-de-France** only.  
Built with a **Groq LLM (Llama 3.3)**, **geospatial tools (INSEE + OpenStreetMap)**, and an **XGBoost regression model** (R² ≈ 0.80).

The system runs as a **real-time interactive chat interface** via **Streamlit**.

---

## **Features**

- **Territorial analysis** in **Île-de-France** (communes, GPS points)
- **OpenStreetMap enrichment** (POIs, transport, amenities)
- **INSEE demographic data**
- **Transport network analysis** (bus, metro, RER, rail)
- **Green space analysis**
- **Address → GPS conversion**
- **Real estate price prediction**

---

## **Machine Learning Model**

- **Model**: **XGBoost Regressor**  
- **Performance**: **R² ≈ 0.80**  

**Features used by the model:**
- **latitude**  
- **longitude**  
- **area (m²)**  
- **property_type** (house / apartment)

---

## **Tools**

- **tool_get_insee_code**: Converts city/postal code into **INSEE code** (entry point for commune analysis)
- **tool_get_commune_centroid**: Returns **geographic centroid** of a commune (INSEE → lat/lon/name)
- **tool_address_to_coords**: Converts an **address into GPS coordinates** (lat/lon)
- **tool_predict_price**: Predicts **real estate price** using lat, lon, area, property_type (XGBoost model)
- **tool_osm_location**: Analyzes **POIs around a GPS point** using OpenStreetMap
- **tool_get_transport_stops**: Gets **nearby transport stops** (bus, metro, rail)
- **tool_get_commune_transport**: Gets **full transport network** of a commune
- **tool_get_green_spaces**: Gets **green spaces around a GPS point**
- **tool_get_commune_greenspaces**: Gets **all green spaces in a commune**
- **tool_get_commune_activities**: Gets **shops, services and activities** in a commune
- **tool_get_department_activities**: Gets **activities at department level**
- **tool_get_commune_demographics**: Gets **population data** for a commune (INSEE)

---

## **Agent Workflow**

1. **Interpret** user request  
2. **Select** required tools  
3. **Retrieve** geographic data (INSEE / OSM)  
4. **Enrich** with transport, POIs, green spaces  
5. **Convert** address → GPS if needed  
6. If only a commune is given → use **tool_get_commune_centroid**  
7. **Run XGBoost model** for price prediction when required  
8. **Return** synthesized response  

---

## **Example interactions**

**me:** What is the demographics of Creteil?  
**Agent:** The commune of Créteil has an estimated population of around 93,000 inhabitants.

---

**me:** What is the estimated price for a 50m² apartment in central Paris?  
**Agent:** The estimated price for a 50m² apartment in central Paris is around 420,000 euros, corresponding to approximately 8,400 euros per square meter.

---

**me:** Analyze green spaces in Creteil  
**Agent:** The commune of Créteil, located in the Val-de-Marne department, has a significant amount of green spaces, including several parks and gardens. Parc Dupeyroux and Parc de la Brèche are two notable examples, offering relaxation and leisure areas for residents. In addition, the commune has many small green spaces scattered throughout its territory, such as squares and gardens, which help improve residents' quality of life. In total, the commune of Créteil has over 2,000 green spaces, including around twenty parks and gardens, as well as nature reserves and forests. This significant green space offering makes Créteil a pleasant place to live, with many areas to relax and enjoy nature.

---

## **Installation**

```bash
git clone https://github.com/your-repo/ai-real-estate-agent
cd ai-real-estate-agent
````

---

## **Setup (uv)**

```bash
uv sync
```

---

## **Environment**

Create **`.env`**:

```env
GROQ_API_KEY=your_api_key
```

---

## **Run (Streamlit App)**

```bash
uv run streamlit run src/Ai_Real_Estate_Agent/main.py
```

---

## **Scope**

* Strictly limited to **Île-de-France**
* **Tool-based reasoning** only
* **No external factual assumptions**
* **Real-time interactive Streamlit interface**
