import numpy as np
import pandas as pd
import joblib
from pyproj import Transformer
from pathlib import Path

MODEL_PATH = Path(__file__).parents[1] / "models" / "xgb_model.pkl"


model = joblib.load(MODEL_PATH)

def predict_price(lat, lon, area, property_type):


    transformer = Transformer.from_crs(
        "EPSG:4326",
        "EPSG:2154",
        always_xy=True
    )

    paris_lon, paris_lat = transformer.transform(
        2.3522,
        48.8566
    )

    lon, lat = transformer.transform(
        lon,
        lat
    )

    distance_paris = np.hypot(
        lon - paris_lon,
        lat - paris_lat
    ) / 1000

    X = pd.DataFrame([{
        "area": np.log1p(area),
        "latitude": lat,
        "longitude": lon,
        "distance_paris": distance_paris
    }])

    X["property_type_house"] = (
        property_type == "house"
    )

    X = X[
        [
            "area",
            "latitude",
            "longitude",
            "distance_paris",
            "property_type_house"
        ]
    ]

    pred = model.predict(X)

    return int(pred[0])


if __name__ == "__main__":

    print("------------------------Versailles------------------------")

    VERSAILLES_LAT = 48.8039
    VERSAILLES_LON = 2.1191

    offsets = {
        "centre":    (0,       0),
        "nord":      (+0.0045, 0),
        "sud":       (-0.0045, 0),
        "est":       (0,       +0.0045),
        "ouest":     (0,       -0.0045),
        "nord-est":  (+0.0032, +0.0032),
        "sud-ouest": (-0.0032, -0.0032),
    }

    areas = [30, 50, 80, 100, 150]
    prop_types = ["apt", "house"]

    for name, (dlat, dlon) in offsets.items():
        lat = VERSAILLES_LAT + dlat
        lon = VERSAILLES_LON + dlon

        for area in areas:
            for pt in prop_types:
                price = predict_price(lat, lon, area, pt)

                print(
                    f"{name:12s} | "
                    f"{area:3d}m² | "
                    f"{pt:5s} | "
                    f"{price:>10,.0f} €"
                )

    print("------------------------Creteil------------------------")

    CRETEIL_LAT = 48.7845
    CRETEIL_LON = 2.4523

    offsets_creteil = {
        "centre":    (0,       0),
        "nord":      (+0.0045, 0),
        "sud":       (-0.0045, 0),
        "est":       (0,       +0.0045),
        "ouest":     (0,       -0.0045),
        "nord-est":  (+0.0032, +0.0032),
        "sud-ouest": (-0.0032, -0.0032),
    }

    print("\n--- CRÉTEIL ---")

    for name, (dlat, dlon) in offsets_creteil.items():
        lat = CRETEIL_LAT + dlat
        lon = CRETEIL_LON + dlon

        for area in areas:
            for pt in prop_types:
                price = predict_price(lat, lon, area, pt)

                print(
                    f"{name:12s} | "
                    f"{area:3d}m² | "
                    f"{pt:5s} | "
                    f"{price:>10,.0f} €"
                )