# Спецификация инжекции дефектов (Defect Injection Specs)

## Методология
Все дефекты инжектируются в статический HTML/CSS/JS до рендеринга. Скриншоты делаются через Playwright (Chromium, 1920x1080). Ground Truth фиксирует тип дефекта и ожидаемую реакцию системы.

## Типы дефектов (≥8)
| ID | Название | Метод инжекции | Ожидаемый эффект | CV-признак |
|----|----------|----------------|------------------|------------|
| 1 | `missing_element` | Удаление DOM-узла `<button>` | Потеря интерактивности | YOLO: `class_count ↓`, Oracle: `layout shift` |
| 2 | `wrong_color` | CSS override `background:#ff0000` | Визуальный контраст | Oracle: `SSIM ↓`, `color histogram shift` |
| 3 | `broken_layout` | CSS `transform:rotate(2deg) scale(0.95)` | Искажение геометрии | Oracle: `bbox alignment ↑`, YOLO: `spatial drift` |
| 4 | `text_overflow` | CSS `width:50px; overflow:hidden` | Обрезка контента | OCR: `text length ↓`, Oracle: `local SSIM ↓` |
| 5 | `misalignment` | CSS `margin-left:150px` | Смещение блока | Oracle: `spatial_distribution change` |
| 6 | `wrong_text` | Замена строки `Products → Pr0ducts_#ERR` | Контентная регрессия | OCR: `levenshtein ↑`, `similarity ↓` |
| 7 | `missing_image` | Удаление `<img>` тега | Пустая область | Oracle: `texture loss`, YOLO: `image class ↓` |
| 8 | `broken_interaction` | JS `disabled=true` | Неотзывчивость UI | CV: `visual ok`, PW: `assertion fail` |

## Воспроизводимость
1. Запустите `python scripts/run_experiment.py --generate`
2. Артефакты сохраняются в `benchmarks/sites/*/screenshots/`
3. GT загружается из `benchmarks/ground_truth/defects_ground_truth.json`
4. Все параметры вынесены в `configs/config.json`