from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
from .models import TestSetupRequest, TaskResponse
from .worker import run_qa_agent_task, celery_app

app = FastAPI(title="AI QA Agent API")

# Настройка CORS для общения с локальным фронтендом (React обычно на порту 3000 или 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Для продакшена заменить на точные URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/run-test", response_model=TaskResponse)
async def start_test(request: TestSetupRequest):
    # Конвертируем Pydantic модель в dict для передачи в Celery
    task = run_qa_agent_task.delay(request.model_dump())
    return {"task_id": task.id, "status": "Task submitted to queue"}

@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    response = {
        "task_id": task_id,
        "status": task_result.status,
    }
    
    if task_result.status == 'SUCCESS':
        response["result"] = task_result.result
    elif task_result.status == 'PROGRESS':
        response["meta"] = task_result.info # Промежуточные логи
    elif task_result.status == 'FAILURE':
        response["error"] = str(task_result.info)
        
    return response