# fal.ai: ілюстрації для рілса 2026-10-26

Підключення: fal MCP (акаунт Лаліти, вхід через OAuth, ключ ніде не записаний).
Модель обрана через `recommend_model` (текст у картинку, 9:16, пріоритет ціна): `bria/fibo-2/generate`, $0.04 за зображення.
Оцінка до генерації (`estimate_cost`): 6 зображень = $0.24, ліміт $1. Згенеровано 5, спершу 1 тестове.
**Разом витрачено: 5 × $0.04 = $0.20.**

Дата генерації: 2026-10-27. Розмір оригіналів 792x1408.

Спільний хвіст промту (стиль):
> Flat editorial illustration, bold ink outline, sticker style, limited palette teal #89b7b0, mint green #5dc7a0, off-white #f4f4ef, near-black #0c0f0e, small yellow #e3bc5b accent, halftone dot texture, clean vector look, plain solid off-white background, centered object with empty margins around it, no text, no letters, no numbers, no logos, no people, no hands

| # | Файл | Що | Промт (початок, далі спільний хвіст) | Seed | Вартість | У рілсі |
|---|---|---|---|---|---|---|
| 1 | `01-notebook.png` | відкритий зошит | A single open notebook seen from slightly above, pages filled with abstract wavy scribble lines with no readable letters, a pencil lying across it. | 2610 | $0.04 | так, сцена 2 (кейс), 3-10 с |
| 2 | `02-flashcards.png` | картки для вивчення мов | A small loose stack of three blank language-learning flashcards, slightly fanned and tilted, each card blank or with only abstract short stroke marks, no readable letters. | 2611 | $0.04 | так, сцена 2 (кейс), 3-10 с |
| 3 | `03-headphones-laptop.png` | навушники й ноутбук | Over-ear headphones resting next to an open laptop, the laptop screen shows only abstract wavy lines and simple shapes, no readable text, no interface. (+ no brand marks) | 2612 | $0.04 | так, «цифровий продукт без ФОП», 14-18 с |
| 4 | `04-speech-bubbles.png` | дві бульбашки діалогу | Two overlapping empty speech bubbles as pure graphic shapes, one mint green and one teal, rounded with small tails, completely empty inside, no text. | 2613 | $0.04 | так, «те, що ти вже вмієш пояснювати», 10-14 с |
| 5 | `05-star.png` | наклейка-зірка | A single chunky five-pointed star sticker in yellow with a mint green inner star and a few small abstract sparkle marks around it, graphic badge shape. | 2614 | $0.04 | так, заклик, 18-22 с |

Ендпоінт для всіх: `bria/fibo-2/generate`, параметри `aspect_ratio: "9:16"`, `seed` з таблиці.

## Перевірка
- Тексту, літер, логотипів немає (на картках і екрані ноутбука лише абстрактні штрихи).
- Облич і постатей немає. Скриншотів платежів, графіків доходу, відгуків, лічильників продажів немає.
- Усе це ілюстративний декор, не доказ кейсу.

## Обробка
- Оригінали 792x1408 лежать у `raw/*.png` (спершу мережа сесії не пускала до fal CDN і рілс збирався з превʼю 432x768; після відкриття доступу стікери перевирізано з оригіналів).
- Фон вирізано локально: `source/cutout.py` (заливка фону від країв, м'який край, обрізка). Окремий `background-removal` у fal не викликався, $0.
- Перевирізати: `python3 source/cutout.py assets/fal/raw/*.png --out assets/fal`, потім перезібрати рілс.

## Оригінали на fal CDN
1. https://v3b.fal.media/files/b/0ab009a7/plIW_6zCV9M3-LztBY4c__b7a0775afa114b609f97b2d688cdf92f.png
2. https://v3b.fal.media/files/b/0ab009b0/zJHG7HZEKyvWYriF6LsVS_4d7fce35c91047fdad73fd445d9b9ec4.png
3. https://v3b.fal.media/files/b/0ab009b0/l0QsUTVMspUPTZ6TUgGyh_5f8ed000ea5a4f2a8c400cbdd6df6661.png
4. https://v3b.fal.media/files/b/0ab009b0/NcEnYMZ9u9aFfihhxO9b__90609b6ec9df4d6a92a865a4abbf31de.png
5. https://v3b.fal.media/files/b/0ab009b0/JXaqQQ6SuznCqPco1EZoe_fd0307e7bbc84cdca6e9db5f693a6aa4.png
