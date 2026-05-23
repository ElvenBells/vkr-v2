import json
from src.ai_agent.llm_client import AIVisionAgent

def run_spatial_test():
    # 1. Симуляция JSON, который будет генерировать ваш future State Builder (YOLO + OCR)
    mock_yolo_detections = {
        "screen_resolution": {"width": 1920, "height": 1080},
        "elements": [
            {"id": 1, "class": "input_field", "text": "Username", "center_x": 960, "center_y": 400},
            {"id": 2, "class": "input_field", "text": "Password", "center_x": 960, "center_y": 500},
            {"id": 3, "class": "button", "text": "Login", "center_x": 960, "center_y": 600},
            {"id": 4, "class": "link", "text": "Forgot password?", "center_x": 960, "center_y": 650}
        ]
    }
    
    # 2. Инициализация нашего агента
    agent = AIVisionAgent() # Не забудьте установить GROQ_API_KEY в терминале перед запуском
    
    # 3. Задаем цель агенту
    target_goal = "Мне нужно войти в систему. Нажми на кнопку авторизации."
    
    print(f"🎯 Цель: {target_goal}")
    print("🧠 Агент думает...\n")
    
    # 4. Получаем ответ
    state_json_str = json.dumps(mock_yolo_detections, ensure_ascii=False, indent=2)
    result_json_str = agent.get_action(goal=target_goal, screen_state_json=state_json_str)
    
    # 5. Парсинг и вывод результата
    result = json.loads(result_json_str)
    
    print("✅ Ответ от LLM:")
    print(json.dumps(result, indent=4, ensure_ascii=False))
    
    if result.get("action") == "click" and result.get("element_id") == 3:
        print("\n🎉 УСПЕХ: Агент правильно определил координаты кнопки 'Login'!")
    else:
        print("\n❌ ОШИБКА: Агент выбрал не тот элемент.")

if __name__ == "__main__":
    run_spatial_test()