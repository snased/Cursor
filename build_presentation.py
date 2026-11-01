#!/usr/bin/env python3
"""Conference slides for the article on long-term Orthodox accompaniment of couples."""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

W = Inches(13.333)
H = Inches(7.5)

WINE = RGBColor(0x5C, 0x2A, 0x33)
WINE_DEEP = RGBColor(0x3E, 0x1C, 0x24)
INK = RGBColor(0x2A, 0x24, 0x1F)
MUTED = RGBColor(0x6E, 0x62, 0x58)
CREAM = RGBColor(0xF6, 0xF1, 0xE8)
CARD = RGBColor(0xFF, 0xFC, 0xF8)
GOLD = RGBColor(0xA6, 0x84, 0x45)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xE4, 0xD8, 0xC8)

SERIF = "Liberation Serif"
SANS = "Liberation Sans"


def set_run_font(run, name, size, color, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.italic = False
    rpr = run._r.get_or_add_rPr()
    for tag in ("latin", "cs", "ea"):
        node = rpr.find(qn(f"a:{tag}"))
        if node is None:
            node = rpr.makeelement(qn(f"a:{tag}"), {})
            rpr.append(node)
        node.set("typeface", name)


def add_rect(slide, l, t, w, h, fill):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()
    return shape


def add_text(slide, l, t, w, h, text, font, size, color, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    try:
        tf._txBody.bodyPr.set("anchor", {MSO_ANCHOR.TOP: "t", MSO_ANCHOR.MIDDLE: "ctr", MSO_ANCHOR.BOTTOM: "b"}[anchor])
    except Exception:
        pass
    p = tf.paragraphs[0]
    p.alignment = align
    p.space_before = Pt(0)
    p.space_after = Pt(0)
    run = p.add_run()
    run.text = text
    set_run_font(run, font, size, color, bold)
    return box


def add_bullets(slide, l, t, w, h, items, size=20, color=INK, spacing=10):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.level = 0
        p.space_before = Pt(spacing if i else 0)
        p.space_after = Pt(0)
        run = p.add_run()
        run.text = item
        set_run_font(run, SANS, size, color, False)
    return box


def chrome(slide, kicker, number, total):
    add_rect(slide, 0, 0, W, H, CREAM)
    add_rect(slide, 0, 0, Inches(0.12), H, WINE)
    add_text(slide, Inches(0.55), Inches(0.28), Inches(10.5), Inches(0.32), kicker.upper(), SANS, 12, GOLD, True)
    add_rect(slide, Inches(0.55), Inches(7.15), Inches(12.2), Inches(0.01), LINE)
    add_text(
        slide,
        Inches(0.55),
        Inches(7.18),
        Inches(10.2),
        Inches(0.28),
        "Смысловое призвание и социальное устроение семьи",
        SANS,
        11,
        MUTED,
    )
    add_text(
        slide,
        Inches(11.3),
        Inches(7.18),
        Inches(1.5),
        Inches(0.28),
        f"{number}  /  {total}",
        SANS,
        11,
        MUTED,
        align=PP_ALIGN.RIGHT,
    )


def title_block(slide, title, top=0.58, height=1.15):
    add_text(slide, Inches(0.55), Inches(top), Inches(12.2), Inches(height), title, SERIF, 32, INK, True)


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def build():
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    prs.core_properties.title = (
        "Смысловое призвание и социальное устроение семьи: "
        "задачи православного психолога в долгосрочном сопровождении супругов"
    )
    prs.core_properties.subject = "Доклад по статье для конференции по православной психологии"
    blank = prs.slide_layouts[6]
    total = 16

    # 1. Title
    s = prs.slides.add_slide(blank)
    add_rect(s, 0, 0, W, H, WINE_DEEP)
    add_rect(s, 0, 0, Inches(0.18), H, GOLD)
    add_text(s, Inches(0.75), Inches(1.35), Inches(11.5), Inches(0.35), "КОНФЕРЕНЦИЯ ПО ПРАВОСЛАВНОЙ ПСИХОЛОГИИ", SANS, 14, GOLD, True)
    add_text(
        s,
        Inches(0.75),
        Inches(1.9),
        Inches(11.6),
        Inches(2.3),
        "Смысловое призвание\nи социальное устроение семьи",
        SERIF,
        40,
        WHITE,
        True,
    )
    add_text(
        s,
        Inches(0.75),
        Inches(4.4),
        Inches(11.2),
        Inches(0.9),
        "Задачи православного психолога\nв долгосрочном сопровождении супругов",
        SANS,
        22,
        RGBColor(0xF0, 0xE4, 0xD4),
    )
    add_rect(s, Inches(0.75), Inches(5.55), Inches(2.1), Inches(0.035), GOLD)
    add_text(s, Inches(0.75), Inches(5.8), Inches(11), Inches(0.7), "Доклад по статье\nМесто для имени докладчика и аффилиации", SANS, 16, RGBColor(0xE4, 0xD4, 0xC4))
    notes(s, "Открыть темой: долгий брак держится согласием лиц и повторяемым трудом общения. Дом — малая церковь как цель, а не готовый устав.")

    slides_meta = []

    def new(kicker):
        slide = prs.slides.add_slide(blank)
        n = len(prs.slides)
        chrome(slide, kicker, n, total)
        return slide

    # 2
    s = new("Постановка")
    title_block(s, "Два дефицита, с которыми приходит пара")
    add_text(
        s,
        Inches(0.55),
        Inches(1.85),
        Inches(12.2),
        Inches(0.7),
        "Запрос звучит бытовым языком: усталость, обида, охлаждение, деньги, родители, дети, разная вера.",
        SANS,
        18,
        MUTED,
    )
    cards = [
        ("Смысловой", "Пара умеет обсуждать расписание и уже плохо понимает, зачем она вместе, помимо привычки и функции."),
        ("Социальный", "Дом, род, труд, приход и дружба устроены так, что один несёт скрытую тяжесть, а другой выпадает из общего дела."),
    ]
    for i, (h, body) in enumerate(cards):
        x = Inches(0.55 + i * 6.3)
        add_rect(s, x, Inches(2.8), Inches(5.95), Inches(3.5), CARD)
        add_rect(s, x, Inches(2.8), Inches(0.1), Inches(3.5), GOLD)
        add_text(s, x + Inches(0.4), Inches(3.1), Inches(5.2), Inches(0.6), h, SERIF, 26, WINE, True)
        add_text(s, x + Inches(0.4), Inches(3.9), Inches(5.2), Inches(2.0), body, SANS, 18, INK)
    notes(s, "Смысл без уклада остаётся настроением. Уклад без вопроса о призвании становится обслуживанием быта. Помощь отвечает на оба дефицита сразу.")

    # 3
    s = new("Метод")
    title_block(s, "Два языка одной работы")
    rows = [
        ("Православная антропология", "Достоинство лица, цель пути, различение духовных состояний. Горизонт — таинство брака и свобода супругов."),
        ("Психология", "Способы переживать, говорить, делить труд и восстанавливать контакт. Сатир и Зинкер входят как инструменты наблюдения."),
        ("Малая церковь", "Место общей молитвы, терпения, гостеприимства и воспитания. Для психолога это цель, а не бытовой регламент."),
    ]
    for i, (h, body) in enumerate(rows):
        y = Inches(2.05 + i * 1.55)
        add_rect(s, Inches(0.55), y, Inches(12.2), Inches(1.4), CARD)
        add_text(s, Inches(0.85), y + Inches(0.22), Inches(11.6), Inches(0.4), h, SERIF, 22, WINE, True)
        add_text(s, Inches(0.85), y + Inches(0.7), Inches(11.6), Inches(0.55), body, SANS, 16, INK)
    notes(s, "Психолог создаёт условия, в которых пара узнаёт дар брака в реальной истории: в прощении, дележе труда, болезни, детях, верности в пустыне.")

    # 4
    s = new("Антропология")
    title_block(s, "Образ дан. Подобие возрастает")
    add_bullets(
        s,
        Inches(0.55),
        Inches(2.05),
        Inches(12.2),
        Inches(4.6),
        [
            "Образ Божий — достоинство каждого супруга, которое нельзя отменить усталостью.",
            "Подобие — путь: любовь, свобода и рассуждение растут во времени, а не выдаются в день венчания.",
            "Брак — школа личности: предел терпения, страх близости, способность прощать.",
            "Лицо живёт в общении. В браке другого легко сделать функцией своего покоя.",
            "Любовь собирает привязанность, желание, дружбу и любовь-решение. Заповедь задаёт им направление: другой есть лицо.",
            "Служение мужа — любовь до самоотдачи. Слово о браке открывается взаимным повиновением во Христе.",
        ],
        size=18,
        spacing=8,
    )
    notes(s, "Антоний Сурожский: в браке человека любят в правде и дают ему расти, включая жизнь за пределами самой четы.")

    # 5
    s = new("Антропология")
    title_block(s, "Увидеть цикл раньше, чем он станет характером")
    pairs = [
        ("Преследует и укоряет", "Отстраняется"),
        ("Несёт тревогу за весь дом", "Гасит вину работой или экраном"),
    ]
    for i, (a, b) in enumerate(pairs):
        y = Inches(2.05 + i * 1.15)
        add_rect(s, Inches(0.55), y, Inches(5.7), Inches(0.95), CARD)
        add_rect(s, Inches(7.05), y, Inches(5.7), Inches(0.95), CARD)
        add_text(s, Inches(0.75), y + Inches(0.25), Inches(5.3), Inches(0.5), a, SANS, 18, INK, True)
        add_text(s, Inches(7.25), y + Inches(0.25), Inches(5.3), Inches(0.5), b, SANS, 18, INK, True)
    add_rect(s, Inches(0.55), Inches(4.5), Inches(12.2), Inches(2.2), WINE)
    add_text(s, Inches(0.85), Inches(4.7), Inches(11.6), Inches(0.4), "Два имени одной паузы", SERIF, 20, GOLD, True)
    add_text(
        s,
        Inches(0.85),
        Inches(5.2),
        Inches(11.6),
        Inches(1.2),
        "Трезвение — заметить движение сердца до ранящего слова.\nПауза в консультации — ответственность за свой вклад в ссору.\nРассуждение различает рану, истощение, несправедливую нагрузку, депрессию и различие темпераментов.",
        SANS,
        16,
        WHITE,
    )
    notes(s, "Рассуждение бережёт пару: где нужен новый порядок дел, там мало требования «поработай над собой»; где болит смысл, там мало бытового договора.")

    # 6
    s = new("Смысл")
    title_block(s, "Собрать собственное предание пары")
    add_text(
        s,
        Inches(0.55),
        Inches(1.8),
        Inches(12.2),
        Inches(0.7),
        "Цель брака — исцеление любви. Благополучие остаётся важным плодом, а не единственной мерой.",
        SANS,
        18,
        MUTED,
    )
    qs = [
        "Откуда у каждого образ мужа, жены, отца и матери?",
        "Какой момент до сих пор считается началом «нас»?",
        "Где уже была верность, даже под другим именем?",
        "Какое общее дело делает союз нужным не только двоим?",
    ]
    for i, q in enumerate(qs):
        col = i % 2
        row = i // 2
        x = Inches(0.55 + col * 6.3)
        y = Inches(2.7 + row * 1.9)
        add_rect(s, x, y, Inches(5.95), Inches(1.7), CARD)
        add_text(s, x + Inches(0.3), y + Inches(0.28), Inches(0.6), Inches(0.45), f"0{i+1}", SERIF, 20, GOLD, True)
        add_text(s, x + Inches(1.0), y + Inches(0.4), Inches(4.6), Inches(1.0), q, SANS, 18, INK)
    notes(s, "Покаяние звучит конкретно: «я обесценил твой труд», «я ушёл в молчание». Общее обвинение в бездуховности закрывает достоинство другого.")

    # 7
    s = new("Смысл")
    title_block(s, "Когда привычный сюжет ломается")
    add_bullets(
        s,
        Inches(0.55),
        Inches(2.0),
        Inches(7.4),
        Inches(4.6),
        [
            "Бесплодие и потеря ребёнка",
            "Болезнь",
            "Жизнь вместе до венчания",
            "Разные веры супругов",
            "Одиночество после ухода детей",
            "Вера одного, в которой второй слышит соперника",
        ],
        size=22,
        spacing=14,
    )
    add_rect(s, Inches(8.2), Inches(2.05), Inches(4.55), Inches(4.4), WINE)
    add_text(s, Inches(8.5), Inches(2.4), Inches(4.05), Inches(1.3), "Призвание\nузнаётся\nв реальных лицах", SERIF, 26, WHITE, True)
    add_text(
        s,
        Inches(8.5),
        Inches(4.3),
        Inches(4.05),
        Inches(1.7),
        "Верность, взаимное служение и открытость к жизни остаются возможными и в таком доме.",
        SANS,
        16,
        RGBColor(0xF3, 0xE6, 0xD8),
    )
    notes(s, "Психолог удерживает достоинство пути, который не совпал с ожидаемым образцом. Духовная жизнь совершается в том доме, который уже есть.")

    # 8
    s = new("Социальное устроение")
    title_block(s, "Любовь становится видимой в порядке дней")
    items = [
        ("Труд", "Невидимая память о врачах, школе, родственниках и настроении дома. Правда нагрузки важнее симметрии каждой задачи."),
        ("Деньги", "Общие цели, порог крупной траты, небольшая личная свобода без отчёта за мелочь. Тайная жизнь денег разрушает общение."),
        ("Род", "Почитание родителей сохраняется. Новый дом говорит: «мы так решили». Помощь родителей и управление браком — разные вещи."),
        ("Приход и дети", "Дом умеет открыть стол. Супруги остаются союзом перед ребёнком. У пары есть собственное время и собственная нежность."),
    ]
    for i, (h, body) in enumerate(items):
        col = i % 2
        row = i // 2
        x = Inches(0.55 + col * 6.3)
        y = Inches(2.0 + row * 2.35)
        add_rect(s, x, y, Inches(5.95), Inches(2.15), CARD)
        add_text(s, x + Inches(0.35), y + Inches(0.25), Inches(5.3), Inches(0.45), h, SERIF, 22, WINE, True)
        add_text(s, x + Inches(0.35), y + Inches(0.8), Inches(5.3), Inches(1.15), body, SANS, 15, INK)
    notes(s, "Устойчивые пары замечают обращения друг к другу и чинят разрыв вскоре после ссоры. В языке малой церкви это названная вина, принятая просьба и возвращение за один стол.")

    # 9
    s = new("Сатир")
    title_block(s, "Семья как мастерская, где создаются люди")
    add_text(s, Inches(0.55), Inches(1.8), Inches(12.2), Inches(0.45), "Вирджиния Сатир. Основание брака — самоценность каждого.", SANS, 18, MUTED)
    modes = [
        ("Угождает", "Стирает свою правду"),
        ("Обвиняет", "Стирает правду другого"),
        ("Рассудочен", "Гасит чувство"),
        ("Смещает разговор", "Важное тонет в шуме"),
    ]
    for i, (h, body) in enumerate(modes):
        x = Inches(0.55 + i * 3.15)
        add_rect(s, x, Inches(2.45), Inches(3.0), Inches(1.7), CARD)
        add_text(s, x + Inches(0.2), Inches(2.6), Inches(2.6), Inches(0.7), h, SERIF, 18, WINE, True)
        add_text(s, x + Inches(0.2), Inches(3.3), Inches(2.6), Inches(0.6), body, SANS, 14, INK)
    add_text(s, Inches(0.55), Inches(4.4), Inches(12.2), Inches(0.4), "Пять свобод в семье", SERIF, 20, INK, True)
    add_text(
        s,
        Inches(0.55),
        Inches(4.95),
        Inches(12.2),
        Inches(1.5),
        "Видеть то, что есть. Сказать то, что думаешь и чувствуешь. Чувствовать то, что чувствуешь.\nПросить о нужном. Рискнуть быть собой рядом с другим.\nСогласованная речь: слова, чувства и ситуация говорят об одном. Хаос после нового события — этап роста, а не конец союза.",
        SANS,
        18,
        INK,
    )
    notes(s, "За годы защита затвердевает в роли: миротворец, прокурор дома, наблюдатель собственной жизни. Самоценность созвучна достоинству образа. Подобие растит её к общению.")

    # 10
    s = new("Зинкер")
    title_block(s, "Супружество — живая форма на границе контакта")
    add_text(
        s,
        Inches(0.55),
        Inches(1.85),
        Inches(12.2),
        Inches(0.7),
        "Ритм живой пары: приближение, встреча, расхождение и отдых, затем новая встреча. Само супружество — третье, и его тоже кормят вниманием.",
        SANS,
        18,
        INK,
    )
    fails = [
        ("Слияние", "Различия стёрты: спрашивать друг друга уже незачем."),
        ("Обрыв", "Двое живут в одном доме без встречи."),
        ("Застывшие роли", "Один навсегда несёт порядок, другой — живость; один — веру, другой — силу."),
    ]
    for i, (h, body) in enumerate(fails):
        y = Inches(2.75 + i * 1.25)
        add_rect(s, Inches(0.55), y, Inches(12.2), Inches(1.1), CARD)
        add_text(s, Inches(0.85), y + Inches(0.15), Inches(3.2), Inches(0.75), h, SERIF, 20, WINE, True, anchor=MSO_ANCHOR.MIDDLE)
        add_text(s, Inches(4.2), y + Inches(0.22), Inches(8.2), Inches(0.7), body, SANS, 18, INK)
    notes(s, "Хорошая форма: ясность, взаимная опора и красота живого обмена. Новый опыт возможен там, где человека уже слышат. Обет верности задаёт время, внутри которого форма созревает.")

    # 11
    s = new("Границы")
    title_block(s, "Психолог и духовник держат разные служения")
    left = [
        "Психолог исследует переживание, речь, смысл, историю и порядок общих дел.",
        "Молитва в кабинете возможна по желанию обоих и только кратко.",
        "Священнику, по согласию обоих, передаётся рамка темы, а не содержание исповеди и не пересказ терапии.",
    ]
    right = [
        "Исповедь, правило, оценка греха и допуск к таинствам принадлежат духовнику.",
        "Унижение, слежка, запреты, угрозы, удары и принуждение требуют безопасности.",
        "Депрессия, зависимость, послеродовое расстройство и риск для жизни требуют врача.",
    ]
    add_rect(s, Inches(0.55), Inches(2.0), Inches(6.0), Inches(4.6), CARD)
    add_rect(s, Inches(6.8), Inches(2.0), Inches(6.0), Inches(4.6), WINE)
    add_text(s, Inches(0.85), Inches(2.2), Inches(5.4), Inches(0.45), "Дело консультации", SERIF, 20, WINE, True)
    add_text(s, Inches(7.1), Inches(2.2), Inches(5.4), Inches(0.45), "Порог, который не пересекают", SERIF, 20, GOLD, True)
    add_bullets(s, Inches(0.85), Inches(2.85), Inches(5.4), Inches(3.4), left, size=16, spacing=12)
    add_bullets(s, Inches(7.1), Inches(2.85), Inches(5.4), Inches(3.4), right, size=16, color=WHITE, spacing=12)
    notes(s, "Терпение есть усилие любви между двумя свободными людьми. Оно предполагает голос и защиту каждого. Достоинство образа Божия задаёт этот порог.")

    # 12
    s = new("Сопровождение")
    title_block(s, "8–12 встреч, затем жизнь без кабинета")
    steps = [
        ("1–2", "Договор, безопасность, история пары, места верности и обрыва."),
        ("3–6", "Призвание этого года, родительские образы любви, правило дома."),
        ("7–12", "Дневник, недельный час, карта труда, круг родных и прихода."),
        ("Далее", "Сезонные встречи. Долгосрочность держат домашние чины."),
    ]
    for i, (n, body) in enumerate(steps):
        y = Inches(2.0 + i * 1.15)
        add_rect(s, Inches(0.55), y, Inches(1.5), Inches(0.95), WINE)
        add_text(s, Inches(0.55), y + Inches(0.22), Inches(1.5), Inches(0.55), n, SERIF, 18, WHITE, True, align=PP_ALIGN.CENTER)
        add_rect(s, Inches(2.2), y, Inches(10.55), Inches(0.95), CARD)
        add_text(s, Inches(2.5), y + Inches(0.22), Inches(10.0), Inches(0.55), body, SANS, 18, INK)
    notes(s, "Ответы записываются словами пары. Если супруги сами говорят о молитве, прощении и венчании, эти слова связываются с конкретным поступком недели.")

    # 13
    s = new("Домашние чины")
    title_block(s, "Дневник семьи и час, который повторяется")
    add_rect(s, Inches(0.55), Inches(1.95), Inches(6.0), Inches(4.7), CARD)
    add_text(s, Inches(0.85), Inches(2.15), Inches(5.4), Inches(0.45), "Пять строк вечером", SERIF, 22, WINE, True)
    add_bullets(
        s,
        Inches(0.85),
        Inches(2.8),
        Inches(5.4),
        Inches(3.5),
        [
            "За что я благодарен тебе и Богу",
            "Что сегодня было важным",
            "Что я при этом чувствовал",
            "О чём я прошу",
            "Какое малое дело заботы получилось",
        ],
        size=18,
        spacing=8,
    )
    add_rect(s, Inches(6.8), Inches(1.95), Inches(6.0), Inches(4.7), CARD)
    add_text(s, Inches(7.1), Inches(2.15), Inches(5.4), Inches(0.45), "Как читают", SERIF, 22, WINE, True)
    add_bullets(
        s,
        Inches(7.1),
        Inches(2.8),
        Inches(5.4),
        Inches(3.5),
        [
            "Раз в неделю, в один и тот же час",
            "Сначала повторить услышанное",
            "Спор переносится на другой день",
            "Сокровенное остаётся в молитве и на исповеди",
            "При страхе и контроле тетрадь откладывается",
        ],
        size=18,
        spacing=8,
    )
    notes(s, "Раз в квартал из тетради выписывают три радости и три боли. В годовщину дневник читается как память верности, включая трудные месяцы.")

    # 14
    s = new("Домашние чины")
    title_block(s, "День, неделя, месяц и год")
    rites = [
        ("Неделя", "Замер температуры по Сатир: благодарность, опасение, жалоба с просьбой, новость, надежда. Затем одно решение: кто, что и к какому сроку."),
        ("День", "Порог на десять–пятнадцать минут. Где сегодня было трудно и где было хорошо."),
        ("Месяц", "Короткое письмо: каким я вижу тебя, что ценю и о чём прошу. Письмо читают вслух."),
        ("Год", "В какой роли я застыл. Какую свою сторону отдал тебе. Какой один способ встречаться берём дальше."),
    ]
    for i, (h, body) in enumerate(rites):
        y = Inches(1.9 + i * 1.2)
        add_rect(s, Inches(0.55), y, Inches(2.0), Inches(1.05), WINE)
        add_text(s, Inches(0.55), y + Inches(0.28), Inches(2.0), Inches(0.5), h, SERIF, 18, WHITE, True, align=PP_ALIGN.CENTER)
        add_text(s, Inches(2.8), y + Inches(0.12), Inches(9.9), Inches(0.85), body, SANS, 16, INK)
    notes(s, "Эксперимент контакта по Зинкеру — один на неделю и маленький. Кто молчит, называет обиду и остаётся. Кто говорит за двоих, минуту повторяет слова другого. Сначала опора, потом новизна.")

    # 15
    s = new("Формы работы")
    title_block(s, "Что ещё собирает дом")
    forms = [
        ("Карта труда", "Кто делает, кто замечает, что тяготит сверх сил. Через три месяца карта сверяется с дневником."),
        ("Круг людей", "Кто даёт силу, кто судит союз, кого давно оставили без внимания. Одно малое действие к роду или приходу."),
        ("Группа пар", "Четыре–шесть пар, восемь встреч. Священник на открытии, на теме таинства и на завершении."),
        ("Возрасты", "Один каркас: смысл года, правда труда, способ мириться, дневник и время двоих."),
    ]
    for i, (h, body) in enumerate(forms):
        col = i % 2
        row = i // 2
        x = Inches(0.55 + col * 6.3)
        y = Inches(2.0 + row * 2.3)
        add_rect(s, x, y, Inches(5.95), Inches(2.1), CARD)
        add_rect(s, x, y, Inches(5.95), Inches(0.08), GOLD)
        add_text(s, x + Inches(0.35), y + Inches(0.3), Inches(5.3), Inches(0.45), h, SERIF, 22, WINE, True)
        add_text(s, x + Inches(0.35), y + Inches(0.9), Inches(5.3), Inches(0.95), body, SANS, 16, INK)
    notes(s, "Если воцерковлён один, верующему нужна общинная среда, а второму — уважение к совести. Вопросы таинства и крещения детей пара выносит к священнику вместе, когда оба готовы слышать.")

    # 16
    s = new("Итог")
    add_rect(s, 0, 0, W, H, WINE_DEEP)
    add_rect(s, 0, 0, Inches(0.18), H, GOLD)
    add_text(s, Inches(0.75), Inches(0.45), Inches(11.5), Inches(0.3), "ЗАКЛЮЧЕНИЕ", SANS, 13, GOLD, True)
    add_text(s, Inches(0.75), Inches(0.95), Inches(11.8), Inches(1.3), "Долгая семья умеет возвращаться\nк общению и узнавать в буднях призвание", SERIF, 32, WHITE, True)
    closes = [
        ("Смысл", "Назвать любовь её настоящими именами и удержать достоинство реального пути."),
        ("Уклад", "Сделать любовь видимой в труде, деньгах, границе с родом и открытости дома."),
        ("Час", "Дневник, недельный совет, порог дня и малое новое действие."),
    ]
    for i, (h, body) in enumerate(closes):
        x = Inches(0.75 + i * 4.05)
        add_text(s, x, Inches(3.3), Inches(3.8), Inches(0.45), h, SERIF, 22, GOLD, True)
        add_text(s, x, Inches(3.9), Inches(3.8), Inches(1.5), body, SANS, 16, RGBColor(0xF4, 0xE8, 0xDC))
    add_text(
        s,
        Inches(0.75),
        Inches(5.8),
        Inches(11.5),
        Inches(0.9),
        "Малая церковь узнаётся по правде, по милости и по часу,\nкогда два лица снова садятся друг напротив друга.",
        SERIF,
        20,
        WHITE,
        True,
    )
    notes(s, "Поблагодарить. Коротко: лицо больше симптома, брак — путь двух свободных людей. При вопросе о источниках назвать Златоуста, Антония Сурожского, Братуся, Василюка, Сатир и Зинкера.")

    # fix page numbers: total is len
    # I hardcoded total=16 but title is 1 and we added 15 more = 16. Good if count matches.
    assert len(prs.slides) == total, len(prs.slides)

    out = "/workspace/supervision/prezentaciya-smyslovoe-prizvanie-semi.pptx"
    prs.save(out)
    print(out, "slides", len(prs.slides))


if __name__ == "__main__":
    build()
