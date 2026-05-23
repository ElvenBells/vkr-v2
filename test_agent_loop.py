import os
from playwright.sync_api import sync_playwright
from src.ai_agent.agent import AutoTesterAgent

def test_full_cycle():
    # НОВАЯ ЦЕЛЬ: Взаимодействие с элементами панели администратора
    test_goal = "Введи 'John Doe' в поле поиска (Search users...), а затем кликни по кнопке добавления пользователя (+ Add User)."
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        current_dir = os.getcwd()
        test_site_path = os.path.join(current_dir, "benchmarks", "sites", "admin", "source", "index.html")
        test_url = f"file:///{test_site_path.replace(chr(92), '/')}"
        
        print(f"🌐 Загрузка страницы: {test_url}")
        page.goto(test_url)
        
        agent = AutoTesterAgent(page=page, model_path="models/best.pt")
        # Увеличим количество шагов, так как тут два разных действия
        agent.run(goal=test_goal, max_steps=4) 
        
        page.wait_for_timeout(3000)
        browser.close()

if __name__ == "__main__":
    test_full_cycle()