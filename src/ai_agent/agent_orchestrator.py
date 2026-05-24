import os
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from loguru import logger

# Импортируем вашего Агента
from src.ai_agent.agent import AutoTesterAgent

# Импортируем ядро вашей системы (из вашего текущего orchestrator.py)
from src.cv_core.yolo_inference import YOLOInferenceEngine
from src.visual_oracle import VisualOracle
from src.ocr_engine import OCREngine
from src.hybrid_aggregator import HybridAggregator

class DynamicExperimentOrchestrator:
    def __init__(self, config_path: str = "configs/config.json"):
        # Инициализируем ваши CV/OCR модули по текущему конфигу
        with open(config_path, "r", encoding="utf-8") as f:
            self.cfg = json.load(f)
            
        logger.info("🔧 Инициализация Гибридного Агрегатора и Оракула...")
        self.yolo = YOLOInferenceEngine(self.cfg)
        self.oracle = VisualOracle(self.cfg)
        self.ocr = OCREngine(self.cfg)
        self.agg = HybridAggregator(self.cfg)
        
        self.temp_dir = Path("temp_screenshots")
        self.temp_dir.mkdir(exist_ok=True)

    def run_dynamic_test(self, test_url: str, goal: str, ref_screenshot_path: str) -> dict:
        """
        Запускает Агента на странице, а затем прогоняет результат через Агрегатор.
        """
        start_time = time.time()
        test_screenshot_path = str(self.temp_dir / "final_agent_state.png")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=300)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            
            logger.info(f"🌐 Агент переходит на: {test_url}")
            
            # БЛОК ЭКСТРЕМАЛЬНОГО ТЕСТИРОВАНИЯ: Проверка валидности URL
            try:
                response = page.goto(test_url, wait_until="domcontentloaded", timeout=30000)
                # Если ответ пустой или статус >= 400 (например, 404 Not Found)
                if not response or not response.ok:
                    status_code = response.status if response else "Unknown"
                    raise ValueError(f"Сайт вернул ошибку {status_code}. Невозможно продолжить тестирование.")
            except Exception as e:
                logger.error(f"Ошибка навигации Playwright: {e}")
                raise ValueError(f"Целевой URL недоступен. Детали: {str(e)}")
            
            # 1. ЗАПУСК АГЕНТА (Сценарная часть)
            agent = AutoTesterAgent(page=page, model_path=self.cfg["paths"].get("yolo_model", "models/best.pt"))
            logger.info(f"🤖 Агент начинает выполнение цели: '{goal}'")
            agent.run(goal=goal, max_steps=3)
            
            # 2. ФИКСАЦИЯ РЕЗУЛЬТАТА
            # После работы агента делаем финальный скриншот для визуального оракула
            page.screenshot(path=test_screenshot_path)
            browser.close()
            
        # 3. ВИЗУАЛЬНАЯ ПРОВЕРКА (CV часть - ваш существующий код)
        logger.info("👁️ Агент закончил. Передаю результат Визуальному Оракулу...")
        
        yolo_ref = self.yolo.predict(ref_screenshot_path)
        yolo_test = self.yolo.predict(test_screenshot_path)
        
        oracle_res = self.oracle.compare(ref_screenshot_path, test_screenshot_path)
        
        ocr_ref = self.ocr.extract_from_image(ref_screenshot_path)
        ocr_test = self.ocr.extract_from_image(test_screenshot_path)
        
        if ocr_ref.full_text and ocr_test.full_text:
            ocr_test.similarity_score = self.ocr.calculate_similarity(ocr_ref.full_text, ocr_test.full_text)
        else:
            ocr_test.similarity_score = 1.0 if not ocr_ref.full_text and not ocr_test.full_text else 0.0
            
        # Ваш математический агрегатор выносит вердикт
        agg_res = self.agg.aggregate_signals(oracle_res, ocr_test, yolo_test, yolo_ref)
        
        elapsed = time.time() - start_time
        logger.info(f"⚖️ Вердикт Оракула | Defect: {agg_res.is_defect} | Уверенность: {agg_res.final_confidence:.4f}")
        
        return {
            "time_s": round(elapsed, 3),
            "confidence": agg_res.final_confidence,
            "is_defect": agg_res.is_defect,
            "signals": agg_res.signal_contributions
        }