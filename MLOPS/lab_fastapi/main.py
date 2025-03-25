from fastapi import FastAPI
from pydantic import BaseModel
import pickle
import pandas as pd
import logging
from typing import List, Optional
import uvicorn
from sklearn.preprocessing import StandardScaler, OrdinalEncoder


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка модели (замените путь на свой)
try:
    with open("cars.joblib", "rb") as f:
        model = pickle.load(f)
    logger.info("Model loaded successfully")

except Exception as e:
    logger.error(f"Error loading model: {e}")
    # raise

with open("power.joblib", 'rb') as file:
    predict2price = pickle.load(file)


app = FastAPI(title="Car Price")


def clear_data(df):
    cat_columns = ['Make', 'Model', 'Style', 'Fuel_type', 'Transmission']
    num_columns = ['Year', 'Distance', 'Engine_capacity(cm3)', 'Price(euro)']
    ordinal = OrdinalEncoder()
    ordinal.fit(df[cat_columns])
    Ordinal_encoded = ordinal.transform(df[cat_columns])
    df_ordinal = pd.DataFrame(Ordinal_encoded, columns=cat_columns)
    df[cat_columns] = df_ordinal[cat_columns]
    return df

def featurize(dframe):
    """
        Генерация новых признаков
    """
    dframe['Distance_by_year'] = dframe['Distance']/(2022 - dframe['Year'])
    dframe['age'] = 2024 - dframe['Year']
    mean_engine_cap = dframe.groupby('Style')['Engine_capacity'].mean()
    dframe['eng_cap_diff'] = dframe.apply(lambda row: abs(row['Engine_capacity'] - mean_engine_cap[row['Style']]), axis=1)

    max_engine_cap = dframe.groupby('Style')['Engine_capacity'].max()
    dframe['eng_cap_diff_max'] = dframe.apply(lambda row: abs(row['Engine_capacity'] - max_engine_cap[row['Style']]), axis=1)
    return dframe

# Модель входных данных
class CarFeatures(BaseModel):
    make: str
    model: str
    year: int
    style: str
    distance: float
    engine_capacity: float
    fuel_type: str
    transmission: str
    # distanse_by_year: str
    # age: str
    # eng_cap_diff: str
    # eng_cap_diff_max: str

@app.post("/predict", summary="Predict car price")
async def predict(car: CarFeatures):
    """
    Предсказывает стоимость автомобиля
    """
    try:
        columns_names = ["Make", "Model", "Year", "Style","Distance", "Engine_capacity", "Fuel_type", "Transmission",]
        input_data = pd.DataFrame([car.dict()])
        input_data.columns = columns_names
        featurize_df = featurize(clear_data(input_data))
        print(featurize_df)
        predict = model.predict(featurize_df)[0]
        price = predict2price.inverse_transform(predict.reshape(-1,1))
        # logger.info(f"Predicted price: {price}")
        
        return {"predicted_price": round(float(price), 2)}
    
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return {"error": str(e)}
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)