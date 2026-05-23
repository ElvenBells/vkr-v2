from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import uuid

# --- Модели данных ---
class TestSetupRequest(BaseModel):
    url: str
    goal: str
    max_steps: int = 10
    mode: str = "dynamic"

# --- Инициализация ---
app = FastAPI(title="AI QA Agent Backend")

# Разрешаем запросы с React-фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Адрес твоего Vite-сервера
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Эндпоинты ---
@app.get("/")
async def root():
    return {"message": "AI QA Backend is running"}

@app.post("/api/run-test")
async def start_test(request: TestSetupRequest):
    # Здесь в будущем будет вызов Celery task: task = run_qa_agent_task.delay(request.dict())
    print(f"Запуск теста на {request.url} с целью: {request.goal}")
    
    # Имитация создания задачи
    task_id = str(uuid.uuid4())
    return {"task_id": task_id, "status": "Task submitted"}

@app.get("/api/status/{task_id}")
async def get_status(task_id: str):
    # Здесь будет проверка состояния задачи в Redis
    return {
        "task_id": task_id,
        "status": "in_progress",
        "current_log": "Агент анализирует DOM-структуру..."
    }

# --- Запуск ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)