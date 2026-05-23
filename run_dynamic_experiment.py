import os
from pathlib import Path
from src.ai_agent.agent_orchestrator import DynamicExperimentOrchestrator

def main():
    # Инициализируем наш новый оркестратор
    orchestrator = DynamicExperimentOrchestrator(config_path="configs/config.json")
    
    current_dir = os.getcwd()
    
    # Сценарий: Тестируем дефектную страницу (broken_interaction)
    # Кнопка добавления сломана (ничего не происходит после клика)
    test_html_path = os.path.join(current_dir, "benchmarks", "sites", "admin", "screenshots", "defected", "broken_interaction.html")
    test_url = f"file:///{test_html_path.replace(chr(92), '/')}"
    
    # Эталонный скриншот (baseline), как ДОЛЖНА выглядеть страница. 
    # В идеале, здесь должен быть скриншот состояния ПОСЛЕ успешного добавления пользователя, 
    # но пока используем ваш baseline.png
    ref_screenshot = os.path.join(current_dir, "benchmarks", "sites", "admin", "screenshots", "reference", "baseline.png")
    
    goal = "Введи 'John Doe' в поле поиска, а затем кликни по кнопке добавления пользователя (+ Add User)."
    
    print("\n" + "="*50)
    print("🚀 ЗАПУСК ДИНАМИЧЕСКОГО ИИ-ТЕСТИРОВАНИЯ")
    print("="*50)
    
    result = orchestrator.run_dynamic_test(
        test_url=test_url, 
        goal=goal, 
        ref_screenshot_path=ref_screenshot
    )
    
    print("\n" + "="*50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ СИСТЕМЫ")
    print("="*50)
    print(f"Обнаружен ли баг (Defect): {'✅ ДА (Тест упал)' if result['is_defect'] else '❌ НЕТ (Тест пройден)'}")
    print(f"Уверенность агрегатора:    {result['confidence']:.4f}")
    print(f"Время выполнения сценария: {result['time_s']} сек.")
    print("Вклад метрик (Signals):")
    for k, v in result['signals'].items():
        print(f"  - {k}: {v:.4f}")
    print("="*50)

if __name__ == "__main__":
    main()