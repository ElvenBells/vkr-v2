import torch

# Загружаем веса (map_location='cpu' чтобы не ругался на отсутствие GPU)
ckpt = torch.load("models/best1e.pt", map_location="cpu", weights_only=False)

print("🔑 Ключи в файле:", ckpt.keys())

# Вытаскиваем метрики последней эпохи
if "train_metrics" in ckpt:
    metrics = ckpt["train_metrics"]
    print("\n📊 Метрики внутри модели:")
    for k, v in metrics.items():
        print(f"  - {k}: {round(v, 4)}")
        
if "epoch" in ckpt:
    print(f"\n🔄 Модель остановилась на эпохе: {ckpt['epoch']}")