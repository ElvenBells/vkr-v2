import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

class AIVisionAgent:
    def __init__(self, model_name="llama-3.1-8b-instant", temperature=0.1):
        api_key = os.getenv("GROQ_API_KEY", "your_groq_api_key")
        base_url = "https://api.groq.com/openai/v1" 
        
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_key=api_key,
            openai_api_base=base_url,
            model_kwargs={"response_format": {"type": "json_object"}}
        )

    def get_action(self, goal: str, screen_state_json: str, history: str = "[]") -> str:
        prompt = PromptTemplate(
            input_variables=["goal", "screen_state", "history"],
            template="""
                    Ты — ИИ-агент для автоматизированного тестирования веб-интерфейсов. 
                    Твоя текущая цель: {goal}
                    
                    История твоих ПРЕДЫДУЩИХ действий (чтобы не повторяться):
                    {history}
                    
                    Текущее состояние экрана (от YOLO) в формате JSON:
                    {screen_state}
                    
                    Проанализируй элементы и историю. Реши, какое ОДНО следующее действие нужно сделать.
                    ВАЖНО: Если ты видишь по истории, что все требуемые в цели действия УЖЕ были выполнены (например, текст введен и нужная кнопка нажата), ты ОБЯЗАН завершить работу, даже если визуально на экране ничего не поменялось. Не зацикливайся!
                    
                    Верни строго JSON в одном из трех форматов:
                    1. Клик: {{"action": "click", "x": координата_X, "y": координата_Y, "element_id": ID, "reasoning": "почему"}}
                    2. Ввод текста: {{"action": "type", "x": координата_X, "y": координата_Y, "element_id": ID, "value": "текст", "reasoning": "почему"}}
                    3. Завершение: {{"action": "done", "reasoning": "все шаги из цели выполнены"}}
                    """
        )
        
        chain = prompt | self.llm
        response = chain.invoke({"goal": goal, "screen_state": screen_state_json, "history": history})
        
        return response.content