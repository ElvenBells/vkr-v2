import os
import json
# Импортируем правильное имя класса
from src.cv_core.yolo_inference import YOLOInferenceEngine 

class StateBuilder:
    def __init__(self, model_path="models/best.pt"):
        # Создаем конфигурацию, которую требует ваш YOLOInferenceEngine.
        # ВАЖНО: Если у вас другие названия классов в модели, обновите список "classes"
        config = {
            "paths": {
                "yolo_model": model_path
            },
            "yolo": {
                "classes": ['backgroundimage', 'button', 'checkbox', 'icon', 'iframe', 'image', 'input', 'link', 'map', 'multitab', 'pageindicator', 'panel', 'spinner', 'switch', 'text', 'textbutton', 'toolbar', 'uppertaskbar'], # пример базовых UI-классов
                "conf_threshold": 0.25,
                "iou_threshold": 0.45,
                "imgsz": 640,
                "device": "cpu"
            }
        }
        self.detector = YOLOInferenceEngine(config)
        self.temp_dir = "temp_screenshots"
        os.makedirs(self.temp_dir, exist_ok=True)
        
    def get_state(self, page) -> str:
        """
        Делает скриншот страницы Playwright, прогоняет через YOLO и возвращает JSON.
        """
        screenshot_path = os.path.join(self.temp_dir, "current_state.png")
        
        # 1. Делаем скриншот текущего состояния страницы
        page.screenshot(path=screenshot_path)
        
        # 2. Получаем объект StructuralFeatures от вашей модели YOLO
        structural_features = self.detector.predict(screenshot_path) 
        
        # 3. Формируем JSON-представление для LLM
        elements = []
        # Итерируемся по списку объектов Detection
        for i, det in enumerate(structural_features.detections):
            
            # Используем готовый метод вашего класса Detection для получения центра
            center_x, center_y = det.center()
            
            elements.append({
                "id": i + 1,
                "class": det.class_name, # Обращаемся как к атрибуту объекта, а не словарю
                "center_x": int(center_x),
                "center_y": int(center_y)
            })
            
        state_dict = {
            "screen_resolution": {"width": page.viewport_size['width'], "height": page.viewport_size['height']},
            "elements": elements
        }
        
        return json.dumps(state_dict, ensure_ascii=False, indent=2)