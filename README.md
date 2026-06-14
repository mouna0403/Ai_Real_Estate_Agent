<p align="center">
  <img src="image/ai_real_estate_agent.png" width="100%" />
</p>

## Overview

**AI Real Estate Agent** is a conversational assistant for **territorial analysis and real estate price estimation in Île-de-France**. It can be run locally as a Streamlit app or deployed as a **Google Chat Add-on** on Cloud Run.

Built with a **Groq LLM (Llama 3.3)**, **geospatial tools (INSEE + OpenStreetMap)**, and an **XGBoost regression model (R² ≈ 0.80)**.

---

## Features

* Territorial analysis in Île-de-France (communes, GPS points)
* OpenStreetMap enrichment (POIs, transport, amenities)
* INSEE demographic data
* Transport network analysis (bus, metro, RER, rail)
* Green space analysis
* Address → GPS conversion
* Real estate price prediction

---

## Machine Learning Model

* **Model:** XGBoost Regressor
* **Performance:** R² ≈ 0.80

**Features used by the model:**

* lat
* lon
* area (m²)
* property_type (house / apartment)

---

## Tools

* **tool_get_insee_code:** Converts city/postal code into INSEE code (entry point for commune analysis)
* **tool_get_commune_centroid:** Returns geographic centroid of a commune using INSEE code → {insee, lat, lon, name}
* **tool_address_to_coords:** Converts an address into GPS coordinates (lat/lon)
* **tool_predict_price:** Predicts real estate price using lat, lon, area, property_type (XGBoost model)
* **tool_osm_location:** Analyzes POIs around a GPS point using OpenStreetMap
* **tool_get_transport_stops:** Gets nearby transport stops (bus, metro, rail) around coordinates
* **tool_get_commune_transport:** Gets full transport network of a commune (INSEE-based)
* **tool_get_green_spaces:** Gets green spaces around a GPS point
* **tool_get_commune_greenspaces:** Gets all green spaces in a commune
* **tool_get_commune_activities:** Gets shops, services and activities in a commune
* **tool_get_department_activities:** Gets activities at department level
* **tool_get_commune_demographics:** Gets population data for a commune (INSEE)

---

## Agent Workflow

1. Interpret user request
2. Select required tools
3. Retrieve geographic data (INSEE / OpenStreetMap)
4. Enrich with transport, POIs, green spaces
5. Convert address → GPS if needed
6. If only a commune is given → use **tool_get_commune_centroid**
7. Run **XGBoost model** for price prediction when required
8. Return synthesized response

---

## Example Interactions

**me:** What is the population of Créteil?
**Agent:** The commune of Créteil has an estimated population of around 93,000 inhabitants.

---

**me:** What is the estimated price for a 50m² apartment in central Paris?
**Agent:** The estimated price for a 50m² apartment in central Paris is around 420,000 euros, corresponding to approximately 8,400 euros per square meter.

---

**me:** Analyze the green spaces in Créteil.
**Agent:** Créteil has a significant amount of green spaces, including Parc Dupeyroux and Parc de la Brèche, plus smaller green spaces distributed across the territory.

---

## Installation

```bash
git clone https://github.com/your-repo/ai-real-estate-agent
cd ai-real-estate-agent
```

---

## Setup (uv)

```bash
uv sync
```

---

## Environment

Create `.env`:

```env
GROQ_API_KEY=your_api_key
```

---

## Get Groq API Key

* Go to [https://console.groq.com](https://console.groq.com)
* Create an account and generate an API key
* Add it to `.env`

---

## Option 1 — Run Locally (Streamlit)

```bash
uv run streamlit run .\src\Ai_Real_Estate_Agent\main1.py
```

Open your browser and interact with the chat interface:

```
me: Your question about Île-de-France
```

---

## Option 2 — Deploy as Google Chat Add-on (Cloud Run)

This deploys the FastAPI app (`main.py`) as a Google Chat Add-on accessible directly from Google Chat.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

---


### Step 1 — Enable required APIs

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com chat.googleapis.com
````

---

### Step 2 — Create an Artifact Registry repository

```bash
gcloud artifacts repositories create ai-real-estate-repo \
  --repository-format=docker \
  --location=europe-west1
```

---

### Step 3 — Authenticate Docker with Google Cloud

```bash
gcloud auth configure-docker europe-west1-docker.pkg.dev
```

---

### Step 4 — Build and tag the Docker image

```bash
docker build -t ai-real-estate-agent-app .

docker tag ai-real-estate-agent-app \
  europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/ai-real-estate-repo/ai-real-estate-agent-app:latest
```

---

### Step 5 — Push the image to Artifact Registry

```bash
docker push \
  europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/ai-real-estate-repo/ai-real-estate-agent-app:latest
```

---

### Step 6 — Create Secret Manager secret (europe-west1)

```bash
gcloud secrets create GROQ_API_KEY \
  --replication-policy=user-managed \
  --locations=europe-west1
```

```bash
echo -n "YOUR_GROQ_API_KEY" | \
gcloud secrets versions add GROQ_API_KEY \
  --data-file=-
```

---

### Step 7 — Grant Secret Manager access to Cloud Run

```bash
gcloud projects describe YOUR_PROJECT_ID \
  --format="value(projectNumber)"
```

```bash
gcloud secrets add-iam-policy-binding GROQ_API_KEY \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

### Step 8 — Deploy to Cloud Run (using Secret Manager)

```bash
gcloud run deploy ai-real-estate-agent-app \
  --image europe-west1-docker.pkg.dev/YOUR_PROJECT_ID/ai-real-estate-repo/ai-real-estate-agent-app:latest \
  --region europe-west1 \
  --platform managed \
  --set-secrets=GROQ_API_KEY=GROQ_API_KEY:latest
```



---

### Step 9 — Grant invoke permission to Google Workspace Add-ons

First, retrieve the service account email:
1. Google Cloud Console → APIs & Services → Google Chat API → Configuration
2. Scroll down to the **"App credentials"** section
3. Copy the value of **"Service account email"**
   (format: `service-XXXXXXXXX@gcp-sa-gsuiteaddons.iam.gserviceaccount.com`)

Then run:

```bash
gcloud run services add-iam-policy-binding ai-real-estate-agent-app \
  --region=europe-west1 \
  --member="serviceAccount:service-XXXXXXXXX@gcp-sa-gsuiteaddons.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

---

### Step 10 — Configure the Google Chat API

1. Google Cloud Console → APIs & Services → Google Chat API → Configuration
2. App name: AI Real Estate Agent
3. Avatar URL: public HTTPS image (PNG, square, min 256x256)
4. Description: AI assistant for real estate analysis
5. Enable interactive features:
   * Users can DM the app
   * App can join spaces and group conversations
6. Connection settings:
   * HTTP endpoint URL → Cloud Run service URL
7. Triggers:
   * Use common HTTP endpoint URL for all triggers
   * URL: `https://YOUR-CLOUDRUN-URL/chat`
8. Visibility:
   * Add your Gmail address
9. Save

---

### Step 11 — Find the app in Google Chat

```text
Google Chat
  -> New Chat
  -> Search Apps
  -> AI Real Estate Agent
```

---

### Scope

* Strictly limited to Île-de-France (75, 77, 78, 91, 92, 93, 94, 95)
* Tool-based reasoning only
* No API keys in environment variables
* Secrets managed via Google Secret Manager (europe-west1)
* Cloud Run endpoint secured via IAM — only invocable by `gcp-sa-gsuiteaddons`

external factual assumptions
* Responds in the same language as the user (French or English)
