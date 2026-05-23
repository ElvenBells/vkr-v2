import { useState, useEffect } from 'react';

export default function App() {
  const [activeTab, setActiveTab] = useState('new_test');
  const [taskId, setTaskId] = useState(null);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col font-sans text-gray-800">
      {/* Навигация */}
      <header className="bg-slate-900 text-white shadow-md">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold flex items-center gap-2">
            🤖 AI QA Agent <span className="text-sm bg-blue-600 px-2 py-0.5 rounded">v2.0</span>
          </h1>
          <nav className="flex gap-4">
            <button onClick={() => setActiveTab('dashboard')} className={`px-3 py-1 rounded ${activeTab === 'dashboard' ? 'bg-slate-700' : 'hover:bg-slate-800'}`}>Dashboard</button>
            <button onClick={() => setActiveTab('new_test')} className={`px-3 py-1 rounded ${activeTab === 'new_test' ? 'bg-slate-700' : 'hover:bg-slate-800'}`}>New Test</button>
            <button onClick={() => setActiveTab('report')} disabled={!taskId} className={`px-3 py-1 rounded ${activeTab === 'report' ? 'bg-slate-700' : 'hover:bg-slate-800'} disabled:opacity-50 disabled:cursor-not-allowed`}>Live Report</button>
          </nav>
        </div>
      </header>

      {/* Основной контент */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8">
        {activeTab === 'dashboard' && <DashboardTab />}
        {activeTab === 'new_test' && <NewTestTab onStartTest={(id) => { setTaskId(id); setActiveTab('report'); }} />}
        {activeTab === 'report' && <LiveReportTab taskId={taskId} />}
      </main>
    </div>
  );
}

// --- Вкладка 1: Dashboard ---
function DashboardTab() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6 border-b pb-2">Последние запуски</h2>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="text-left py-3 px-4 font-semibold text-gray-600">ID Теста</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-600">Цель (Goal)</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-600">F1-Score</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-600">Статус</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b hover:bg-gray-50">
              <td className="py-3 px-4 font-mono text-sm">#QA-882</td>
              <td className="py-3 px-4">Добавить пользователя в CRM</td>
              <td className="py-3 px-4">0.941</td>
              <td className="py-3 px-4"><span className="bg-red-100 text-red-800 px-2 py-1 rounded text-sm">Defect Found</span></td>
            </tr>
            <tr className="hover:bg-gray-50">
              <td className="py-3 px-4 font-mono text-sm">#QA-881</td>
              <td className="py-3 px-4">Проверка корзины</td>
              <td className="py-3 px-4">1.000</td>
              <td className="py-3 px-4"><span className="bg-green-100 text-green-800 px-2 py-1 rounded text-sm">Clean</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// --- Вкладка 2: Настройка нового теста ---
function NewTestTab({ onStartTest }) {
  const [url, setUrl] = useState('http://localhost:3000');
  const [goal, setGoal] = useState('Нажми на кнопку "Создать" и введи тестовые данные');

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Имитация отправки на FastAPI (замени на реальный fetch к /api/run-test)
    console.log("Starting test for:", url, goal);
    const mockTaskId = "task_" + Math.random().toString(36).substr(2, 9);
    onStartTest(mockTaskId);
  };

  return (
    <div className="max-w-2xl mx-auto bg-white p-8 rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-6">Конфигурация теста</h2>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Target URL</label>
          <input 
            type="url" required value={url} onChange={(e) => setUrl(e.target.value)}
            className="w-full border border-gray-300 rounded p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none" 
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">LLM Goal (Цель агента)</label>
          <textarea 
            required rows="3" value={goal} onChange={(e) => setGoal(e.target.value)}
            className="w-full border border-gray-300 rounded p-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
            placeholder="Опишите, что агент должен сделать на странице..."
          ></textarea>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Глубина тестирования</label>
            <input type="number" defaultValue={10} className="w-full border border-gray-300 rounded p-2" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Режим работы</label>
            <select className="w-full border border-gray-300 rounded p-2 bg-white">
              <option>Dynamic (ReAct + YOLO)</option>
              <option>Visual Only (SSIM)</option>
            </select>
          </div>
        </div>
        <button type="submit" className="w-full bg-blue-600 text-white font-bold py-3 rounded hover:bg-blue-700 transition">
          Запустить агента
        </button>
      </form>
    </div>
  );
}

// --- Вкладка 3: Мониторинг выполнения (Live) ---
function LiveReportTab({ taskId }) {
  const [logs, setLogs] = useState(["Инициализация браузера...", "Переход по URL..."]);
  
  // Здесь в будущем будет useEffect с setInterval для опроса FastAPI /api/status/{taskId}
  // или подключение по WebSocket

  return (
    <div className="grid grid-cols-3 gap-6 h-[80vh]">
      {/* Левая колонка: Логи агента */}
      <div className="col-span-1 bg-gray-900 text-green-400 rounded-lg shadow p-4 font-mono text-sm overflow-y-auto flex flex-col">
        <h3 className="text-white text-lg font-bold mb-4 border-b border-gray-700 pb-2">💡 Логика ИИ (Task: {taskId})</h3>
        <div className="space-y-2 flex-1">
          {logs.map((log, i) => (
            <div key={i}>&gt; {log}</div>
          ))}
          <div className="animate-pulse">&gt; Ожидание ответа от LLM_Client...</div>
        </div>
      </div>

      {/* Правая колонка: Визуал (Предпросмотр / Диффы) */}
      <div className="col-span-2 bg-white rounded-lg shadow flex flex-col overflow-hidden">
        <div className="bg-gray-100 px-4 py-3 border-b flex justify-between items-center">
          <span className="font-semibold">Текущее состояние браузера</span>
          <span className="text-sm bg-yellow-200 text-yellow-800 px-2 py-1 rounded animate-pulse">In Progress</span>
        </div>
        <div className="flex-1 bg-gray-200 flex items-center justify-center p-4">
          <div className="text-center text-gray-500">
            <svg className="w-16 h-16 mx-auto mb-4 text-gray-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p>Трансляция UI через State Builder...</p>
          </div>
        </div>
      </div>
    </div>
  );
}