import numpy as np
import pandas as pd
import joblib
from pyproj import Transformer
from pathlib import Path

MODEL_PATH = Path(__file__).parents[1] / "models" / "xgb_model.pkl"





def predict_price(lat, lon, area, property_type):
    """
    Predict real estate price based on location, area and property type.
    """
    model = joblib.load(MODEL_PATH)
    X = pd.DataFrame([{
        "latitude": lat,
        "longitude": lon,
        "area": np.log1p(area)
    }])

    # Recreate exact dummy column expected by the model
    X["property_type_house"] = (property_type == "house")
    X = X[["area", "latitude", "longitude", "property_type_house"]]

    # Transform coordinates to French projection system
    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:2154",
        always_xy=True
    )

    X["longitude"], X["latitude"] = transformer.transform(
        X["longitude"].values,
        X["latitude"].values  # Fixed: was X["longitude"] duplicated
    )

    pred_log = model.predict(X)
    return int(np.expm1(pred_log)[0])

if __name__ == "__main__":
    # Test cases - Île-de-France
    test_cases = [
        (48.8566, 2.3522, 10, "apt"),   # Paris centre - small apt
        (48.8566, 2.3522, 50, "apt"),   # Paris centre - apt
        (48.8566, 2.3522, 80, "house"), # Paris centre - house
        (48.8848, 2.2690, 30, "apt"),   # Neuilly - apt
        (48.8848, 2.2690, 100, "house"),   # Neuilly - apt
        (48.7903, 2.4557, 25, "apt"),   # Créteil - apt
        (48.7903, 2.4557, 60, "apt"),   # Créteil - apt
        (48.9358, 2.3540, 55, "apt"),   # Saint-Denis - apt
        (48.9358, 2.3540, 70, "house"),   # Saint-Denis - apt
        (48.8014, 2.1301, 90, "house"), # Versailles - house
        (49.0359, 2.0625, 85, "house"), # Cergy - house
        (49.0359, 2.0625, 40, "apt"), # Cergy - house
    ]
    
    for lat, lon, area, prop_type in test_cases:
        price = predict_price(lat, lon, area, prop_type)
        print(f"{lat}, {lon}, {area}, {prop_type} -> {price:,.0f} €")