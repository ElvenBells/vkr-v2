import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import html2pdf from 'html2pdf.js';
import {
  BarChart3,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Download,
  FileJson2,
  FileText,
  Globe,
  Image as ImageIcon,
  Link2,
  Loader2,
  Lock,
  MousePointer2,
  Play,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  PanelTop,
  Bot,
  ArrowLeftRight,
  Upload,
  ExternalLink,
  FileImage,
  XCircle,
  Gauge,
} from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8001/api';

function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

function formatTaskId(taskId) {
  if (!taskId) return '—';
  return String(taskId).slice(0, 8);
}

function formatDateTime(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('ru-RU', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function normalizeScore(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return 0;
  return value > 1 ? Math.min(value / 100, 1) : Math.max(0, Math.min(value, 1));
}

function scoreToDisplay(value) {
  const normalized = normalizeScore(value);
  return normalized.toFixed(2);
}

function percentFromScore(value) {
  return Math.round(normalizeScore(value) * 100);
}

function deviationFromScore(value) {
  return Math.max(0, 100 - percentFromScore(value));
}

function getSeverityLabel(result) {
  if (result?.severity) return result.severity;
  if (!result) return '—';
  if (result.is_defect) {
    const confidence = normalizeScore(result.confidence);
    if (confidence >= 0.85) return 'High';
    if (confidence >= 0.65) return 'Medium';
    return 'Low';
  }
  return 'Low';
}

function MetricCard({ title, value, icon: Icon, accent = 'blue' }) {
  const pct = percentFromScore(value);
  const deviation = deviationFromScore(value);
  const isCritical = deviation > 40;

  const barClass = isCritical
    ? 'bg-gradient-to-r from-rose-500 to-red-500'
    : accent === 'orange'
      ? 'bg-gradient-to-r from-orange-500 to-amber-500'
      : accent === 'green'
        ? 'bg-gradient-to-r from-emerald-500 to-green-500'
        : accent === 'indigo'
          ? 'bg-gradient-to-r from-indigo-500 to-blue-500'
          : 'bg-gradient-to-r from-sky-500 to-blue-500';

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white/90 p-4 shadow-sm shadow-slate-200/60 backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            {title}
          </p>
          <div className={cn('mt-2 text-3xl font-semibold leading-none', isCritical ? 'text-rose-600' : 'text-slate-900')}>
            {scoreToDisplay(value)}
            <span className="ml-1 text-sm font-medium text-slate-400">/ 1.00</span>
          </div>
        </div>
        <div className={cn(
          'grid h-10 w-10 place-items-center rounded-xl border',
          isCritical ? 'border-rose-200 bg-rose-50 text-rose-600' : 'border-slate-200 bg-slate-50 text-slate-600'
        )}>
          <Icon size={18} />
        </div>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-200/80">
        <div
          className={cn('h-full rounded-full transition-all duration-500 ease-out', barClass)}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="mt-3 flex items-center justify-between text-xs">
        <span className={cn('font-medium', isCritical ? 'text-rose-600' : 'text-slate-500')}>
          Отклонение: {deviation}%
        </span>
        <span className="text-slate-400">Порог: 40%</span>
      </div>
    </div>
  );
}

function StatusPill({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-100 text-slate-700 border-slate-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    red: 'bg-rose-50 text-rose-700 border-rose-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    indigo: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  };

  return (
    <span className={cn('inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold', tones[tone] || tones.slate)}>
      {children}
    </span>
  );
}

function SectionTitle({ icon: Icon, title, subtitle, right }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-200/80 pb-5">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 grid h-11 w-11 place-items-center rounded-2xl bg-blue-50 text-blue-600 ring-1 ring-inset ring-blue-100">
          <Icon size={20} />
        </div>
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
        </div>
      </div>
      {right}
    </div>
  );
}

function ImageComparison({ baseline, final }) {
  const [position, setPosition] = useState(50);

  return (
    <div className="relative overflow-hidden rounded-3xl border border-slate-200 bg-slate-900 shadow-[0_20px_60px_-35px_rgba(15,23,42,0.45)] select-none">
      <div className="absolute left-4 top-4 z-20 rounded-full bg-slate-900/85 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur">
        Эталон (Baseline)
      </div>
      <div className="absolute right-4 top-4 z-20 rounded-full bg-blue-600/90 px-3 py-1.5 text-xs font-semibold text-white backdrop-blur">
        Результат (Playwright)
      </div>

      <div className="relative aspect-video w-full bg-slate-100">
        <img
          src={`data:image/png;base64,${baseline}`}
          alt="Baseline"
          className="absolute inset-0 h-full w-full object-contain bg-white pointer-events-none"
        />

        <img
          src={`data:image/png;base64,${final}`}
          alt="Result"
          className="absolute inset-0 h-full w-full object-contain bg-white pointer-events-none"
          style={{ clipPath: `inset(0 0 0 ${position}%)` }}
        />

        <input
          type="range"
          min="0"
          max="100"
          value={position}
          onChange={(e) => setPosition(Number(e.target.value))}
          className="absolute inset-0 z-20 h-full w-full cursor-ew-resize opacity-0"
          aria-label="Слайдер сравнения"
        />

        <div
          className="absolute top-0 bottom-0 z-10 w-[3px] bg-blue-600 shadow-[0_0_30px_rgba(37,99,235,0.55)]"
          style={{ left: `${position}%`, transform: 'translateX(-50%)' }}
        >
          <div className="absolute left-1/2 top-1/2 grid h-12 w-12 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border-4 border-white bg-blue-600 text-white shadow-xl">
            <ArrowLeftRight size={18} />
          </div>
        </div>

        <div className="absolute inset-x-0 bottom-0 z-10 flex items-center justify-between px-4 pb-4 text-xs font-medium text-white">
          <span className="rounded-full bg-slate-900/70 px-3 py-1 backdrop-blur">Базовая версия</span>
          <span className="rounded-full bg-slate-900/70 px-3 py-1 backdrop-blur">Финальный скрин</span>
        </div>
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
  const [isDragging, setIsDragging] = useState(false);
  
  // Состояние загрузки во время выгрузки PDF
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false);

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
            setError(data.error || 'Не удалось выполнить проверку');
            clearInterval(intervalId);
          }
        } catch (err) {
          console.error('Ошибка при опросе:', err);
        }
      }, 3000);
    }

    return () => clearInterval(intervalId);
  }, [taskId, status]);

  const summaryDate = useMemo(() => formatDateTime(result?.created_at || result?.createdAt), [result]);

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
      alert('Пожалуйста, укажите эталон (файл или ссылку)');
      return;
    }

    try {
      setStatus('pending');
      setResult(null);
      setError(null);
      const response = await axios.post(`${API_BASE_URL}/run-test`, formData);
      setTaskId(response.data.task_id);
    } catch (err) {
      setError(err?.message || 'Ошибка запуска теста');
      setStatus('failed');
    }
  };

  const downloadJSON = () => {
    if (!result) return;
    const exportData = { ...result };
    delete exportData.images;
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(exportData, null, 2));
    const anchor = document.createElement('a');
    anchor.setAttribute('href', dataStr);
    anchor.setAttribute('download', `qa_report_${taskId || 'result'}.json`);
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  };

  // Полностью безопасная функция выгрузки
  const downloadPDF = async () => {
    if (!result) return;
    setIsGeneratingPDF(true);

    // Пауза 100мс, чтобы React успел отрисовать лоадер на кнопке
    setTimeout(async () => {
      try {
        const element = document.getElementById('pdf-export-content');
        if (!element) throw new Error('Скрытый контейнер для PDF не найден');

        const opt = {
          margin: 10,
          filename: `qa_report_${taskId || 'result'}.pdf`,
          image: { type: 'jpeg', quality: 0.95 },
          html2canvas: { 
            scale: 1.5, 
            useCORS: true, 
            logging: false, // отключено для скорости
            windowWidth: 800 // жесткая фиксация ширины
          },
          jsPDF: { 
            unit: 'mm', 
            format: 'a4', 
            orientation: 'portrait' 
          },
        };

        // Запуск генерации
        await html2pdf().set(opt).from(element).save();

      } catch (e) {
        console.error('Ошибка экспорта PDF:', e);
        alert(`Не удалось выгрузить PDF. Причина: ${e.message}`);
      } finally {
        setIsGeneratingPDF(false); // В любом случае возвращаем кнопку в норму
      }
    }, 100);
  };

  const reportReady = Boolean(result);
  const isBusy = status === 'pending' || status === 'processing';

  const confidence = normalizeScore(result?.confidence);
  const defect = Boolean(result?.is_defect);

  const metricValues = [
    { title: 'SSIM', value: result?.signals?.ssim, icon: Gauge, accent: 'indigo' },
    { title: 'OCR (Текст)', value: result?.signals?.ocr_sim, icon: FileText, accent: 'orange' },
    { title: 'UI Структура (YOLO)', value: result?.signals?.yolo_struct_drift, icon: PanelTop, accent: 'green' },
    { title: 'Сдвиг Bounding Boxes', value: result?.signals?.yolo_bbox_shift, icon: MousePointer2, accent: 'blue' },
  ];

  const defaultDefects = useMemo(() => {
    if (!result) return [];
    const items = [];

    if (result?.signals?.yolo_bbox_shift != null) {
      items.push(`Смещение геометрии интерфейса: ${percentFromScore(result.signals.yolo_bbox_shift)}%`);
    }
    if (result?.signals?.ocr_sim != null) {
      items.push(`Текстовый дрейф: ${percentFromScore(result.signals.ocr_sim)}%`);
    }
    if (result?.signals?.ssim != null) {
      items.push(`Визуальные различия: ${percentFromScore(result.signals.ssim)}%`);
    }
    if (result?.signals?.yolo_struct_drift != null) {
      items.push(`Изменения структуры UI: ${percentFromScore(result.signals.yolo_struct_drift)}%`);
    }

    return items.slice(0, 4);
  }, [result]);

  const signalsCount = result?.signals ? Object.keys(result.signals).length : 0;
  const totalSignals = result?.total_signals || 8;

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 relative">
      <div className="mx-auto flex min-h-screen w-full flex-col">
        {/* Header */}
        <header className="border-b border-slate-200/80 bg-white/80 px-5 py-4 backdrop-blur-xl">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-200">
                <Sparkles size={26} />
              </div>
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold tracking-tight text-slate-900">AutoTester Agent</h1>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-1 shadow-sm">
              <button
                type="button"
                onClick={() => setActiveTab('new_test')}
                className={cn(
                  'inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition-all',
                  activeTab === 'new_test'
                    ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-200'
                    : 'text-slate-600 hover:bg-white hover:text-slate-900'
                )}
              >
                <Upload size={16} />
                Новый тест
              </button>

              <button
                type="button"
                disabled={!reportReady}
                onClick={() => setActiveTab('report')}
                className={cn(
                  'inline-flex items-center gap-2 rounded-xl px-5 py-3 text-sm font-semibold transition-all',
                  activeTab === 'report'
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-600 hover:bg-white hover:text-slate-900',
                  !reportReady && 'cursor-not-allowed opacity-40 hover:bg-transparent hover:text-slate-600'
                )}
              >
                <BarChart3 size={16} />
                Отчет
                {!reportReady ? <Lock size={14} /> : null}
              </button>
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 shadow-sm lg:flex">
                <CircleAlert size={16} />
                <span>{reportReady ? 'Отчет доступен' : 'Отчет станет доступен после завершения анализа'}</span>
              </div>
              <button
                type="button"
                className="grid h-12 w-12 place-items-center rounded-2xl border border-slate-200 bg-white text-slate-700 shadow-sm transition hover:bg-slate-50"
                aria-label="Theme"
              >
                <span className="text-lg">☼</span>
              </button>
              <button
                type="button"
                className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-3 py-2.5 shadow-sm transition hover:bg-slate-50"
              >
                <div className="grid h-10 w-10 place-items-center rounded-full bg-gradient-to-br from-indigo-600 to-blue-600 text-sm font-bold text-white">
                  QA
                </div>
                <div className="hidden text-left sm:block">
                  <div className="text-sm font-semibold leading-tight text-slate-900">QA Engineer</div>
                  <div className="text-xs text-slate-500">Профиль</div>
                </div>
                <ChevronDown size={16} className="text-slate-400" />
              </button>
            </div>
          </div>
        </header>

        {/* Main dashboard */}
        <main className="flex-1 p-4 lg:p-6 z-10 relative">
          <div className="grid gap-6 xl:grid-cols-[1.02fr_1.18fr]">
            {/* Left configuration panel */}
            <section className="rounded-3xl border border-slate-200/80 bg-white p-6 shadow-sm shadow-slate-200/60">
              <SectionTitle
                icon={PanelTop}
                title="Конфигурация теста"
                subtitle="Опишите целевой сайт, сценарий и эталон для сравнения."
              />

              <form onSubmit={handleSubmit} className="mt-6 space-y-6">
                <div className="grid gap-5 md:grid-cols-2">
                  <label className="block">
                    <span className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800">
                      <Globe size={16} className="text-blue-600" />
                      Target URL
                    </span>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3.5 shadow-inner shadow-slate-100 focus-within:border-blue-300 focus-within:bg-white focus-within:ring-4 focus-within:ring-blue-100">
                      <input
                        type="text"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="https://example.com или http://localhost:3000"
                        className="w-full bg-transparent text-sm outline-none placeholder:text-slate-400"
                        required
                      />
                    </div>
                  </label>

                  <label className="block">
                    <span className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800">
                      <Sparkles size={16} className="text-indigo-600" />
                      Инструкция для ИИ (Сценарий)
                    </span>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3.5 shadow-inner shadow-slate-100 focus-within:border-indigo-300 focus-within:bg-white focus-within:ring-4 focus-within:ring-indigo-100">
                      <textarea
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        placeholder="Например: авторизация пользователя, добавление товара в корзину и проверка успешной покупки."
                        rows={5}
                        className="w-full resize-none bg-transparent text-sm outline-none placeholder:text-slate-400"
                        required
                      />
                    </div>
                  </label>
                </div>

                <div className="rounded-3xl border border-slate-200 bg-[#f8fafc] p-5">
                  <div className="flex flex-col gap-4 border-b border-slate-200 pb-5 md:flex-row md:items-center md:justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-slate-900">Эталон (Baseline)</h3>
                      <p className="mt-1 text-sm text-slate-500">Загрузите скриншот или укажите URL-ссылку.</p>
                    </div>

                    <div className="inline-flex rounded-2xl border border-slate-200 bg-white p-1 shadow-sm">
                      <button
                        type="button"
                        onClick={() => setBaselineType('file')}
                        className={cn(
                          'rounded-xl px-4 py-2 text-sm font-semibold transition',
                          baselineType === 'file'
                            ? 'bg-blue-600 text-white shadow-md shadow-blue-200'
                            : 'text-slate-600 hover:text-slate-900'
                        )}
                      >
                        Загрузить скриншот
                      </button>
                      <button
                        type="button"
                        onClick={() => setBaselineType('url')}
                        className={cn(
                          'rounded-xl px-4 py-2 text-sm font-semibold transition',
                          baselineType === 'url'
                            ? 'bg-blue-600 text-white shadow-md shadow-blue-200'
                            : 'text-slate-600 hover:text-slate-900'
                        )}
                      >
                        Указать URL-ссылку
                      </button>
                    </div>
                  </div>

                  {baselineType === 'file' ? (
                    <label
                      onDragEnter={(e) => { e.preventDefault(); setIsDragging(true); }}
                      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                      onDragLeave={(e) => { e.preventDefault(); setIsDragging(false); }}
                      onDrop={(e) => {
                        e.preventDefault();
                        setIsDragging(false);
                        const file = e.dataTransfer.files?.[0];
                        if (file) {
                          const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
                          if (!validTypes.includes(file.type)) {
                            alert('❌ Ошибка: Допускаются только изображения в форматах PNG, JPG или WebP.');
                            return;
                          }
                          setBaselineFile(file);
                        }
                      }}
                      className={cn(
                        'mt-5 flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed bg-white px-6 py-8 text-center transition',
                        isDragging ? 'border-blue-500 bg-blue-50/80' : 'border-blue-200 hover:bg-blue-50/50'
                      )}
                    >
                      <div className="grid h-14 w-14 place-items-center rounded-full bg-blue-50 text-blue-600 ring-1 ring-inset ring-blue-100">
                        <FileImage size={24} />
                      </div>

                      <p className="mt-4 text-base font-semibold text-slate-900">
                        {baselineFile ? (
                          <span className="inline-flex items-center gap-2 text-emerald-600">
                            <CheckCircle2 size={18} />
                            {baselineFile.name}
                          </span>
                        ) : (
                          'Перетащите файл сюда или кликните для выбора'
                        )}
                      </p>
                      <p className="mt-2 text-sm text-slate-500">PNG, JPG, WebP (до 10MB)</p>

                      <input
                        type="file"
                        accept=".png, .jpg, .jpeg, .webp"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
                            if (!validTypes.includes(file.type)) {
                              alert('❌ Ошибка: Пожалуйста, загрузите изображение (PNG, JPG, WebP).');
                              e.target.value = ''; // Сбрасываем некорректный файл
                              return;
                            }
                            setBaselineFile(file);
                          } else {
                            setBaselineFile(null);
                          }
                        }}
                        className="hidden"
                      />
                    </label>
                  ) : (
                    <div className="mt-5 rounded-3xl border border-slate-200 bg-white px-4 py-4 shadow-sm focus-within:border-blue-300 focus-within:ring-4 focus-within:ring-blue-100">
                      <div className="flex items-center gap-3">
                        <Link2 size={18} className="text-slate-400" />
                        <input
                          type="text"
                          value={baselineUrl}
                          onChange={(e) => setBaselineUrl(e.target.value)}
                          placeholder="https://site.com/baseline"
                          className="w-full bg-transparent text-sm outline-none placeholder:text-slate-400"
                        />
                      </div>
                    </div>
                  )}

                  {baselineFile ? (
                    <div className="mt-4 flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3">
                      <div className="grid h-10 w-10 place-items-center rounded-xl bg-white text-emerald-600">
                        <ImageIcon size={18} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-semibold text-emerald-900">{baselineFile.name}</div>
                        <div className="text-xs text-emerald-700/80">
                          {(baselineFile.size / 1024 / 1024).toFixed(2)} MB
                        </div>
                      </div>
                      <StatusPill tone="green">Загружено</StatusPill>
                    </div>
                  ) : null}
                </div>

                <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-start gap-3">
                      <div className={cn(
                        'mt-0.5 grid h-12 w-12 place-items-center rounded-full border',
                        isBusy ? 'border-blue-200 bg-blue-50 text-blue-600' : error ? 'border-rose-200 bg-rose-50 text-rose-600' : 'border-slate-200 bg-slate-50 text-slate-500'
                      )}>
                        {isBusy ? <Loader2 size={20} className="animate-spin" /> : error ? <XCircle size={20} /> : <ShieldCheck size={20} />}
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-slate-900">
                          {isBusy ? 'Агент выполняет сценарий...' : error ? 'Ошибка выполнения' : 'Готов к запуску'}
                        </div>
                        <div className="mt-1 text-sm text-slate-500">
                          {isBusy
                            ? 'Форма заблокирована до завершения анализа.'
                            : error
                              ? error
                              : 'Нажмите кнопку ниже, чтобы запустить проверку.'}
                        </div>
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={isBusy}
                      className={cn(
                        'inline-flex items-center justify-center gap-3 rounded-2xl px-6 py-4 text-base font-semibold text-white shadow-lg shadow-blue-200 transition active:scale-[0.99]',
                        isBusy
                          ? 'cursor-not-allowed bg-slate-400 shadow-none'
                          : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500'
                      )}
                    >
                      {isBusy ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} fill="currentColor" />}
                      Начать тестирование
                    </button>
                  </div>
                </div>
              </form>
            </section>

            {/* Right report panel */}
            <section className="rounded-3xl border border-slate-200/80 bg-white p-6 shadow-sm shadow-slate-200/60">
              <div className="space-y-6">
                <div className="flex flex-col gap-5 border-b border-slate-200/80 pb-5 md:flex-row md:items-start md:justify-between">
                  <SectionTitle
                    icon={FileText}
                    title="Отчет о тестировании"
                    subtitle={`ID: #${formatTaskId(taskId)} · ${summaryDate !== '—' ? summaryDate : 'Ожидает запуска'}`}
                    right={null}
                  />

                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={downloadJSON}
                      disabled={!reportReady}
                      className={cn(
                        'inline-flex items-center gap-2 rounded-2xl border px-4 py-3 text-sm font-semibold transition',
                        reportReady
                          ? 'border-blue-200 bg-white text-blue-700 shadow-sm hover:bg-blue-50'
                          : 'cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400'
                      )}
                    >
                      <FileJson2 size={16} />
                      JSON
                    </button>
                    <button
                      type="button"
                      onClick={downloadPDF}
                      disabled={!reportReady || isGeneratingPDF}
                      className={cn(
                        'inline-flex items-center gap-2 rounded-2xl border px-4 py-3 text-sm font-semibold transition min-w-[110px] justify-center',
                        reportReady && !isGeneratingPDF
                          ? 'border-rose-200 bg-white text-rose-700 shadow-sm hover:bg-rose-50'
                          : 'cursor-not-allowed border-slate-200 bg-slate-50 text-slate-400'
                      )}
                    >
                      {isGeneratingPDF ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                      {isGeneratingPDF ? 'Экспорт...' : 'PDF'}
                    </button>
                  </div>
                </div>

                {!reportReady ? (
                  <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-8">
                    <div className="flex items-start gap-4">
                      <div className="grid h-12 w-12 place-items-center rounded-2xl bg-white text-slate-500 shadow-sm">
                        <Lock size={20} />
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-slate-900">Отчет недоступен</h3>
                        <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">
                          Здесь появится вердикт агрегатора, объяснение LLM, метрики качества и интерактивное сравнение.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className={cn(
                      'rounded-3xl border p-5 shadow-sm',
                      defect ? 'border-rose-200 bg-rose-50/70' : 'border-emerald-200 bg-emerald-50/70'
                    )}>
                      <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
                        <div className="flex items-start gap-4">
                          <div className={cn(
                            'grid h-14 w-14 place-items-center rounded-2xl text-white shadow-lg',
                            defect ? 'bg-gradient-to-br from-rose-500 to-red-500 shadow-rose-200' : 'bg-gradient-to-br from-emerald-500 to-green-500 shadow-emerald-200'
                          )}>
                            {defect ? <ShieldAlert size={26} /> : <ShieldCheck size={26} />}
                          </div>
                          <div>
                            <div className={cn('text-2xl font-semibold', defect ? 'text-rose-700' : 'text-emerald-700')}>
                              {defect ? 'Обнаружен дефект' : 'Тест пройден'}
                            </div>
                            <div className="mt-1 text-sm text-slate-600">Уверенность агрегатора</div>
                            <div className="mt-4 h-3 w-72 max-w-full overflow-hidden rounded-full bg-white/80">
                              <div
                                className={cn('h-full rounded-full transition-all duration-700', defect ? 'bg-rose-500' : 'bg-emerald-500')}
                                style={{ width: `${Math.round(confidence * 100)}%` }}
                              />
                            </div>
                          </div>
                        </div>

                        <div className="min-w-[200px] rounded-2xl border border-white/70 bg-white/80 p-4 shadow-sm">
                          <div className="flex items-center justify-between gap-4">
                            <div className="text-sm text-slate-500">Общая уверенность</div>
                            <StatusPill tone={defect ? 'red' : 'green'}>{defect ? 'FAIL' : 'PASS'}</StatusPill>
                          </div>
                          <div className="mt-2 text-4xl font-semibold text-slate-900">
                            {Math.round(confidence * 100)}%
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="grid gap-4 rounded-3xl border border-indigo-200 bg-indigo-50/70 p-5 shadow-sm">
                      <div className="flex items-start gap-4">
                        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-white text-indigo-600 shadow-sm ring-1 ring-inset ring-indigo-100">
                          <Bot size={20} />
                        </div>
                        <div className="flex-1">
                          <h3 className="text-lg font-semibold text-indigo-950">AI-интерпретация (LLM)</h3>
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-indigo-950/90">
                            {result?.llm_summary || 'Нет текстового резюме от модели.'}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div>
                      <div className="mb-4 flex items-center justify-between gap-4">
                        <h3 className="text-lg font-semibold text-slate-900">Метрики качества</h3>
                      </div>
                      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        {metricValues.map((item) => (
                          <MetricCard key={item.title} title={item.title} value={item.value} icon={item.icon} accent={item.accent} />
                        ))}
                      </div>
                    </div>

                    <div className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
                      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                        <div className="mb-4 flex items-center justify-between gap-4">
                          <div>
                            <h3 className="text-lg font-semibold text-slate-900">Сравнение: Эталон vs Результат</h3>
                            <p className="mt-1 text-sm text-slate-500">Перетаскивайте ползунок для анализа сдвигов.</p>
                          </div>
                        </div>

                        {result?.images?.baseline && result?.images?.final ? (
                          <ImageComparison baseline={result.images.baseline} final={result.images.final} />
                        ) : (
                          <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">
                            Изображения не переданы backend-ом.
                          </div>
                        )}
                      </div>

                      <aside className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
                        <div className="mb-4 flex items-center justify-between gap-3">
                          <h3 className="text-lg font-semibold text-slate-900">Детали дефектов</h3>
                        </div>
                        <div className="space-y-3">
                          {(defaultDefects.length ? defaultDefects : ['Нарушений не найдено']).map((item, idx) => (
                            <div key={`${item}-${idx}`} className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
                              <div className="mt-0.5 grid h-7 w-7 place-items-center rounded-full bg-slate-200 text-slate-700 text-xs font-bold">
                                {idx + 1}
                              </div>
                              <div className="text-sm leading-6 text-slate-700">{item}</div>
                            </div>
                          ))}
                        </div>
                      </aside>
                    </div>
                  </>
                )}
              </div>
            </section>
          </div>
        </main>
      </div>

      {/* СЕКРЕТНЫЙ КОНТЕЙНЕР ДЛЯ РЕНДЕРИНГА PDF
        Полностью избавлен от любых CSS-классов Tailwind, чтобы избежать ошбики "oklch".
        Все цвета прописаны строгими HEX-кодами через style={{...}}.
      */}
      <div style={{ position: 'absolute', top: 0, left: 0, opacity: 0, pointerEvents: 'none', zIndex: -50 }}>
        {reportReady && (
          <div id="pdf-export-content" style={{ width: '800px', backgroundColor: '#ffffff', padding: '2rem', color: '#000000' }}>
            
            {/* Шапка */}
            <div style={{ borderBottom: '2px solid #e2e8f0', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
              <h1 style={{ fontSize: '1.875rem', fontWeight: 'bold', color: '#0f172a', margin: 0 }}>Отчет о QA-тестировании #{formatTaskId(taskId)}</h1>
              <p style={{ color: '#64748b', marginTop: '0.5rem' }}>Дата формирования: {summaryDate !== '—' ? summaryDate : new Date().toLocaleString()}</p>
            </div>

            {/* Статус */}
            <div style={{ 
              padding: '1.25rem', 
              marginBottom: '1.5rem', 
              borderRadius: '0.75rem', 
              border: `2px solid ${defect ? '#fda4af' : '#6ee7b7'}`, 
              backgroundColor: defect ? '#fff1f2' : '#ecfdf5',
            }}>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', margin: 0, color: defect ? '#be123c' : '#047857', marginBottom: '0.5rem' }}>
                {defect ? '❌ ОБНАРУЖЕН ДЕФЕКТ (FAIL)' : '✅ ТЕСТ ПРОЙДЕН (PASS)'}
              </h2>
              <p style={{ fontWeight: 600, fontSize: '1.125rem', margin: 0, color: '#1e293b' }}>
                Общая уверенность системы: {Math.round(confidence * 100)}%
              </p>
            </div>

            {/* LLM */}
            <div style={{ marginBottom: '1.5rem', padding: '1.25rem', border: '1px solid #c7d2fe', borderRadius: '0.75rem', backgroundColor: '#eef2ff' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#1e1b4b', marginBottom: '0.75rem', marginTop: 0 }}>AI-интерпретация (LLM)</h3>
              <p style={{ whiteSpace: 'pre-wrap', fontSize: '1rem', lineHeight: 1.6, color: '#1e1b4b', margin: 0 }}>
                {result?.llm_summary || 'Нет текстового резюме от модели.'}
              </p>
            </div>

            {/* Метрики */}
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '1rem', color: '#0f172a' }}>Метрики качества (Сигналы)</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
                {metricValues.map((item) => (
                  <div key={item.title} style={{ padding: '1rem', border: '1px solid #e2e8f0', borderRadius: '0.5rem', backgroundColor: '#f8fafc', width: 'calc(50% - 0.5rem)', boxSizing: 'border-box' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{item.title}</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#0f172a', marginTop: '0.5rem' }}>{scoreToDisplay(item.value)} / 1.00</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="html2pdf__page-break"></div>

            {/* Скриншоты */}
            {result?.images?.baseline && (
              <div style={{ marginBottom: '2rem' }}>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '1rem', color: '#0f172a' }}>Эталонное состояние (Baseline)</h3>
                <img 
                  src={`data:image/png;base64,${result.images.baseline}`} 
                  alt="Baseline" 
                  style={{ width: '100%', border: '2px solid #e2e8f0', borderRadius: '0.75rem', display: 'block' }} 
                />
              </div>
            )}

            <div className="html2pdf__page-break"></div>

            {result?.images?.final && (
              <div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '1rem', color: '#0f172a' }}>Результат тестирования (Final)</h3>
                <img 
                  src={`data:image/png;base64,${result.images.final}`} 
                  alt="Final" 
                  style={{ width: '100%', border: '2px solid #e2e8f0', borderRadius: '0.75rem', display: 'block' }} 
                />
              </div>
            )}

          </div>
        )}
      </div>

    </div>
  );
}

export default App;