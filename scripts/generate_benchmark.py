# scripts/generate_benchmark.py
from __future__ import annotations
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any
import playwright.sync_api as pw
from loguru import logger

# Пути к исходным HTML-файлам
SITE_SOURCES = {
    "ecommerce": "benchmarks/sites/ecommerce/source/index.html",
    "dashboard": "benchmarks/sites/dashboard/source/index.html",
    "crm": "benchmarks/sites/crm/source/index.html",
    "admin": "benchmarks/sites/admin/source/index.html",
    "booking": "benchmarks/sites/booking/source/index.html",
}

# Функции инжекции дефектов (универсальные, работают с любым HTML)
DEFECT_INJECTIONS = {
    "missing_element": lambda html: html.replace('<button', '<span')
                                      .replace('<input', '<span'),
    # ИСПРАВЛЕНО: Убрано ошибочное дублирование "+ html" в первой ветке replace
    "wrong_color": lambda html: html.replace('</head>', 
        '<style>.button,.btn,[class*="button"]{background:#ff0000 !important;color:#fff !important;}</style></head>')
        if '</head>' in html else '<style>.button{background:#f00 !important;}</style>' + html,
    "broken_layout": lambda html: html.replace('<body>', '<body style="transform:rotate(1.5deg) scale(0.98);">'),
    "text_overflow": lambda html: html.replace('<h1>', '<h1 style="width:80px;overflow:hidden;white-space:nowrap;">')
                                    .replace('<title>', '<title>[TRUNCATED] '),
    "misalignment": lambda html: html.replace('<main>', '<main style="margin-left:120px;">')
                                   .replace('<div class="container"', '<div class="container" style="padding-left:100px;"'),
    "wrong_text": lambda html: html.replace('Confirm', 'C0nfirm_#ERR')
                                  .replace('Submit', 'Subm1t_#ERR')
                                  .replace('Save', 'S@ve_#ERR'),
    "missing_image": lambda html: html.replace('<img', '<div')
                                     .replace('src=', 'data-src='),
    "broken_interaction": lambda html: html + '<script>document.querySelectorAll("button,input,select,textarea,a").forEach(el=>{if(el.tagName!=="A"||el.href!=="#"){el.disabled=true;el.style.pointerEvents="none";el.style.opacity="0.6";}});</script>'
}

def generate_benchmark(output_dir: str = "benchmarks"):
    out = Path(output_dir)
    gt_dir = out / "ground_truth"
    out.mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)

    ground_truth = {}

    with pw.sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-gpu", "--no-sandbox"])
        context = browser.new_context(viewport={"width": 1920, "height": 1080})

        for site_name, source_path in SITE_SOURCES.items():
            source_file = Path(source_path)
            if not source_file.exists():
                logger.warning(f"⚠️ Source not found: {source_file}. Skipping site '{site_name}'.")
                continue
                
            with open(source_file, "r", encoding="utf-8") as f:
                base_html = f.read()
            
            site_dir = out / "sites" / site_name / "screenshots"
            ref_dir = site_dir / "reference"
            test_dir = site_dir / "defected"
            ref_dir.mkdir(parents=True, exist_ok=True)
            test_dir.mkdir(parents=True, exist_ok=True)

            # Сохраняем и загружаем референсную версию
            ref_html_path = site_dir / "reference" / "index.html"
            with open(ref_html_path, "w", encoding="utf-8") as f:
                f.write(base_html)
            
            page = context.new_page()
            page.goto(f"file:///{ref_html_path.resolve().as_posix()}")
            page.wait_for_load_state("networkidle")
            ref_path = ref_dir / "baseline.png"
            page.screenshot(path=str(ref_path))
            logger.info(f"✅ Reference: {ref_path}")

            site_gt = []
            for defect_name, inject_fn in DEFECT_INJECTIONS.items():
                try:
                    mutated_html = inject_fn(base_html)
                    test_html_path = test_dir / f"{defect_name}.html"
                    with open(test_html_path, "w", encoding="utf-8") as f:
                        f.write(mutated_html)
                    
                    page.goto(f"file:///{test_html_path.resolve().as_posix()}")
                    page.wait_for_load_state("networkidle")
                    test_path = test_dir / f"{defect_name}.png"
                    page.screenshot(path=str(test_path))

                    site_gt.append({
                        "site": site_name,
                        "defect_type": defect_name,
                        "ref_screenshot": str(ref_path),
                        "test_screenshot": str(test_path),
                        "expected_severity": "high" if defect_name in ["missing_element", "wrong_text", "broken_interaction"] else "medium",
                        "gt_bbox": {"x1": 100, "y1": 100, "x2": 1800, "y2": 900}
                    })
                    logger.info(f"🔧 Injected {defect_name} → {test_path}")
                except Exception as e:
                    logger.error(f"❌ Failed to inject {defect_name} for {site_name}: {e}")
                    continue

            ground_truth[site_name] = site_gt
            logger.info(f"🎯 Site '{site_name}' complete: {len(site_gt)} defects")

        browser.close()

    gt_path = gt_dir / "defects_ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2, ensure_ascii=False)
    logger.info(f"💾 Ground Truth saved: {gt_path}")
    return ground_truth

if __name__ == "__main__":
    generate_benchmark()