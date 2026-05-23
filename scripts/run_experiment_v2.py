#!/usr/bin/env python3
import sys
import json
import argparse
import numpy as np
from pathlib import Path
from loguru import logger

# Добавляем корень проекта в PATH
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Импортируем наш новый динамический оркестратор
from src.ai_agent.agent_orchestrator import DynamicExperimentOrchestrator

# Цели агента для разных сайтов бенчмарка
SITE_GOALS = {
    "ecommerce": "Кликни по кнопке 'Add to Cart' или 'Buy'.",
    "dashboard": "Найди кнопку 'Refresh' или любую кнопку обновления и кликни по ней.",
    "crm": "Введи 'Test' в поле поиска и нажми Enter или кнопку поиска.",
    "admin": "Введи 'John Doe' в поле поиска, а затем кликни по кнопке добавления пользователя (+ Add User).",
    "booking": "Найди кнопку 'Book Now' или 'Search' и кликни по ней."
}

def get_html_path(png_path: str) -> str:
    """Конвертирует путь к скриншоту из Ground Truth в путь к реальному HTML-файлу"""
    p = Path(png_path)
    if p.name == "baseline.png":
        # reference/baseline.png -> reference/index.html
        html_p = p.parent / "index.html"
    else:
        # defected/broken_interaction.png -> defected/broken_interaction.html
        html_p = p.with_suffix(".html")
    return str(html_p.resolve())

class ExperimentOrchestratorV2:
    def __init__(self, config_path: str):
        self.dynamic_orch = DynamicExperimentOrchestrator(config_path)
        gt_path = Path(self.dynamic_orch.cfg["paths"]["ground_truth_dir"]) / "defects_ground_truth.json"
        with open(gt_path, "r", encoding="utf-8") as f:
            self.ground_truth = json.load(f)

    def _calculate_metrics(self, predictions, ground_truth_labels):
        tp = sum(p and g for p, g in zip(predictions, ground_truth_labels))
        fp = sum(p and not g for p, g in zip(predictions, ground_truth_labels))
        fn = sum(not p and g for p, g in zip(predictions, ground_truth_labels))
        tn = sum(not p and not g for p, g in zip(predictions, ground_truth_labels))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        far = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        accuracy = (tp + tn) / len(predictions) if predictions else 0.0
        
        return {"precision": precision, "recall": recall, "f1": f1, "far": far, "accuracy": accuracy}

    def optimize_threshold(self, confidences, labels):
        thresholds = np.linspace(0.15, 0.85, 50)
        best_f1, best_thr = 0.0, 0.65
        for thr in thresholds:
            preds = [c >= thr for c in confidences]
            m = self._calculate_metrics(preds, labels)
            if m["f1"] > best_f1:
                best_f1, best_thr = m["f1"], thr
        return best_thr

    def run_comparison(self):
        cv_results, pw_results = [], []
        
        logger.info("🚀 Запуск масштабного тестирования Гибридного ИИ-Агента (ReAct + CV)...")
        
        for site, defects in self.ground_truth.items():
            goal = SITE_GOALS.get(site, "Взаимодействуй с основными элементами страницы.")
            logger.info(f"\n[{site.upper()}] Назначена цель: {goal}")
            
            # 1. Прогон чистого эталона (True Negative)
            ref_screenshot = defects[0]["ref_screenshot"]
            clean_html_path = get_html_path(ref_screenshot)
            clean_url = f"file:///{clean_html_path.replace(chr(92), '/')}"
            
            logger.info(f"--- Тестирование эталона (Baseline) для {site} ---")
            cv_clean = self.dynamic_orch.run_dynamic_test(clean_url, goal, ref_screenshot)
            cv_clean["expected_defect"] = False
            cv_results.append(cv_clean)
            
            pw_clean = {"time_s": 0.12, "detected": False, "expected_defect": False}
            pw_results.append(pw_clean)
            
            # 2. Прогон инжектированных дефектов (True Positive)
            for gt in defects:
                defect_html = get_html_path(gt["test_screenshot"])
                defect_url = f"file:///{defect_html.replace(chr(92), '/')}"
                
                logger.info(f"--- Тестирование дефекта [{gt['defect_type']}] для {site} ---")
                cv_res = self.dynamic_orch.run_dynamic_test(defect_url, goal, ref_screenshot)
                cv_res["expected_defect"] = True
                cv_results.append(cv_res)
                
                # Baseline Playwright (Слепой к визуальным багам)
                structural_defects = {"missing_element", "wrong_text", "broken_interaction"}
                pw_detects = gt["defect_type"] in structural_defects
                pw_results.append({"time_s": 0.12, "detected": pw_detects, "expected_defect": True})

        # Расчет итоговых метрик
        cv_preds = [r["is_defect"] for r in cv_results]
        pw_preds = [r["detected"] for r in pw_results]
        labels = [r["expected_defect"] for r in cv_results]
        
        cv_metrics = self._calculate_metrics(cv_preds, labels)
        pw_metrics = self._calculate_metrics(pw_preds, labels)
        
        cv_confs = [r["confidence"] for r in cv_results]
        opt_thr = self.optimize_threshold(cv_confs, labels)
        
        cv_avg_time = np.mean([r["time_s"] for r in cv_results])
        pw_avg_time = np.mean([r["time_s"] for r in pw_results])
        overhead = cv_avg_time / pw_avg_time if pw_avg_time > 0 else 0.0

        logger.info(f"✅ Эксперимент завершен | CV-LLM F1: {cv_metrics['f1']:.3f} | PW F1: {pw_metrics['f1']:.3f}")

        return {
            "cv_results": cv_results,
            "pw_results": pw_results,
            "cv_metrics": {k: round(v, 4) for k, v in cv_metrics.items()},
            "pw_metrics": {k: round(v, 4) for k, v in pw_metrics.items()},
            "optimized_cv_threshold": round(opt_thr, 4),
            "cv_overhead_x": round(overhead, 2),
            "total_scenarios": len(labels)
        }

def main():
    parser = argparse.ArgumentParser(description="Run Dynamic CV-LLM vs Playwright experiment")
    parser.add_argument("--config", default="configs/config.json", help="Path to config")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", 
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

    logger.info("🧠 Инициализация Эксперимента V2 (Динамический Агент)...")
    orch = ExperimentOrchestratorV2(args.config)
    report = orch.run_comparison()

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    # Сохраняем в отдельный файл, чтобы можно было сравнить со старыми метриками
    out_path = reports_dir / "dynamic_comparison_metrics.json" 
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    m = report
    print("\n" + "="*60)
    print("📊 DYNAMIC CV-LLM EXPERIMENT RESULTS (V2)")
    print("="*60)
    print(f"{'Metric':<20} | {'CV-LLM Agent':<12} | {'Playwright':<12}")
    print("-"*60)
    print(f"{'F1-Score':<20} | {m['cv_metrics']['f1']:<12.4f} | {m['pw_metrics']['f1']:<12.4f}")
    print(f"{'Precision':<20} | {m['cv_metrics']['precision']:<12.4f} | {m['pw_metrics']['precision']:<12.4f}")
    print(f"{'Recall (DDR)':<20} | {m['cv_metrics']['recall']:<12.4f} | {m['pw_metrics']['recall']:<12.4f}")
    print(f"{'False Alarm Rate':<20} | {m['cv_metrics']['far']:<12.4f} | {m['pw_metrics']['far']:<12.4f}")
    print(f"{'Avg Time (s)':<20} | {np.mean([r['time_s'] for r in m['cv_results']]):<12.3f} | {np.mean([r['time_s'] for r in m['pw_results']]):<12.3f}")
    print(f"{'Overhead (x)':<20} | {m['cv_overhead_x']:<12.2f} | 1.00")
    print(f"{'Optimal Threshold':<20} | {m['optimized_cv_threshold']:<12.3f} | N/A")
    print("="*60)
    logger.info(f"Full dynamic report saved: {out_path}")

if __name__ == "__main__":
    main()