# Видеостудия

Короткометражка, мультфильм, реклама, клип или длинный ролик собираются кодом. Агент пишет сцены и звук, студия отдаёт готовый MP4.

Картинка — это страница, в которой каждый кадр считается из времени: холст, плоские слои или сетка из треугольников. Chrome снимает кадры, Python собирает музыку, шумы и озвучку, ffmpeg сводит дорожку примерно к −14 LUFS.

Два режима:

- **Quick** — один файл `film.html`, несколько вопросов, черновик и финал. Для роликов примерно до минуты.
- **Film** — план, сценарий, пробный кадр, аниматик и главы. Главы склеиваются в один ролик, в том числе длиннее десяти минут.

Вид картинки: кинематографичный, пластилин, аниме, книжка, бумажная аппликация, VHS, глянцевая реклама, тушь.

## Что уже лежит в репозитории

`films/paper-boat/` — ночная гавань и бумажный кораблик, 10 секунд, 1280×720, пластилин. Готовый файл: `films/paper-boat/paper-boat.mp4`.

Посмотреть страницу в браузере:

```bash
node studio/capture.mjs --serve
```

Адрес будет в выводе команды, страница `films/paper-boat/film.html`.

## Собрать ролик

Нужны Node.js 22, Python 3, ffmpeg и Chrome. Озвучка по умолчанию — eSpeak NG. Чужой ключ не обязателен.

```bash
pip install -r requirements.txt
python3 studio/init_film.py harbor --title "Гавань" --look cinematic --seconds 8
python3 studio/render.py stills films/harbor --at 1,4
python3 studio/render.py draft films/harbor
python3 studio/render.py final films/harbor
```

Финальный файл появляется рядом со страницами фильма: `films/harbor/harbor.mp4`.

Для длинного фильма инициализация с `--mode film` создаёт первую главу в `chapters/01`. Готовые главы склеиваются так:

```bash
python3 studio/render.py concat films/show/chapters/01/01.mp4 films/show/chapters/02/02.mp4 --out films/show/show.mp4
```

Свои ключи ElevenLabs, если они нужны отдельной реплике, записываются в `.env`. Имена полей лежат в `EnvExample`. В чат ключ копировать не нужно. Пока у реплики не стоит `engine: "elevenlabs"`, студия говорит голосом eSpeak NG.

Проверка:

```bash
python3 -m unittest tests/test_studio.py
```

Агенту, который будет снимать следующий ролик, достаточно открыть `.cursor/skills/videomaker/SKILL.md`.
