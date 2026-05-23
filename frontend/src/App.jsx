import { useState } from 'react';

function App() {
  const [activeTab, setActiveTab] = useState('new_test');

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <nav className="mb-8 flex gap-4">
        <button onClick={() => setActiveTab('new_test')} className="px-4 py-2 bg-blue-600 text-white rounded">Новый тест</button>
        <button onClick={() => setActiveTab('dashboard')} className="px-4 py-2 bg-gray-600 text-white rounded">Дашборд</button>
      </nav>

      {activeTab === 'new_test' ? (
        <div className="bg-white p-6 rounded shadow">
          <h2 className="text-xl font-bold mb-4">Настройка запуска</h2>
          <input id="urlInput" placeholder="URL сайта" className="border p-2 w-full mb-4" />
          <textarea id="goalInput" placeholder="Цель агента (например: 'Добавь товар в корзину')" className="border p-2 w-full mb-4"></textarea>
          <button 
            onClick={() => {
              const url = document.getElementById('urlInput').value;
              const goal = document.getElementById('goalInput').value;
              fetch("http://localhost:8000/api/run-test", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url, goal })
              }).then(res => res.json()).then(data => alert("Тест запущен: " + data.task_id));
            }}
            className="bg-green-600 text-white px-6 py-2 rounded"
          >
            Запустить ИИ-агента
          </button>
        </div>
      ) : (
        <div className="bg-white p-6 rounded shadow">
          <h2 className="text-xl font-bold">История тестов</h2>
          <p>Здесь будут результаты ваших прогонов...</p>
        </div>
      )}
    </div>
  );
}

export default App;