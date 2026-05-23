import json
from src.ai_agent.state_builder import StateBuilder
from src.ai_agent.llm_client import AIVisionAgent
from src.ai_agent.executor import PlaywrightExecutor

class AutoTesterAgent:
    def __init__(self, page, model_path="models/best.pt"):
        self.page = page
        self.state_builder = StateBuilder(model_path=model_path)
        self.llm = AIVisionAgent()
        self.executor = PlaywrightExecutor(page)

    def run(self, goal: str, max_steps: int = 5):
        print(f"\n🚀 ЗАПУСК АГЕНТА. Цель: '{goal}'")
        
        # Инициализируем память агента
        history = []

        for step in range(1, max_steps + 1):
            print(f"\n--- Шаг {step} из {max_steps} ---")

            print("📸 Анализирую экран...")
            state_json = self.state_builder.get_state(self.page)

            print("🧠 Принимаю решение (с учетом памяти)...")
            # Передаем историю в LLM
            history_str = json.dumps(history, ensure_ascii=False)
            llm_response_str = self.llm.get_action(goal, state_json, history_str)
            
            try:
                action_data = json.loads(llm_response_str)
            except json.JSONDecodeError:
                print(f"❌ Ошибка парсинга ответа от LLM: {llm_response_str}")
                break

            print(f"💡 Логика ИИ: {action_data.get('reasoning')}")

            if action_data.get("action") == "done":
                print("🏁 Агент решил, что цель успешно достигнута!")
                break

            success = self.executor.execute(action_data)
            if not success:
                print("🛑 Выполнение прервано из-за ошибки действия.")
                break
                
            # Если действие успешно выполнено, записываем его в память
            # Мы сохраняем тип действия и введенное значение, чтобы агент помнил суть
            action_summary = {
                "step": step,
                "action": action_data.get("action"),
                "element_id": action_data.get("element_id"),
                "value": action_data.get("value")
            }
            history.append(action_summary)

        print("✅ Работа агента завершена.")