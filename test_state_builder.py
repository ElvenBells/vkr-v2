import os
from playwright.sync_api import sync_playwright
from src.ai_agent.state_builder import StateBuilder

def run_state_test():
    print("🔧 Инициализация YOLO и State Builder...")
    # Укажите правильный путь до вашей обученной модели (best.pt)
    builder = StateBuilder(model_path="models/best.pt")
    
    with sync_playwright() as p:
        # headless=False позволяет нам видеть, что происходит на экране
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        
        # Получаем абсолютный путь к одному из ваших тестовых сайтов в репозитории
        current_dir = os.getcwd()
        test_site_path = os.path.join(current_dir, "benchmarks", "sites", "admin", "source", "index.html")
        test_url = f"file:///{test_site_path.replace(chr(92), '/')}"
        
        print(f"🌐 Открываем локальную страницу: {test_url}")
        page.goto(test_url)
        
        print("📸 Делаем скриншот и анализируем UI через YOLO...")
        state_json = builder.get_state(page)
        
        print("\n✅ Текущее состояние экрана глазами YOLO:")
        print(state_json)
        
        browser.close()

if __name__ == "__main__":
    run_state_test()