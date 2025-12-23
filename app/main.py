import os
import psycopg
from flask import Flask, request, redirect
from datetime import date, timedelta
from html import escape

DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)

BASE_CSS = """
:root{
  --bg:#0b1020; --card:#121a33; --muted:#93a4c7; --text:#e7ecff;
  --accent:#6ea8fe; --danger:#ff6b6b; --warn:#ffd166; --ok:#4cd4a3;
  --border:rgba(255,255,255,.10); height:100%;
}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;
  background:radial-gradient(1200px 600px at 10% 0%, #17234a 0%, var(--bg) 50%);
  color:var(--text); line-height:1.45;}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.container{max-width:980px;margin:0 auto;padding:24px}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px}
.h1{font-size:28px;margin:0}
.grid{display:grid;gap:14px}
@media (min-width:900px){.grid-2{grid-template-columns:1.1fr .9fr}}
.card{background:rgba(18,26,51,.92); border:1px solid var(--border);
  border-radius:16px; padding:16px; box-shadow:0 8px 30px rgba(0,0,0,.25)}
.card h2{margin:0 0 10px 0;font-size:18px}
.muted{color:var(--muted);font-size:13px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
input,select,button{font:inherit}
input,select{
  background:#0e1630;color:var(--text); border:1px solid var(--border);
  padding:10px 12px;border-radius:12px; outline:none}
input:focus,select:focus{border-color:rgba(110,168,254,.6)}
button{
  background:var(--accent);color:#081026;border:0; padding:10px 14px;border-radius:12px;
  cursor:pointer;font-weight:700; margin: 10px 0;}
button.secondary{background:transparent;color:var(--text);border:1px solid var(--border)}
button.danger{background:var(--danger);color:#260808}
.list{list-style:none;padding:0;margin:0;display:grid;gap:10px}
.item{
  display:flex;gap:10px;align-items:flex-start;justify-content:space-between;
  padding:12px;border-radius:14px;border:1px solid var(--border);background:rgba(14,22,48,.65)}
.item b{font-weight:800}
.badge{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;
  border:1px solid var(--border);background:rgba(255,255,255,.06);font-size:12px}
.hr{height:1px;background:var(--border);margin:12px 0}
.table{width:100%;border-collapse:separate;border-spacing:0 10px}
.table th{color:var(--muted);font-weight:700;font-size:12px;text-align:left;padding:0 10px}
.table td{background:rgba(14,22,48,.65);border:1px solid var(--border);
  padding:12px 10px}
.table tr td:first-child{border-radius:12px 0 0 12px}
.table tr td:last-child{border-radius:0 12px 12px 0}
.alert{border:1px solid rgba(255,107,107,.45);background:rgba(255,107,107,.08);
  padding:10px 12px;border-radius:14px}
.kpi{display:flex;gap:12px;flex-wrap:wrap}
.kpi .chip{padding:8px 10px;border-radius:14px;border:1px solid var(--border);background:rgba(255,255,255,.06)}
.small{font-size:12px}
.total{margin-top:14px}
ul {
    list-style-type: none;
    padding: 0;
    text-align: center;
}
li {
    justify-content: space-between;
    display: flex;
    align-items: center;
}
form {
    display: flex;
    flex-direction: column;
}
"""
def page(title: str, body_html: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>{BASE_CSS}</style>
</head>
<body>
  <div class="container">
    {body_html}
  </div>
</body>
</html>"""


def init_db():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Cars table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cars (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # Jobs table (legacy had car TEXT; keep it for compatibility)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY,
                    car TEXT,
                    car_id INTEGER,
                    mileage INTEGER NOT NULL,
                    job TEXT NOT NULL,
                    cost INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # Reminders table (maintenance)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id SERIAL PRIMARY KEY,
                    car_id INTEGER NOT NULL REFERENCES cars(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    interval_km INTEGER,        -- например 10000
                    interval_days INTEGER,      -- например 365
                    last_mileage INTEGER DEFAULT 0,
                    last_date DATE DEFAULT CURRENT_DATE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)


            # Add category column if not exists
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name='jobs' AND column_name='category'
                    ) THEN
                        ALTER TABLE jobs
                        ADD COLUMN category TEXT NOT NULL DEFAULT 'work';
                    END IF;
                END $$;
            """)


            # Old schema compatibility: car column might still be NOT NULL
            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name='jobs'
                          AND column_name='car'
                          AND is_nullable='NO'
                    ) THEN
                        ALTER TABLE jobs ALTER COLUMN car DROP NOT NULL;
                    END IF;
                END $$;
            """)


            # Ensure column car_id exists (for older DBs)
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name='jobs' AND column_name='car_id'
                    ) THEN
                        ALTER TABLE jobs ADD COLUMN car_id INTEGER;
                    END IF;
                END $$;
            """)

            # Add FK (ignore if exists)
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'jobs_car_id_fkey'
                    ) THEN
                        ALTER TABLE jobs
                        ADD CONSTRAINT jobs_car_id_fkey
                        FOREIGN KEY (car_id) REFERENCES cars(id)
                        ON DELETE SET NULL;
                    END IF;
                END $$;
            """)

        conn.commit()


def fetch_cars(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, title FROM cars ORDER BY title ASC;")
        return cur.fetchall()

def err_html(errors: list[str]) -> str:
    if not errors:
        return ""
    items = "".join(f"<li>{escape(e)}</li>" for e in errors)
    return f"<div style='background:#ffecec;padding:10px;border:1px solid #ffb3b3;margin:10px 0;'><b>Проверь форму:</b><ul>{items}</ul></div>"

def val(form: dict, key: str, default: str = "") -> str:
    return escape(str(form.get(key, default) if form else default))

def render_index_page(cars, rows, summary_rows, errors=None, form=None):
    cars_options = ""
    for car_id, title in cars:
        selected = "selected" if str(car_id) == str(form.get("car_id")) else ""
        cars_options += f'<option value="{car_id}" {selected}>{escape(title)}</option>'

    cars_links = "<ul>"
    for car_id, title in cars:
        cars_links += f'<li><a href="/cars/{car_id}">{escape(title)}</a></li>'
    cars_links += "</ul>"

    summary_html = """
    <table border="1" cellpadding="6" cellspacing="0">
      <tr>
        <th>Авто</th>
        <th>Всего</th>
        <th>Запчасти</th>
        <th>Работа</th>
        <th>Записей</th>
      </tr>
    """
    for s in summary_rows:
        car_id, title, total, parts, work, cnt = s
        summary_html += (
            f"<tr>"
            f"<td><a href='/cars/{car_id}'>{escape(title)}</a></td>"
            f"<td><b>{total} ₽</b></td>"
            f"<td>{parts} ₽</td>"
            f"<td>{work} ₽</td>"
            f"<td>{cnt}</td>"
            f"</tr>"
        )
    summary_html += "</table>"

    errors_block = err_html(errors or [])

    category = (form or {}).get("category", "work")
    work_sel = "selected" if category == "work" else ""
    part_sel = "selected" if category == "part" else ""

    html = f"""
    <div class="topbar">
      <h1 class="h1">Гаражный журнал</h1>
      <div class="muted">Учёт обслуживания и расходов</div>
    </div>
    
    <div class="grid grid-2">
      <div class="card">    
        <h2>Добавить запись</h2>
        {errors_block}
        <form method="POST" action="/add_job">
          <label>Автомобиль:</label>
          <select name="car_id" required>
            <option value="" disabled {"selected" if not (form or {}).get("car_id") else ""}>— выбери авто —</option>
            {cars_options}
          </select>
    
          <label>Категория:</label>
          <select name="category" required>
            <option value="work" {work_sel}>Работа</option>
            <option value="part" {part_sel}>Запчасть</option>
          </select>
    
          <input name="mileage" placeholder="Пробег" type="number" required value="{val(form or {}, 'mileage')}">
          <input name="job" placeholder="Описание" required value="{val(form or {}, 'job')}">
          <input name="cost" placeholder="Стоимость (₽)" type="number" value="{val(form or {}, 'cost', '0')}">
          <button type="submit">Добавить</button>
        </form>
      </div>
      
    <div class="card">  
        <h2>Добавить автомобиль</h2>
        <form method="POST" action="/add_car">
          <input name="title" placeholder="Например: BMW E90 320i" required>
          <button type="submit">Создать авто</button>
        </form>
    </div>
    
    <div class="card">  
        <h2>Автомобили</h2>
        {cars_links}
    </div>
    
    <div class="card">  
        <h2>Сводка по вложениям</h2>
        {summary_html}
    </div>
    </div>
    
    <div class="grid total">
    <div class="card">  
    <h2>Последние записи</h2>
    <ul>
    """

    for r in rows:
        job_id = r[0]
        icon = "🔧" if r[2] == "work" else "🧩"
        html += (
            f"<li>{icon} <b>{escape(r[1])}</b> — {r[3]} км — {escape(r[4])} — {r[5]} ₽ "
            f"<small>({r[6]})</small> "
            f"<a href='/jobs/{job_id}/edit'>✏️ Ред.</a> "
            f"<form method='POST' action='/jobs/{job_id}/delete' style='display:inline;'>"
            f"<button type='submit' onclick=\"return confirm('Удалить запись?');\">🗑</button>"
            f"</form>"
            f"</li>"
        )

    html += "</ul></div></div>"
    return html



@app.get("/")
def index():
    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        cars = fetch_cars(conn)

        with conn.cursor() as cur:
            cur.execute("""
                SELECT j.id,
                       COALESCE(c.title, j.car, '—') AS car_title,
                       j.category, j.mileage, j.job, j.cost, j.created_at
                FROM jobs j
                LEFT JOIN cars c ON c.id = j.car_id
                ORDER BY j.id DESC
                LIMIT 50;
            """)
            rows = cur.fetchall()

            cur.execute("""
                SELECT
                    c.id,
                    c.title,
                    COALESCE(SUM(j.cost), 0) AS total_cost,
                    COALESCE(SUM(CASE WHEN j.category = 'part' THEN j.cost ELSE 0 END), 0) AS parts_cost,
                    COALESCE(SUM(CASE WHEN j.category = 'work' THEN j.cost ELSE 0 END), 0) AS work_cost,
                    COUNT(j.id) AS jobs_count
                FROM cars c
                LEFT JOIN jobs j ON j.car_id = c.id
                GROUP BY c.id, c.title
                ORDER BY total_cost DESC, c.title ASC;
            """)
            summary_rows = cur.fetchall()

    return page("Гаражный журнал", render_index_page(cars, rows, summary_rows, errors=[], form={}))


@app.post("/add_car")
def add_car():
    title = (request.form["title"] or "").strip()
    if not title:
        return redirect("/")

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Insert if not exists
            cur.execute("""
                INSERT INTO cars (title)
                VALUES (%s)
                ON CONFLICT (title) DO NOTHING;
            """, (title,))
        conn.commit()

    return redirect("/")


@app.post("/add_job")
def add_job():
    # соберём форму как строки (чтобы вернуть обратно как есть)
    form = {
        "car_id": request.form.get("car_id", ""),
        "category": request.form.get("category", "work"),
        "mileage": request.form.get("mileage", ""),
        "job": request.form.get("job", ""),
        "cost": request.form.get("cost", "0"),
        "return_to": request.form.get("return_to", "/"),  # на будущее
    }

    errors = []

    # валидация
    if not form["car_id"].isdigit():
        errors.append("Выбери автомобиль.")
    if not str(form["mileage"]).lstrip("-").isdigit():
        errors.append("Пробег должен быть числом.")
    if not str(form["cost"]).lstrip("-").isdigit():
        errors.append("Стоимость должна быть числом.")
    if not (form["job"] or "").strip():
        errors.append("Описание не может быть пустым.")
    if form["category"] not in ("work", "part"):
        errors.append("Некорректная категория.")

    # если базовые ошибки — рендерим главную с подсказками
    if errors:
        init_db()
        with psycopg.connect(DATABASE_URL) as conn:
            cars = fetch_cars(conn)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT j.id,
                           COALESCE(c.title, j.car, '—') AS car_title,
                           j.category, j.mileage, j.job, j.cost, j.created_at
                    FROM jobs j
                    LEFT JOIN cars c ON c.id = j.car_id
                    ORDER BY j.id DESC
                    LIMIT 50;
                """)
                rows = cur.fetchall()

                cur.execute("""
                    SELECT
                        c.id, c.title,
                        COALESCE(SUM(j.cost), 0),
                        COALESCE(SUM(CASE WHEN j.category = 'part' THEN j.cost ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN j.category = 'work' THEN j.cost ELSE 0 END), 0),
                        COUNT(j.id)
                    FROM cars c
                    LEFT JOIN jobs j ON j.car_id = c.id
                    GROUP BY c.id, c.title
                    ORDER BY 3 DESC, c.title ASC;
                """)
                summary_rows = cur.fetchall()

        return page(
            "Добавить работу",
            render_index_page(cars, rows, summary_rows, errors=errors, form=form)
        ), 400

    car_id = int(form["car_id"])
    mileage = int(form["mileage"])
    cost = int(form["cost"])
    job_text = form["job"].strip()
    category = form["category"]

    if cost < 0:
        errors.append("Стоимость не может быть отрицательной.")
    if mileage < 0:
        errors.append("Пробег не может быть отрицательным.")

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        # “пробег назад”
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(mileage), 0) FROM jobs WHERE car_id=%s;", (car_id,))
            max_mileage = cur.fetchone()[0] or 0
        if mileage < max_mileage:
            errors.append(f"Пробег не может быть меньше предыдущего для этого авто (минимум {max_mileage}).")

        if errors:
            # вернуть главную с ошибками и заполненной формой
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT j.id,
                           COALESCE(c.title, j.car, '—') AS car_title,
                           j.category, j.mileage, j.job, j.cost, j.created_at
                    FROM jobs j
                    LEFT JOIN cars c ON c.id = j.car_id
                    ORDER BY j.id DESC
                    LIMIT 50;
                """)
                rows = cur.fetchall()

                cur.execute("""
                    SELECT
                        c.id, c.title,
                        COALESCE(SUM(j.cost), 0),
                        COALESCE(SUM(CASE WHEN j.category = 'part' THEN j.cost ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN j.category = 'work' THEN j.cost ELSE 0 END), 0),
                        COUNT(j.id)
                    FROM cars c
                    LEFT JOIN jobs j ON j.car_id = c.id
                    GROUP BY c.id, c.title
                    ORDER BY 3 DESC, c.title ASC;
                """)
                summary_rows = cur.fetchall()

            cars = fetch_cars(conn)
            return page("Добавить работу", render_index_page(cars, rows, summary_rows, errors=errors, form=form)), 400

        # всё ок — сохраняем
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO jobs (car_id, mileage, job, cost, category) VALUES (%s,%s,%s,%s,%s);",
                (car_id, mileage, job_text, cost, category),
            )
        conn.commit()

    return redirect(f"/cars/{car_id}")

@app.get("/cars/<int:car_id>")
def car_jobs(car_id: int):
    init_db()

    # --- читаем фильтры из query params ---
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()   # work / part / ""
    mileage_from = (request.args.get("m_from") or "").strip()
    mileage_to = (request.args.get("m_to") or "").strip()
    date_from = (request.args.get("d_from") or "").strip()    # YYYY-MM-DD
    date_to = (request.args.get("d_to") or "").strip()        # YYYY-MM-DD

    # --- строим WHERE динамически ---
    where = ["j.car_id = %s"]
    params = [car_id]

    if category in ("work", "part"):
        where.append("j.category = %s")
        params.append(category)

    if q:
        where.append("j.job ILIKE %s")
        params.append(f"%{q}%")

    if mileage_from.isdigit():
        where.append("j.mileage >= %s")
        params.append(int(mileage_from))

    if mileage_to.isdigit():
        where.append("j.mileage <= %s")
        params.append(int(mileage_to))

    # даты: на всякий случай валидируем простым regex-подобным условием
    def is_date(s: str) -> bool:
        return len(s) == 10 and s[4] == "-" and s[7] == "-" and s.replace("-", "").isdigit()

    if is_date(date_from):
        where.append("j.created_at >= %s::date")
        params.append(date_from)

    if is_date(date_to):
        # включительно по дате: < (date_to + 1 day)
        where.append("j.created_at < (%s::date + interval '1 day')")
        params.append(date_to)

    where_sql = " AND ".join(where)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # текущий пробег по авто
            cur.execute("SELECT COALESCE(MAX(mileage), 0) FROM jobs WHERE car_id=%s;", (car_id,))
            current_mileage = cur.fetchone()[0] or 0

            # напоминания
            cur.execute("""
                SELECT id, title, interval_km, interval_days, last_mileage, last_date, is_active
                FROM reminders
                WHERE car_id=%s
                ORDER BY is_active DESC, id DESC;
            """, (car_id,))
            reminders = cur.fetchall()

            cur.execute("SELECT id, title FROM cars WHERE id = %s;", (car_id,))
            car = cur.fetchone()
            if not car:
                return "Автомобиль не найден", 404

            # выборка работ с учётом фильтров
            cur.execute(f"""
                SELECT j.id, j.mileage, j.job, j.cost, j.category, j.created_at
                FROM jobs j
                WHERE {where_sql}
                ORDER BY j.id DESC
                LIMIT 500;
            """, params)
            jobs = cur.fetchall()

            # суммы по отфильтрованным данным (для удобной сводки сверху)
            cur.execute(f"""
                SELECT
                  COALESCE(SUM(j.cost), 0) AS total,
                  COALESCE(SUM(CASE WHEN j.category='part' THEN j.cost ELSE 0 END), 0) AS parts,
                  COALESCE(SUM(CASE WHEN j.category='work' THEN j.cost ELSE 0 END), 0) AS works,
                  COUNT(*) AS cnt
                FROM jobs j
                WHERE {where_sql};
            """, params)
            total, parts, works, cnt = cur.fetchone()

    # --- значения в форму (чтобы не сбрасывались) ---
    qv = escape(q)
    m_from_v = escape(mileage_from)
    m_to_v = escape(mileage_to)
    d_from_v = escape(date_from)
    d_to_v = escape(date_to)

    work_sel = "selected" if category == "work" else ""
    part_sel = "selected" if category == "part" else ""
    all_sel = "selected" if category not in ("work", "part") else ""

    today = date.today()
    # HTML для напоминаний
    reminders_html = '<div class="card"><h2>Напоминания (ТО)</h2>'

    reminders_html += f"<p><b>Текущий пробег:</b> {current_mileage} км</p>"

    today_str = today.isoformat()

    reminders_html += """
    <form method="POST" action="/reminders/add">
      <input type="hidden" name="car_id" value="{car_id}">
      <input name="title" placeholder="Например: Замена масла" required>
      <input name="interval_km" placeholder="Интервал (км), например 10000" type="number">
      <input name="interval_days" placeholder="Интервал (дней), например 365" type="number">
      <input name="last_mileage" placeholder="Последний пробег" type="number" value="{current_mileage}">
      <input name="last_date" placeholder="Последняя дата" type="date" value="{today_str}">
      <button type="submit">Добавить напоминание</button>
    </form>
    """.format(car_id=car_id, current_mileage=current_mileage, today_str=today_str)

    if not reminders:
        reminders_html += "<p><i>Пока нет напоминаний.</i></p>"
    else:
        reminders_html += "<ul>"
        for rid, title, interval_km, interval_days, last_mileage, last_date, is_active in reminders:
            next_km = None
            next_dt = None

            if interval_km and interval_km > 0:
                next_km = (last_mileage or 0) + interval_km

            if interval_days and interval_days > 0 and last_date:
                next_dt = last_date + timedelta(days=interval_days)

            # статус
            status = "🟢"
            hints = []

            if next_km is not None:
                km_left = next_km - current_mileage
                hints.append(f"след. при {next_km} км (осталось {km_left} км)")
                if km_left <= 0:
                    status = "🔴"
                elif km_left <= 500:
                    status = "🟡"

            if next_dt is not None:
                days_left = (next_dt - today).days
                hints.append(f"след. дата {next_dt} (через {days_left} дн.)")
                if days_left <= 0:
                    status = "🔴"
                elif days_left <= 14 and status != "🔴":
                    status = "🟡"

            active_txt = "" if is_active else " (выключено)"

            reminders_html += (
                f"<li>{status} <b>{escape(title)}</b>{active_txt} — "
                + "; ".join(hints)
                + f"""
                <form method="POST" action="/reminders/{rid}/done" style="display:inline;margin-left:8px;">
                  <input type="hidden" name="car_id" value="{car_id}">
                  <input type="hidden" name="current_mileage" value="{current_mileage}">
                  <button type="submit">✅ Выполнено</button>
                </form>
                <form method="POST" action="/reminders/{rid}/toggle" style="display:inline;margin-left:4px;">
                  <input type="hidden" name="car_id" value="{car_id}">
                  <button type="submit">{'⏸ Выкл' if is_active else '▶ Вкл'}</button>
                </form>
                """
                + "</li>"
            )
        reminders_html += "</ul>"

    reminders_html += '</div>'

    html = f"""
    <a href="/">← назад</a>
    <h1>Работы: {escape(car[1])}</h1>
    
    {reminders_html}

    <h2>Поиск и фильтры (только для этого авто)</h2>
    <form method="GET" action="/cars/{car_id}">
      <input name="q" placeholder="Поиск по описанию" value="{qv}">
      <select name="category">
        <option value="" {all_sel}>Все категории</option>
        <option value="work" {work_sel}>Работа</option>
        <option value="part" {part_sel}>Запчасть</option>
      </select>

      <input name="m_from" placeholder="Пробег от" type="number" value="{m_from_v}">
      <input name="m_to" placeholder="Пробег до" type="number" value="{m_to_v}">

      <input name="d_from" placeholder="Дата от" type="date" value="{d_from_v}">
      <input name="d_to" placeholder="Дата до" type="date" value="{d_to_v}">

      <button type="submit">Применить</button>
      <a href="/cars/{car_id}" style="margin-left:10px;">Сбросить</a>
    </form>

    <p>
      <b>Найдено:</b> {cnt} записей |
      <b>Всего:</b> {total} ₽ |
      <b>Запчасти:</b> {parts} ₽ |
      <b>Работа:</b> {works} ₽
    </p>

    <h2>Добавить работу для этого авто</h2>
    <form method="POST" action="/add_job">
      <input type="hidden" name="car_id" value="{car_id}">
      <select name="category" required>
        <option value="work">Работа</option>
        <option value="part">Запчасть</option>
      </select>
      <input name="mileage" placeholder="Пробег" type="number" required>
      <input name="job" placeholder="Описание" required>
      <input name="cost" placeholder="Стоимость (₽)" type="number" value="0">
      <button type="submit">Добавить</button>
    </form>

    <hr>
    <h2>История</h2>
    <ul>
    """

    for j in jobs:
        job_id = j[0]
        icon = "🔧" if j[4] == "work" else "🧩"
        html += (
            f"<li>{icon} {j[1]} км — {escape(j[2])} — {j[3]} ₽ "
            f"<small>({j[5]})</small> "
            f"<a href='/jobs/{job_id}/edit'>✏️ Ред.</a> "
            f"<form method='POST' action='/jobs/{job_id}/delete' style='display:inline;'>"
            f"<button type='submit' onclick=\"return confirm('Удалить запись?');\">🗑</button>"
            f"</form>"
            f"</li>"
        )

    html += "</ul>"
    return page(f"Авто: {car[1]}", html)


@app.get("/jobs/<int:job_id>/edit")
def edit_job_form(job_id: int):
    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        cars = fetch_cars(conn)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, car_id, category, mileage, job, cost
                FROM jobs
                WHERE id = %s;
            """, (job_id,))
            row = cur.fetchone()

    if not row:
        return "Запись не найдена", 404

    _, car_id, category, mileage, job_text, cost = row

    cars_options = ""
    for cid, title in cars:
        selected = "selected" if cid == car_id else ""
        cars_options += f'<option value="{cid}" {selected}>{title}</option>'

    work_selected = "selected" if category == "work" else ""
    part_selected = "selected" if category == "part" else ""

    return f"""
    <a href="/">← назад</a>
    <h1>Редактировать запись #{job_id}</h1>

    <form method="POST" action="/jobs/{job_id}/edit">
      <label>Авто:</label>
      <select name="car_id" required>
        {cars_options}
      </select>
      <label>Категория:</label>
      <select name="category" required>
        <option value="work" {work_selected}>Работа</option>
        <option value="part" {part_selected}>Запчасть</option>
      </select>
      <input name="mileage" placeholder="Пробег" type="number" required value="{mileage}">
      <input name="job" placeholder="Описание" required value="{job_text}">
      <input name="cost" placeholder="Стоимость (₽)" type="number" required value="{cost}">
      <button type="submit">Сохранить</button>
    </form>

    <form method="POST" action="/jobs/{job_id}/delete" style="margin-top:12px;">
      <button type="submit" onclick="return confirm('Удалить запись?');">🗑 Удалить</button>
    </form>
    """


@app.post("/jobs/<int:job_id>/edit")
def edit_job_save(job_id: int):
    car_id = int(request.form["car_id"])
    mileage = int(request.form["mileage"])
    job_text = (request.form.get("job") or "").strip()
    cost = int(request.form.get("cost") or 0)
    category = request.form.get("category", "work")
    if category not in ("work", "part"):
        category = "work"

    if not job_text:
        return redirect(f"/jobs/{job_id}/edit")

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE jobs
                SET car_id=%s, category=%s, mileage=%s, job=%s, cost=%s
                WHERE id=%s
                RETURNING car_id;
            """, (car_id, category, mileage, job_text, cost, job_id))
            updated = cur.fetchone()
        conn.commit()

    if not updated:
        return "Запись не найдена", 404

    # после сохранения логично вернуть на страницу авто
    return redirect(f"/cars/{updated[0]}")


@app.post("/jobs/<int:job_id>/delete")
def delete_job(job_id: int):
    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # узнаем car_id чтобы вернуться на нужную страницу
            cur.execute("SELECT car_id FROM jobs WHERE id=%s;", (job_id,))
            row = cur.fetchone()
            if not row:
                return "Запись не найдена", 404
            car_id = row[0]

            cur.execute("DELETE FROM jobs WHERE id=%s;", (job_id,))
        conn.commit()

    return redirect(f"/cars/{car_id}")

@app.post("/reminders/add")
def reminder_add():
    car_id = int(request.form["car_id"])
    title = (request.form.get("title") or "").strip()

    interval_km = request.form.get("interval_km") or ""
    interval_days = request.form.get("interval_days") or ""
    last_mileage = request.form.get("last_mileage") or "0"
    last_date = request.form.get("last_date") or date.today().isoformat()

    # приведение
    ikm = int(interval_km) if interval_km.isdigit() else None
    idays = int(interval_days) if interval_days.isdigit() else None
    lm = int(last_mileage) if str(last_mileage).lstrip("-").isdigit() else 0

    if not title:
        return redirect(f"/cars/{car_id}")

    # хотя бы один интервал должен быть
    if (ikm is None or ikm <= 0) and (idays is None or idays <= 0):
        return redirect(f"/cars/{car_id}")

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO reminders (car_id, title, interval_km, interval_days, last_mileage, last_date, is_active)
                VALUES (%s, %s, %s, %s, %s, %s::date, TRUE);
            """, (car_id, title, ikm, idays, lm, last_date))
        conn.commit()

    return redirect(f"/cars/{car_id}")


@app.post("/reminders/<int:reminder_id>/done")
def reminder_done(reminder_id: int):
    car_id = int(request.form["car_id"])
    current_mileage = int(request.form.get("current_mileage") or 0)

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE reminders
                SET last_mileage=%s, last_date=CURRENT_DATE
                WHERE id=%s;
            """, (current_mileage, reminder_id))
        conn.commit()

    return redirect(f"/cars/{car_id}")


@app.post("/reminders/<int:reminder_id>/toggle")
def reminder_toggle(reminder_id: int):
    car_id = int(request.form["car_id"])

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE reminders
                SET is_active = NOT is_active
                WHERE id=%s;
            """, (reminder_id,))
        conn.commit()

    return redirect(f"/cars/{car_id}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
