# main.py - Упрощенная версия
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import pickle
import pandas as pd
import logging
import time
from contextlib import asynccontextmanager
import uvicorn
from sklearn.preprocessing import OrdinalEncoder
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
from fastapi import Response

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('car_price_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== PROMETHEUS МЕТРИКИ ==========
# Очищаем registry при старте (избегаем дублирования при перезагрузках)
for collector in list(REGISTRY._collector_to_names.keys()):
    try:
        REGISTRY.unregister(collector)
    except:
        pass

# Счетчик предсказаний по маркам автомобилей
PREDICTIONS_TOTAL = Counter(
    'car_predictions_total', 
    'Total predictions by make',
    ['make']
)

# Гистограмма времени выполнения предсказаний
PREDICTION_DURATION = Histogram(
    'car_prediction_duration_seconds', 
    'Time for car price prediction'
)

# ========== ЗАГРУЗКА МОДЕЛЕЙ ==========
try:
    with open("cars.joblib", "rb") as f:
        model = pickle.load(f)
    logger.info("✅ Model loaded successfully")
except Exception as e:
    logger.error(f"❌ Error loading model: {e}")
    raise

try:
    with open("power.joblib", "rb") as file:
        predict2price = pickle.load(file)
    logger.info("✅ Power transformer loaded successfully")
except Exception as e:
    logger.error(f"❌ Error loading power transformer: {e}")
    raise

# ========== ПРЕДОБРАБОТКА ДАННЫХ ==========
ordinal_encoder = None

def fit_encoder():
    """Инициализация энкодера"""
    global ordinal_encoder
    cat_columns = ['Make', 'Model', 'Style', 'Fuel_type', 'Transmission']
    sample_df = pd.DataFrame({
        'Make': ['Toyota'], 'Model': ['Camry'], 'Style': ['Sedan'],
        'Fuel_type': ['Petrol'], 'Transmission': ['Automatic']
    })
    ordinal_encoder = OrdinalEncoder()
    ordinal_encoder.fit(sample_df[cat_columns])
    logger.info("✅ Ordinal encoder fitted")

def clear_data(df):
    """Очистка и кодирование категориальных признаков"""
    global ordinal_encoder
    cat_columns = ['Make', 'Model', 'Style', 'Fuel_type', 'Transmission']
    
    if ordinal_encoder is None:
        fit_encoder()
    
    Ordinal_encoded = ordinal_encoder.transform(df[cat_columns])
    df_ordinal = pd.DataFrame(Ordinal_encoded, columns=cat_columns)
    df[cat_columns] = df_ordinal[cat_columns]
    return df

def featurize(dframe):
    """Генерация новых признаков"""
    dframe['Distance_by_year'] = dframe['Distance'] / (2022 - dframe['Year'])
    dframe['age'] = 2024 - dframe['Year']
    
    mean_engine_cap = dframe.groupby('Style')['Engine_capacity'].mean()
    dframe['eng_cap_diff'] = dframe.apply(
        lambda x: abs(x['Engine_capacity'] - mean_engine_cap[x['Style']]), 
        axis=1
    )
    
    max_engine_cap = dframe.groupby('Style')['Engine_capacity'].max()
    dframe['eng_cap_diff_max'] = dframe.apply(
        lambda x: abs(x['Engine_capacity'] - max_engine_cap[x['Style']]), 
        axis=1
    )
    
    return dframe

# ========== FASTAPI ПРИЛОЖЕНИЕ ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("🚀 Starting Car Price Prediction Service")
    yield
    logger.info("🛑 Shutting down Car Price Prediction Service")

app = FastAPI(
    title="Car Price Prediction API",
    description="MLOps эксплуатация модели: мониторинг, логирование, метрики",
    version="1.0.0",
    lifespan=lifespan
)

# Автоматические метрики FastAPI (количество запросов, коды ответов)
instrumentator = Instrumentator(
    excluded_handlers=["/metrics", "/health", "/"]
)
instrumentator.instrument(app).expose(app, endpoint="/metrics")

# ========== PYDANTIC МОДЕЛИ ==========
class CarFeatures(BaseModel):
    make: str = Field(..., example="Toyota", description="Марка автомобиля")
    model: str = Field(..., example="Camry", description="Модель")
    year: int = Field(..., ge=1990, le=2024, example=2020, description="Год выпуска")
    style: str = Field(..., example="Sedan", description="Тип кузова")
    distance: float = Field(..., ge=0, example=50000, description="Пробег (км)")
    engine_capacity: float = Field(..., ge=500, le=8000, example=2000, description="Объем двигателя (см³)")
    fuel_type: str = Field(..., example="Petrol", description="Тип топлива")
    transmission: str = Field(..., example="Automatic", description="Трансмиссия")

class PredictionResponse(BaseModel):
    predicted_price: float
    processing_time_ms: float

# ========== ЭНДПОИНТЫ ==========
@app.get("/", tags=["Health"])
async def root():
    """Корневой эндпоинт для проверки работы сервиса"""
    return {
        "service": "Car Price Prediction",
        "status": "running"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check для систем мониторинга"""
    return {"status": "healthy"}

@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict(car: CarFeatures):
    """Предсказывает стоимость автомобиля с метриками производительности"""
    start_time = time.time()
    
    try:
        logger.info(f"📥 Prediction request: {car.make} {car.model}, year={car.year}")
        
        # Подготовка данных
        columns_names = ["Make", "Model", "Year", "Style", "Distance", "Engine_capacity", "Fuel_type", "Transmission"]
        input_data = pd.DataFrame([car.dict()])
        input_data.columns = columns_names
        
        # Обработка и генерация признаков
        cleaned_df = clear_data(input_data)
        featurized_df = featurize(cleaned_df)
        
        # Предсказание (измеряем время с помощью гистограммы Prometheus)
        with PREDICTION_DURATION.time():
            predict_val = model.predict(featurized_df)[0]
            price = predict2price.inverse_transform(predict_val.reshape(-1, 1))
        
        # Увеличиваем счетчик предсказаний для данной марки
        PREDICTIONS_TOTAL.labels(make=car.make).inc()
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"✅ Prediction: {car.make} {car.model} -> {round(float(price[0]), 2)}€, time={processing_time:.2f}ms")
        
        return PredictionResponse(
            predicted_price=round(float(price[0]), 2),
            processing_time_ms=round(processing_time, 2)
        )
        
    except Exception as e:
        logger.error(f"❌ Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        reload=False,  # False для production, чтобы избежать проблем с метриками
        log_level="info"
    )