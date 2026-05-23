import time

class PlaywrightExecutor:
    def __init__(self, page):
        self.page = page

    def execute(self, action_data: dict) -> bool:
        action = action_data.get("action")
        x = action_data.get("x")
        y = action_data.get("y")

        if action == "click":
            print(f"🖱️ Выполняю КЛИК по координатам (x:{x}, y:{y})")
            if x is not None and y is not None:
                self.page.mouse.click(x, y)
                time.sleep(1) # Небольшая пауза, чтобы UI успел отреагировать (анимации, загрузка)
                return True
                
        elif action == "type":
            value = action_data.get("value", "")
            print(f"⌨️ Выполняю ВВОД ТЕКСТА '{value}' по координатам (x:{x}, y:{y})")
            if x is not None and y is not None:
                # Кликаем в поле, чтобы установить фокус, затем печатаем
                self.page.mouse.click(x, y)
                self.page.keyboard.type(value, delay=50) # delay имитирует реального человека
                time.sleep(1)
                return True
                
        elif action == "done":
            print("🏁 Агент сообщил об успешном выполнении задачи!")
            return True
            
        print(f"❌ Ошибка: Неизвестное действие или отсутствуют координаты: {action_data}")
        return False