import os
import shutil
import uuid
import base64
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from dotenv import load_dotenv

from playwright.sync_api import sync_playwright
from openai import OpenAI # Используем стандартный клиент для запроса к LLM

from src.ai_agent.agent_orchestrator import DynamicExperimentOrchestrator

load_dotenv()

app = FastAPI(title="AI-Native QA Dashboard API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TASKS: Dict[str, Dict[str, Any]] = {}
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Инициализируем LLM клиента (подхватит GROQ_API_KEY или OPENAI_API_KEY из .env)
api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
base_url = "https://api.groq.com/openai/v1" if os.environ.get("GROQ_API_KEY") else None
llm_client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

def encode_image(image_path: str) -> str:
    """Конвертирует картинку в Base64 для передачи на фронтенд."""
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def capture_baseline(url: str, path: str):
    """Делает эталонный скриншот, если передан URL, а не файл."""
    logger.info(f"Захват эталона по ссылке: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if not response or not response.ok:
                status = response.status if response else "Unknown"
                raise ValueError(f"Эталонный URL недоступен. Код ответа: {status}")
            page.screenshot(path=path)
        except Exception as e:
            raise ValueError(f"Ошибка загрузки эталонного URL: {str(e)}")
        finally:
            browser.close()

def generate_llm_report(result: dict) -> str:
    """Анализирует сырые метрики и пишет человекочитаемый отчет (Интерпретатор)."""
    if not llm_client:
        return "LLM интерпретатор недоступен (не найден API ключ)."
        
    signals = result.get('signals', {})
    prompt = f"""
    Ты QA-инженер. Я передаю тебе результаты автоматического тестирования веб-интерфейса.
    Вердикт системы: {'ОБНАРУЖЕН ДЕФЕКТ' if result['is_defect'] else 'ТЕСТ ПРОЙДЕН УСПЕШНО'}.
    Уверенность в дефекте: {result['confidence'] * 100:.1f}%

    Вклад нейросетей в сигнал ошибки (от 0 до 1, где 1 - это критическая поломка):
    - Визуальные отклонения (SSIM): {signals.get('ssim', 0):.2f} (цвета, фоны, пиксели)
    - Текстовые искажения (OCR): {signals.get('ocr_sim', 0):.2f} (изменение или пропажа текста)
    - Структура элементов (YOLO): {signals.get('yolo_struct_drift', 0):.2f} (исчезновение или появление новых кнопок/полей)
    - Сдвиг элементов (YOLO BBox): {signals.get('yolo_bbox_shift', 0):.2f} (съехала верстка)

    Напиши краткий отчет (3-4 предложения) для разработчика. Объясни, что именно сломалось, опираясь на метрики.
    Пиши профессиональным, но понятным языком. Без лишних вступлений.
    """
    try:
        response = llm_client.chat.completions.create(
            model="llama-3.3-70b-versatile" if "groq" in (base_url or "") else "gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка LLM интерпретатора: {e}")
        return f"Не удалось сгенерировать интерпретацию: {e}"

def background_test_execution(task_id: str, test_url: str, goal: str, ref_path: str):
    TASKS[task_id]["status"] = "processing"
    try:
        orchestrator = DynamicExperimentOrchestrator(config_path="configs/config.json")
        test_screenshot_path = str(orchestrator.temp_dir / "final_agent_state.png")
        
        result = orchestrator.run_dynamic_test(test_url, goal, ref_path)
        
        # 1. Генерируем AI-отчет
        ai_summary = generate_llm_report(result)
        result["llm_summary"] = ai_summary
        
        # 2. Добавляем картинки в Base64 для UI (Сравнение)
        result["images"] = {
            "baseline": encode_image(ref_path),
            "final": encode_image(test_screenshot_path)
        }
        
        TASKS[task_id]["status"] = "completed"
        TASKS[task_id]["result"] = result
        
    except Exception as e:
        logger.exception(f"[Task {task_id}] Критический сбой выполнения:")
        TASKS[task_id]["status"] = "failed"
        
        # Преобразуем ошибку в строку для семантического анализа текста
        err_msg = str(e)
        
        # 1. Отлавливаем ошибку авторизации API-ключей (Groq / OpenAI / 401)
        if "401" in err_msg or "invalid_api_key" in err_msg or "Invalid API Key" in err_msg:
            readable_error = (
                "Ошибка авторизации внешнего сервиса: Указан недействительный, "
                "неактивный или пустой API-ключ ИИ-провайдера (Invalid API Key) "
                "в файле конфигурации среды .env."
            )
        
        # 2. Отлавливаем ошибку несуществующего или недоступного URL (ERR_NAME_NOT_RESOLVED)
        elif "ERR_NAME_NOT_RESOLVED" in err_msg or "invalid/url" in err_msg or "net::ERR" in err_msg:
            readable_error = (
                "Ошибка сетевой навигации: Указанный целевой URL-адрес не существует в сети, "
                "введен некорректно или удаленный веб-сервер не отвечает (DNS Error / Unreachable)."
            )
        
        # 3. Отлавливаем сбой сети / таймаут соединения с LLM-провайдером
        elif "ConnectTimeout" in err_msg or "Connection error" in err_msg or "api.groq.com" in err_msg:
            readable_error = (
                "Сбой сетевого соединения: Внешний шлюз ИИ-провайдера (API Gateway) "
                "не ответил за установленный интервал времени. Проверьте подключение к Интернету."
            )
            
        # 4. Отлавливаем отсутствие физического файла весов YOLO (best.pt)
        elif "FileNotFoundError" in err_msg or "best.pt" in err_msg or "not found" in err_msg.lower():
            readable_error = (
                "Ошибка инициализации модуля компьютерного зрения (CV): Файл предобученных весов "
                "нейросети (best.pt) не обнаружен в целевой директории models/. "
                "Проверьте наличие артефактов модели."
            )
            
        # Для всех остальных непредвиденных исключений
        else:
            readable_error = f"Системное исключение при выполнении конвейера тестов: {err_msg}"
            
        TASKS[task_id]["error"] = readable_error

@app.post("/api/run-test")
def start_qa_test(  # <-- УБРАЛИ СЛОВО async
    background_tasks: BackgroundTasks,
    test_url: str = Form(...),
    goal: str = Form(...),
    baseline_type: str = Form(...),  # 'file' или 'url'
    ref_url: Optional[str] = Form(None),
    ref_screenshot: Optional[UploadFile] = File(None)
):
    task_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{task_id}_baseline.png")
    
    # Обрабатываем эталон в зависимости от выбора пользователя
    if baseline_type == 'file' and ref_screenshot:
        # Проверка расширения файла (Защита от экстремальных вводов)
        ext = ref_screenshot.filename.split('.')[-1].lower()
        if ext not in ['png', 'jpg', 'jpeg', 'webp']:
            return {"error": f"Формат '{ext}' не поддерживается. Разрешены только PNG, JPG, WebP."}
            
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(ref_screenshot.file, buffer)
            
    elif baseline_type == 'url' and ref_url:
        try:
            capture_baseline(ref_url, file_path) # Playwright безопасно отработает
        except ValueError as e:
            return {"error": str(e)} # Если URL битый, вернем ошибку на фронт сразу
    else:
        return {"error": "Не предоставлен эталон"}

    TASKS[task_id] = {"status": "pending", "result": None, "error": None}
    background_tasks.add_task(
        background_test_execution, task_id=task_id, test_url=test_url, goal=goal, ref_path=file_path
    )
    return {"task_id": task_id}

@app.get("/api/status/{task_id}")
async def get_test_status(task_id: str):
    if task_id not in TASKS:
        return {"error": "Task not found", "status": "unknown"}
    return TASKS[task_id]