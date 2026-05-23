import React, { useState, useEffect } from 'react';
import axios from 'axios';
import html2pdf from 'html2pdf.js';
import { Play, CheckCircle, XCircle, Loader2, LayoutDashboard, Download, Link, Bot, FileText, Image as ImageIcon } from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8001/api';

// --- КОМПОНЕНТ ИНТЕРАКТИВНОГО СРАВНЕНИЯ ИЗОБРАЖЕНИЙ ---
function ImageComparison({ baseline, final }) {
  const [position, setPosition] = useState(50);

  return (
    <div className="relative w-full aspect-video rounded-xl overflow-hidden border border-slate-300 bg-slate-200 shadow-inner select-none group">
      {/* ОЖИДАЛОСЬ (Слой снизу, виден слева) */}
      <img
        src={`data:image/png;base64,${baseline}`}
        alt="Baseline"
        className="absolute inset-0 w-full h-full object-contain pointer-events-none bg-white"
      />

      {/* ПОЛУЧЕНО (Слой сверху, обрезанный ползунком, виден справа) */}
      <img
        src={`data:image/png;base64,${final}`}
        alt="Final"
        className="absolute inset-0 w-full h-full object-contain pointer-events-none bg-white"
        style={{ clipPath: `inset(0 0 0 ${position}%)` }}
      />

      {/* Невидимый инпут для управления мышью */}
      <input
        type="range"
        min="0"
        max="100"
        value={position}
        onChange={(e) => setPosition(e.target.value)}
        className="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-20 m-0"
      />

      {/* Визуальный разделитель (линия и кружок) */}
      <div
        className="absolute top-0 bottom-0 w-1 bg-blue-500 shadow-[0_0_10px_rgba(0,0,0,0.5)] z-10 pointer-events-none flex items-center justify-center transition-all duration-75"
        style={{ left: `${position}%`, transform: 'translateX(-50%)' }}
      >
        <div className="w-10 h-10 bg-white border-4 border-blue-500 rounded-full flex items-center justify-center shadow-xl">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="text-blue-500">
            <path d="M18 8l4 4-4 4M6 16l-4-4 4-4" />
          </svg>
        </div>
      </div>
      
      {/* Плашки с подписями */}
      <div className="absolute top-6 left-6 bg-slate-900/80 text-white px-4 py-2 rounded-lg text-sm font-bold z-10 pointer-events-none backdrop-blur-md border border-slate-700 shadow-lg transition-opacity">
        ОЖИДАЛОСЬ (Эталон)
      </div>
      <div className="absolute top-6 right-6 bg-blue-600/90 text-white px-4 py-2 rounded-lg text-sm font-bold z-10 pointer-events-none backdrop-blur-md shadow-lg border border-blue-500 transition-opacity">
        ПОЛУЧЕНО (Агент)
      </div>
    </div>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState('new_test');
  
  const [url, setUrl] = useState('');
  const [goal, setGoal] = useState('');
  const [baselineType, setBaselineType] = useState('file');
  const [baselineFile, setBaselineFile] = useState(null);
  const [baselineUrl, setBaselineUrl] = useState('');
  
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let intervalId;
    if (taskId && (status === 'pending' || status === 'processing')) {
      intervalId = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/status/${taskId}`);
          const data = response.data;
          setStatus(data.status);
          
          if (data.status === 'completed') {
            setResult(data.result);
            setActiveTab('report');
            clearInterval(intervalId);
          } else if (data.status === 'failed') {
            setError(data.error);
            clearInterval(intervalId);
          }
        } catch (err) {
          console.error("Ошибка при опросе:", err);
        }
      }, 3000);
    }
    return () => clearInterval(intervalId);
  }, [taskId, status]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('test_url', url);
    formData.append('goal', goal);
    formData.append('baseline_type', baselineType);
    
    if (baselineType === 'file' && baselineFile) {
      formData.append('ref_screenshot', baselineFile);
    } else if (baselineType === 'url' && baselineUrl) {
      formData.append('ref_url', baselineUrl);
    } else {
      alert("Пожалуйста, укажите эталон (файл или ссылку)");
      return;
    }

    try {
      setStatus('pending'); setResult(null); setError(null);
      const response = await axios.post(`${API_BASE_URL}/run-test`, formData);
      setTaskId(response.data.task_id);
    } catch (err) {
      setError(err.message);
      setStatus('failed');
    }
  };

  const downloadJSON = () => {
    if (!result) return;
    const exportData = { ...result };
    delete exportData.images; 
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportData, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `qa_report_${taskId}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  const downloadPDF = () => {
    const element = document.getElementById('pdf-report-container');
    const opt = {
      margin: 10,
      filename: `qa_report_${taskId}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'landscape' }
    };
    html2pdf().set(opt).from(element).save();
  };

  return (
    <div className="min-h-screen flex bg-[#f8fafc] text-[#0f172a] font-sans">
      {/* Sidebar */}
      <div className="w-72 bg-[#0f172a] text-white flex flex-col shadow-2xl z-10">
        <div className="p-6 text-xl font-bold border-b border-slate-800 flex items-center gap-3">
          <LayoutDashboard size={26} className="text-[#2563eb]" /> 
          <span>QA AI Engine</span>
        </div>
        <nav className="flex-1 p-4 flex flex-col gap-2 mt-4">
          <button onClick={() => setActiveTab('new_test')} className={`text-left px-5 py-3.5 rounded-xl transition-all font-medium ${activeTab === 'new_test' ? 'bg-[#2563eb] shadow-lg text-white' : 'hover:bg-slate-800 text-slate-400 hover:text-slate-200'}`}>Новый тест</button>
          <button onClick={() => setActiveTab('report')} disabled={!result} className={`text-left px-5 py-3.5 rounded-xl transition-all font-medium ${(result) ? (activeTab === 'report' ? 'bg-[#2563eb] shadow-lg text-white' : 'hover:bg-slate-800 text-slate-400 hover:text-slate-200') : 'opacity-30 cursor-not-allowed'}`}>Отчет (Оракул)</button>
        </nav>
      </div>

      {/* Main Content - Убраны жесткие max-w, теперь интерфейс на весь экран */}
      <div className="flex-1 p-6 lg:p-12 overflow-y-auto w-full">
        {activeTab === 'new_test' && (
          <div className="w-full bg-white rounded-2xl shadow-sm border border-[#e2e8f0] p-8 lg:p-12">
            <div className="border-b border-[#e2e8f0] pb-6 mb-10">
              <h2 className="text-3xl font-extrabold text-[#0f172a]">Конфигурация теста</h2>
              <p className="text-slate-500 mt-2">Запустите AI-агента для автономной проверки вашего интерфейса.</p>
            </div>
            
            <form onSubmit={handleSubmit} className="flex flex-col gap-10">
              
              {/* Блок 1: Основные настройки */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div className="flex flex-col gap-3">
                  <label className="text-base font-bold text-[#0f172a]">Где тестируем? (Target URL)</label>
                  <p className="text-sm text-slate-500">Укажите адрес тестового стенда или локального сервера.</p>
                  <input type="text" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="http://localhost:8080/admin/source/" className="w-full px-5 py-4 bg-[#f8fafc] border border-[#e2e8f0] rounded-xl focus:ring-2 focus:ring-[#2563eb] focus:bg-white outline-none transition-all text-base shadow-sm" required />
                </div>
                
                <div className="flex flex-col gap-3">
                  <label className="text-base font-bold text-[#0f172a]">Инструкция для ИИ (Сценарий)</label>
                  <p className="text-sm text-slate-500">Опишите задачу на естественном языке.</p>
                  <textarea value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Например: Введи 'John Doe' в поле поиска и нажми кнопку 'Добавить пользователя'" rows={3} className="w-full px-5 py-4 bg-[#f8fafc] border border-[#e2e8f0] rounded-xl focus:ring-2 focus:ring-[#2563eb] focus:bg-white outline-none transition-all text-base shadow-sm resize-none" required />
                </div>
              </div>

              {/* Блок 2: Эталон */}
              <div className="p-8 border border-[#e2e8f0] rounded-2xl bg-[#f8fafc] shadow-sm">
                <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 mb-6 border-b border-slate-200 pb-6">
                  <div>
                    <label className="text-lg font-bold text-[#0f172a]">С чем сравниваем (Эталон)?</label>
                    <p className="text-sm text-slate-500 mt-1">Оракул сравнит результат агента с этим состоянием.</p>
                  </div>
                  <div className="flex bg-slate-200/60 rounded-lg p-1.5 shadow-inner">
                    <button type="button" onClick={() => setBaselineType('file')} className={`px-6 py-2.5 text-sm font-bold rounded-md transition-all ${baselineType === 'file' ? 'bg-white shadow text-[#2563eb]' : 'text-slate-600 hover:text-slate-900'}`}>Загрузить скриншот</button>
                    <button type="button" onClick={() => setBaselineType('url')} className={`px-6 py-2.5 text-sm font-bold rounded-md transition-all ${baselineType === 'url' ? 'bg-white shadow text-[#2563eb]' : 'text-slate-600 hover:text-slate-900'}`}>Указать URL-ссылку</button>
                  </div>
                </div>

                <div className="w-full">
                  {baselineType === 'file' ? (
                    <div className="flex items-center justify-center w-full">
                      <label className="flex flex-col items-center justify-center w-full h-40 border-2 border-[#2563eb] border-dashed rounded-xl cursor-pointer bg-blue-50/50 hover:bg-blue-50 transition-colors">
                        <div className="flex flex-col items-center justify-center pt-5 pb-6">
                          <ImageIcon className="w-10 h-10 text-[#2563eb] mb-3" />
                          <p className="mb-2 text-sm text-slate-600 font-medium">
                            {baselineFile ? <span className="text-green-600 font-bold">Выбран файл: {baselineFile.name}</span> : <span>Нажмите для загрузки картинки</span>}
                          </p>
                          <p className="text-xs text-slate-400">PNG, JPG (до 10MB)</p>
                        </div>
                        <input type="file" accept="image/*" onChange={(e) => setBaselineFile(e.target.files[0])} className="hidden" />
                      </label>
                    </div>
                  ) : (
                    <div className="flex items-center gap-4 bg-white px-5 py-2 border border-[#e2e8f0] rounded-xl focus-within:ring-2 focus-within:ring-[#2563eb] transition-shadow shadow-sm">
                      <Link size={24} className="text-slate-400" />
                      <input type="text" value={baselineUrl} onChange={(e) => setBaselineUrl(e.target.value)} placeholder="https://my-prod-site.com (Скриншот сделается автоматически)" className="flex-1 py-4 outline-none text-base bg-transparent font-medium text-slate-700" />
                    </div>
                  )}
                </div>
              </div>

              {/* Блок 3: Кнопка запуска */}
              <div className="flex flex-col lg:flex-row items-center justify-between mt-6 bg-slate-50 p-6 rounded-2xl border border-slate-200">
                <div className="text-base font-semibold mb-6 lg:mb-0">
                  {(status === 'pending' || status === 'processing') && <span className="text-[#2563eb] flex items-center gap-3 bg-blue-100/50 px-6 py-3 rounded-xl"><Loader2 className="animate-spin" size={24} /> Агент выполняет сценарий...</span>}
                  {status === 'failed' && <span className="text-[#dc2626] flex items-center gap-3 bg-red-50 px-6 py-3 rounded-xl"><XCircle size={24} /> Ошибка: {error}</span>}
                  {status === '' && <span className="text-slate-500">Система готова к запуску</span>}
                </div>
                <button type="submit" disabled={status === 'pending' || status === 'processing'} className="w-full lg:w-auto px-10 py-4 bg-[#2563eb] text-white rounded-xl font-bold hover:bg-[#1d4ed8] flex items-center justify-center gap-3 shadow-[0_4px_14px_0_rgba(37,99,235,0.39)] disabled:opacity-50 disabled:shadow-none transition-all text-lg">
                  <Play size={24} fill="currentColor" /> Начать тестирование
                </button>
              </div>
            </form>
          </div>
        )}

        {activeTab === 'report' && result && (
          <div className="w-full space-y-8">
            <div className="flex justify-end gap-4 mb-6">
              <button onClick={downloadJSON} className="flex items-center gap-2 px-6 py-3 bg-white text-slate-700 hover:bg-slate-100 rounded-xl font-bold border border-[#e2e8f0] transition-colors shadow-sm">
                <FileText size={20} /> Скачать JSON
              </button>
              <button onClick={downloadPDF} className="flex items-center gap-2 px-6 py-3 bg-red-50 text-red-700 hover:bg-red-100 rounded-xl font-bold border border-red-200 transition-colors shadow-sm">
                <Download size={20} /> Экспорт PDF
              </button>
            </div>

            <div id="pdf-report-container" className="w-full bg-white p-8 lg:p-12 rounded-2xl shadow-sm border border-[#e2e8f0]">
              
              <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between border-b border-slate-100 pb-8 mb-8">
                <div className="mb-6 lg:mb-0">
                  <h2 className="text-4xl font-extrabold text-[#0f172a]">Отчет: #{taskId.substring(0, 8)}</h2>
                  <p className="text-slate-500 mt-3 text-base flex gap-6 font-medium">
                    <span className="bg-slate-100 px-3 py-1 rounded-md">Время выполнения: {result.time_s} сек.</span>
                    <span className="bg-slate-100 px-3 py-1 rounded-md">Engine: Гибридный Агрегатор</span>
                  </p>
                </div>
                <div className={`px-8 py-5 rounded-2xl border-2 flex items-center gap-5 ${result.is_defect ? 'bg-red-50 border-red-200 text-red-700' : 'bg-green-50 border-green-200 text-[#16a34a]'}`}>
                  {result.is_defect ? <XCircle size={48} /> : <CheckCircle size={48} />}
                  <div>
                    <div className="font-black text-2xl uppercase tracking-wider">{result.is_defect ? 'Обнаружен дефект' : 'Тест пройден'}</div>
                    <div className="text-base opacity-90 mt-1 font-bold">Уверенность: {(result.confidence * 100).toFixed(1)}%</div>
                  </div>
                </div>
              </div>

              {/* Отчет LLM */}
              <div className="bg-indigo-50 border border-indigo-100 p-8 rounded-2xl flex gap-6 mb-10 shadow-sm">
                <div className="bg-indigo-100 p-4 rounded-2xl h-fit text-indigo-600 shadow-sm">
                  <Bot size={36} />
                </div>
                <div>
                  <h3 className="text-xl font-extrabold text-indigo-900 mb-3">AI Интерпретатор</h3>
                  <p className="text-indigo-800 leading-relaxed whitespace-pre-wrap text-base font-medium">{result.llm_summary}</p>
                </div>
              </div>

              {/* Метрики */}
              <h3 className="text-2xl font-bold text-[#0f172a] mb-6">Декомпозиция сигналов</h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                <MetricCard title="SSIM (Визуал/Цвета)" value={result.signals.ssim} />
                <MetricCard title="OCR (Текст/Опечатки)" value={result.signals.ocr_sim} />
                <MetricCard title="YOLO (Состав UI)" value={result.signals.yolo_struct_drift} />
                <MetricCard title="YOLO (Сдвиг Верстки)" value={result.signals.yolo_bbox_shift} />
              </div>

              {/* ИНТЕРАКТИВНЫЙ СЛАЙДЕР СРАВНЕНИЯ */}
              {result.images && (
                <div>
                  <h3 className="text-2xl font-bold text-[#0f172a] mb-6 border-t border-slate-100 pt-10">Интерактивное сравнение (Слайдер)</h3>
                  <p className="text-slate-500 mb-6 font-medium">Используйте ползунок, чтобы наглядно увидеть различия между эталоном и результатом.</p>
                  
                  <div className="w-full">
                    <ImageComparison 
                      baseline={result.images.baseline} 
                      final={result.images.final} 
                    />
                  </div>
                </div>
              )}

            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ title, value }) {
  const percentage = (value * 100).toFixed(1);
  const isHigh = value > 0.4;
  return (
    <div className="bg-[#f8fafc] p-6 rounded-2xl shadow-sm border border-[#e2e8f0] flex flex-col transition-all hover:shadow-md">
      <span className="text-slate-500 text-sm font-bold uppercase tracking-wider">{title}</span>
      <div className={`text-4xl font-black mt-4 ${isHigh ? 'text-[#dc2626]' : 'text-[#0f172a]'}`}>{percentage}%</div>
      <div className="w-full bg-slate-200 rounded-full h-2.5 mt-5 overflow-hidden shadow-inner">
        <div className={`h-full rounded-full transition-all duration-1000 ${isHigh ? 'bg-gradient-to-r from-red-500 to-red-600' : 'bg-gradient-to-r from-blue-500 to-blue-600'}`} style={{ width: `${percentage}%` }}></div>
      </div>
    </div>
  );
}

export default App;