# scripts/run_experiment.py
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

from src.orchestrator import ExperimentOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Run full CV-AI vs Playwright experiment")
    parser.add_argument("--generate", action="store_true", help="Generate benchmark & defects first")
    parser.add_argument("--config", default="configs/config.json", help="Path to config")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO", 
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

    if args.generate:
        logger.info("📦 Generating synthetic benchmark & injecting defects...")
        from scripts.generate_benchmark import generate_benchmark
        generate_benchmark()
        logger.info("✅ Benchmark generation complete")

    logger.info("🧠 Starting experiment orchestrator...")
    orch = ExperimentOrchestrator(args.config)
    report = orch.run_comparison()

    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    out_path = reports_dir / "comparison_metrics.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    m = report
    print("\n" + "="*60)
    print("📊 COMPARATIVE EXPERIMENT RESULTS")
    print("="*60)
    print(f"{'Metric':<20} | {'CV-AI Agent':<12} | {'Playwright':<12}")
    print("-"*60)
    print(f"{'F1-Score':<20} | {m['cv_metrics']['f1']:<12.4f} | {m['pw_metrics']['f1']:<12.4f}")
    print(f"{'Precision':<20} | {m['cv_metrics']['precision']:<12.4f} | {m['pw_metrics']['precision']:<12.4f}")
    print(f"{'Recall (DDR)':<20} | {m['cv_metrics']['recall']:<12.4f} | {m['pw_metrics']['recall']:<12.4f}")
    print(f"{'False Alarm Rate':<20} | {m['cv_metrics']['far']:<12.4f} | {m['pw_metrics']['far']:<12.4f}")
    print(f"{'Avg Time (s)':<20} | {np.mean([r['time_s'] for r in m['cv_results']]):<12.3f} | {np.mean([r['time_s'] for r in m['pw_results']]):<12.3f}")
    print(f"{'Overhead (x)':<20} | {m['cv_overhead_x']:<12.2f} | 1.00")
    print(f"{'Optimal Threshold':<20} | {m['optimized_cv_threshold']:<12.3f} | N/A")
    print("="*60)
    logger.info(f"Full report saved: {out_path}")


if __name__ == "__main__":
    main()