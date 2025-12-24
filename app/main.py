import os
import psycopg
from flask import Flask, request, redirect, session
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta
from html import escape

DATABASE_URL = os.environ.get("DATABASE_URL")

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

CAR_IMAGES = {
    "bmw_x1": ("/static/cars/bmw_x1.jpg", "BMW X1"),
    "bmw_x3": ("/static/cars/bmw_x3.png", "BMW X3"),
    "ford_focus": ("/static/cars/ford_focus.jpeg", "Ford Focus"),
    "mitsubishi_outlander": ("/static/cars/mitsubishi_outlander.jpg", "Mitsubishi Outlander"),
    "lada_granta": ("/static/cars/lada_granta.jpg", "Lada Granta"),
}

DEFAULT_CAR_IMAGE = "/static/cars/default.jpg"  # можешь добавить заглушку


BASE_CSS = """
:root{
  --bg0:#0e0c0a;
  --text:#eee8df;
  --muted:#b8afa3;

  --glass: rgba(255,255,255,.07);
  --stroke: rgba(255,255,255,.14);

  --field: rgba(0,0,0,.22);
  --fieldStroke: rgba(255,255,255,.10);

  --a1:#ffb020; /* amber */
  --a2:#ff7a18; /* orange */
  --a3:#c77d3a; /* copper */

  --shadow: 0 24px 60px rgba(0,0,0,.55);

  --border: rgba(255,255,255,.14);
  --accent: var(--a1);
  --danger: #ff6b6b;
}

*{box-sizing:border-box}

body{
    margin: 0;
    font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial;
    color: var(--text);
    line-height: 1.45;
    background: radial-gradient(900px 500px at 20% 10%, rgba(255, 176, 32, .20), transparent 55%), radial-gradient(800px 500px at 85% 25%, rgba(199, 125, 58, .18), transparent 60%), linear-gradient(rgba(10, 8, 6, 0.20), rgba(10, 8, 6, 0.55)), url(/static/bg2.jpg);
    background-size: auto, auto, auto, cover;
    background-position: center, center, center, center;
    background-repeat: no-repeat;
    background-attachment: fixed;
    height: 100vh;
    display: flex;
}

.login {
    justify-content: center;
    align-items: center;
    height: 100%;
    display: flex;
}

.logs {
    width: 350px;
}

/* Links */
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}

/* Layout */
.container{max-width:980px;margin:0 auto;padding:24px}
.topbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:18px}

.h1{
  font-size:28px;
  margin:0;
  font-weight:780;
  letter-spacing:.2px;
  text-shadow:0 10px 35px rgba(0,0,0,.55);
}

.grid{display:grid;gap:14px}
@media (min-width:900px){.grid-2{grid-template-columns:1.1fr .9fr}}

.muted{color:var(--muted);font-size:13px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}

/* Card / Glass */
.card{
  background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.05));
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 16px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  position: relative;
}
.card::before{
  content:"";
  position:absolute;
  left: 18px; right: 18px; top: 10px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,176,32,.45), transparent);
  opacity: .85;
  pointer-events:none;
}
.card h2{
  margin:0 0 10px 0;
  font-size:18px;
  font-weight:650;
  letter-spacing:.1px;
}

/* Forms */
input,select,button{font:inherit}
form{display:flex;flex-direction:column}
label{
  font-size:13px;
  color: rgba(238,232,223,.78);
  margin-top: 10px;
}

/* Controls */
input,select{
  width: 100%;
  height: 44px;
  padding: 10px 12px;
  border-radius: 14px;
  background: rgba(0,0,0,.22);
  border: 1px solid rgba(255,255,255,.10);
  color: var(--text);
  outline: none;
  margin: 10px 0;

  box-shadow: inset 0 1px 0 rgba(255,255,255,.05);
  transition: border-color .2s ease, box-shadow .2s ease, transform .2s ease;
}

input::placeholder{color:rgba(184,175,163,.55)}
input:hover,select:hover{border-color: rgba(255,255,255,.18)}
input:focus,select:focus{
  border-color: rgba(255,176,32,.55);
  box-shadow: 0 0 0 4px rgba(255,176,32,.14), inset 0 1px 0 rgba(255,255,255,.06);
}

/* Select arrow (custom) */
select{
  appearance:none;
  -webkit-appearance:none;
  padding-right: 42px;
  cursor: pointer;

  background-image:
    linear-gradient(45deg, transparent 50%, rgba(238,232,223,.82) 50%),
    linear-gradient(135deg, rgba(238,232,223,.82) 50%, transparent 50%),
    linear-gradient(to right, transparent, transparent);
  background-position:
    calc(100% - 18px) 18px,
    calc(100% - 12px) 18px,
    0 0;
  background-size:
    6px 6px,
    6px 6px,
    100% 100%;
  background-repeat:no-repeat;
}
select option{
  background:#14110e;
  color:var(--text);
}

/* Buttons */
button{
  width: 100%;
  height: 46px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,.12);
  cursor:pointer;
  font-weight:700;
  margin: 10px 0;
  color:#1b120a;

  background: linear-gradient(135deg, var(--a1), var(--a2));
  box-shadow: 0 18px 45px rgba(255,122,24,.22);
  transition: transform .25s ease, box-shadow .25s ease, filter .25s ease;
}
button:hover{
  transform: translateY(-2px);
  box-shadow: 0 22px 60px rgba(255,122,24,.30);
  filter: brightness(1.03);
}
button:active{transform: translateY(0) scale(.99)}

/* Secondary button (если используешь) */
button.secondary{
  background: rgba(255,255,255,.06);
  color: var(--text);
  border: 1px solid rgba(255,255,255,.14);
  box-shadow: 0 18px 45px rgba(0,0,0,.30);
}
button.secondary:hover{
  transform: translateY(-2px);
  border-color: rgba(255,176,32,.35);
  box-shadow: 0 22px 60px rgba(0,0,0,.40);
}

/* Danger button */
button.danger{
  background: linear-gradient(135deg, rgba(255,107,107,.95), rgba(255,107,107,.70));
  color:#240b0b;
  border: 1px solid rgba(255,107,107,.35);
  box-shadow: 0 18px 45px rgba(255,107,107,.18);
}
button.danger:hover{
  transform: translateY(-2px);
  box-shadow: 0 22px 60px rgba(255,107,107,.28);
}

/* Small buttons inside list items (удалить/выполнено/вкл) */
li form button{
  width: auto;
  height: 34px;
  padding: 0 10px;
  border-radius: 12px;
  font-weight: 650;
  margin: 0 0 0 6px;
}

/* Lists */
ul{
  list-style-type:none;
  padding:0;
  margin:0;
  text-align:left;
  display:grid;
  gap:10px;
}
li{
  justify-content:space-between;
  display:flex;
  align-items:center;
  gap: 10px;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(0,0,0,.18);
}
li small{color: rgba(184,175,163,.75)}

/* Your custom blocks */
.table-block{
  display:grid;
  grid-template-columns: 1fr 1fr;
  text-align:left;
  align-items:baseline;
  background: rgba(0,0,0,.18);
  padding: 10px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.10);
}

/* Cars layout */
.cars-list{
  display:flex;
  justify-content:space-around;
  align-items:center;
  height: 50%;
}

.header{
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap: 12px;
}

.cars-photo{
  width:100%;
  height:140px;
  object-fit:cover;
  border-radius:12px;
  border:1px solid rgba(255,255,255,.10);
  display:flex;
  align-items:center;
  background: rgba(255,255,255,.04);
  overflow:hidden;
  justify-content: center;
  background: #fff;
}

/* Hover for car cards (у тебя a.card glass) */
a.card{
  transition: transform .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s, border-color .35s;
}
a.card:hover{
  transform: translateY(-6px);
  border-color: rgba(255,176,32,.28);
  box-shadow: 0 30px 70px rgba(255,176,32,.10), 0 24px 60px rgba(0,0,0,.6);
}

/* Tables (summary) */
table{
  width:100%;
  border-collapse: separate;
  border-spacing: 0;
  overflow:hidden;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(0,0,0,.18);
}
th,td{
  border-bottom: 1px solid rgba(255,255,255,.08);
  padding: 10px 12px;
}
th{
  color: rgba(238,232,223,.75);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: .6px;
}
tr:last-child td{border-bottom:none}

/* Misc */
.list{list-style:none;padding:0;margin:0;display:grid;gap:10px}
.item b{font-weight:800}
.badge{
  display:inline-flex;align-items:center;gap:6px;
  padding:4px 10px;border-radius:999px;
  border:1px solid rgba(255,255,255,.12);
  background:rgba(255,255,255,.06);
  font-size:12px
}
.hr{height:1px;background:rgba(255,255,255,.12);margin:12px 0}
.alert{
  border:1px solid rgba(255,107,107,.45);
  background:rgba(255,107,107,.08);
  padding:10px 12px;border-radius:14px
}
.kpi{display:flex;gap:12px;flex-wrap:wrap}
.kpi .chip{
  padding:8px 10px;border-radius:14px;
  border:1px solid rgba(255,255,255,.12);
  background:rgba(255,255,255,.06)
}
.small{font-size:12px}
.total{margin-top:14px}

/* Optional: smoother feel */
@media (prefers-reduced-motion: no-preference){
  .card, input, select, button, a.card { will-change: transform; }
}

/* ===== MOBILE FIXES ===== */
@media (max-width: 640px){

  .login {
    width: 300px;
  }
  .container{
    padding: 14px;
  }

  /* Верхняя панель: не в одну строку */
  .topbar{
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }
  .topbar .muted{
    margin-top: -4px;
  }

  /* Сетка: в одну колонку */
  .grid-2{
    grid-template-columns: 1fr !important;
  }

  /* Карточки: меньше радиус/паддинги */
  .card{
    padding: 14px;
    border-radius: 16px;
    width: 95%;
  }
  
  .card-total {
    width: 100%;
  }

  /* Карточки авто: не даём “прыгать” из-за inline-стилей */
  a.card{
    display: block !important;
    width: 100%;
  }

  /* Картинка в авто: адаптивная высота */
  .cars-photo{
    height: 140px; /* можно 130–160 */
  }
  .cars-photo img{
    width: 100% !important;
    height: 100% !important;
    object-fit: cover !important;
    display: block;
  }

  /* Таблица: чтобы не ломала ширину */
  table{
    display:block;
    width:100%;
    overflow-x:auto;
    -webkit-overflow-scrolling: touch;
  }

  /* Список записей: перенос текста */
  li{
    flex-wrap: wrap;
    justify-content: flex-start;
    gap: 8px;
  }
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

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect("/login")
        return fn(*args, **kwargs)
    return wrapper

def current_user_id() -> int:
    return int(session["user_id"])

def init_db():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # Cars table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS cars (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    image_key TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            # если в старой схеме был UNIQUE(title) — убираем его
            cur.execute("""
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'cars_title_key'
              ) THEN
                ALTER TABLE cars DROP CONSTRAINT cars_title_key;
              END IF;
            END $$;
            """)

            # Ensure column user_id exists in cars (for older DBs)
            cur.execute("""
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='cars' AND column_name='user_id'
              ) THEN
                ALTER TABLE cars ADD COLUMN user_id INTEGER;
              END IF;
            END $$;
            """)

            # Ensure FK cars.user_id -> users.id (optional but recommended)
            cur.execute("""
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname='cars_user_id_fkey'
              ) THEN
                ALTER TABLE cars
                ADD CONSTRAINT cars_user_id_fkey
                FOREIGN KEY (user_id) REFERENCES users(id)
                ON DELETE CASCADE;
              END IF;
            END $$;
            """)

            # уникальность: одно и то же название авто только в рамках одного пользователя
            cur.execute("""
            DO $$
            BEGIN
              -- если constraint уже есть — ничего не делаем
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'cars_user_title_uq'
              ) THEN
                ALTER TABLE cars
                ADD CONSTRAINT cars_user_title_uq UNIQUE (user_id, title);
              END IF;
            END $$;
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

            # Add user_id to jobs if not exists
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='jobs' AND column_name='user_id'
                    ) THEN
                        ALTER TABLE jobs ADD COLUMN user_id INTEGER;
                    END IF;
                END $$;
            """)

            # FK jobs.user_id -> users.id
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname='jobs_user_id_fkey'
                    ) THEN
                        ALTER TABLE jobs
                        ADD CONSTRAINT jobs_user_id_fkey
                        FOREIGN KEY (user_id) REFERENCES users(id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
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

            # Add user_id to reminders if not exists
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='reminders' AND column_name='user_id'
                    ) THEN
                        ALTER TABLE reminders ADD COLUMN user_id INTEGER;
                    END IF;
                END $$;
            """)

            # FK reminders.user_id -> users.id
            cur.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname='reminders_user_id_fkey'
                    ) THEN
                        ALTER TABLE reminders
                        ADD CONSTRAINT reminders_user_id_fkey
                        FOREIGN KEY (user_id) REFERENCES users(id)
                        ON DELETE CASCADE;
                    END IF;
                END $$;
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

            # Recreate FK with ON DELETE CASCADE (safe migration)
            cur.execute("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'jobs_car_id_fkey'
                    ) THEN
                        ALTER TABLE jobs DROP CONSTRAINT jobs_car_id_fkey;
                    END IF;
                
                    ALTER TABLE jobs
                    ADD CONSTRAINT jobs_car_id_fkey
                    FOREIGN KEY (car_id) REFERENCES cars(id)
                    ON DELETE CASCADE;
                END $$;
            """)

        conn.commit()


def fetch_cars(conn, user_id: int):
    with conn.cursor() as cur:
        cur.execute("SELECT id, title, image_key FROM cars WHERE user_id=%s ORDER BY title ASC;", (user_id,))
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
    for car_id, title, image_key in cars:
        selected = "selected" if str(car_id) == str(form.get("car_id")) else ""
        cars_options += f'<option value="{car_id}" {selected}>{escape(title)}</option>'

    cars_cards = '<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px">'
    for car_id, title, image_key in cars:
        img = CAR_IMAGES.get(image_key, (DEFAULT_CAR_IMAGE, title))[0] if image_key else DEFAULT_CAR_IMAGE
        cars_cards += f"""
        <a class="card glass" href="/cars/{car_id}" style="display:block">
          <div class="cars-photo">
              <img src="{img}" alt="{escape(title)}"
                   style="height:100%;object-fit:cover;border-radius:12px;border:1px solid rgba(255,255,255,.10);">
          </div>     
          <div style="margin-top:10px;font-weight:800">{escape(title)}</div>
          <div class="muted small">Открыть журнал</div>
        </a>
        """
    cars_cards += "</div>"

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

    car_select = '<select name="image_key" required>'
    car_select += '<option value="" disabled selected>— выбери автомобиль —</option>'
    for key, (img, label) in CAR_IMAGES.items():
        car_select += f'<option value="{key}">{escape(label)}</option>'
    car_select += '</select>'

    html = f"""
    <div class="topbar">
      <h1 class="h1">Гаражный журнал</h1>
      <div class="muted">Учёт обслуживания и расходов</div>
    </div>
    
    <div class="grid grid-2">
      <div class="card glass">    
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
      
    <div class="card glass">  
        <h2>Добавить автомобиль</h2>
         <form method="POST" action="/add_car">
            {car_select}
            <button type="submit">Добавить авто</button>
          </form>
    </div>
    
    <div class="card glass">  
        <h2>Автомобили</h2>
        {cars_cards}
    </div>
    
    <div class="card glass">  
        <h2>Сводка по вложениям</h2>
        {summary_html}
    </div>
    </div>
    
    <div class="grid total">
    <div class="card glass card-total">  
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

@app.get("/register")
def register_form():
    return page("Регистрация", """
      <div class="card glass">
        <h2>Регистрация</h2>
        <form method="POST" action="/register">
          <input name="username" placeholder="Логин" required>
          <input name="password" placeholder="Пароль" type="password" required>
          <button type="submit">Создать аккаунт</button>
        </form>
        <p class="muted">Уже есть аккаунт? <a href="/login">Войти</a></p>
      </div>
    """)

@app.post("/register")
def register_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    if not username or len(password) < 4:
        return page("Ошибка", "<div class='card glass'><p>Логин обязателен, пароль минимум 4 символа.</p></div>"), 400

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s)
                ON CONFLICT (username) DO NOTHING
                RETURNING id;
            """, (username, generate_password_hash(password)))
            row = cur.fetchone()
        conn.commit()

    if not row:
        return page("Ошибка", "<div class='card glass'><p>Такой логин уже существует.</p></div>"), 400

    session["user_id"] = row[0]
    session["username"] = username
    return redirect("/")


@app.get("/login")
def login_form():
    return page("Вход", """
      <div class="login">
          <div class="card glass logs">
            <h2>Вход</h2>
            <form method="POST" action="/login">
              <input name="username" placeholder="Логин" required>
              <input name="password" placeholder="Пароль" type="password" required>
              <button type="submit">Войти</button>
            </form>
            <p class="muted">Нет аккаунта? <a href="/register">Регистрация</a></p>
          </div>
      </div>
    """)

@app.post("/login")
def login_post():
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash FROM users WHERE username=%s;", (username,))
            row = cur.fetchone()

    if not row or not check_password_hash(row[1], password):
        return page("Ошибка", "<div class='card glass'><p>Неверный логин или пароль.</p></div>"), 400

    session["user_id"] = row[0]
    session["username"] = username
    return redirect("/")


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.get("/")
@login_required
def index():
    user_id = current_user_id()
    init_db()

    with psycopg.connect(DATABASE_URL) as conn:
        cars = fetch_cars(conn, user_id)

        with conn.cursor() as cur:
            cur.execute("""
                SELECT j.id,
                       COALESCE(c.title, j.car, '—') AS car_title,
                       j.category, j.mileage, j.job, j.cost, j.created_at
                FROM jobs j
                LEFT JOIN cars c ON c.id = j.car_id AND c.user_id = %s
                WHERE j.user_id = %s
                ORDER BY j.id DESC
                LIMIT 50;
            """, (user_id, user_id))
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
                LEFT JOIN jobs j ON j.car_id = c.id AND j.user_id = %s
                WHERE c.user_id = %s
                GROUP BY c.id, c.title
                ORDER BY total_cost DESC, c.title ASC;
            """, (user_id, user_id))
            summary_rows = cur.fetchall()

    return page("Гаражный журнал", render_index_page(cars, rows, summary_rows, errors=[], form={}))


@app.post("/add_car")
@login_required
def add_car():
    user_id = current_user_id()
    image_key = (request.form.get("image_key") or "").strip()

    if image_key not in CAR_IMAGES:
        return redirect("/")

    title = CAR_IMAGES[image_key][1]

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO cars (title, image_key, user_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, title) DO NOTHING;
            """, (title, image_key, user_id))
        conn.commit()

    return redirect("/")



@app.post("/add_job")
@login_required
def add_job():
    user_id = current_user_id()
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
        user_id = current_user_id()
        init_db()
        with psycopg.connect(DATABASE_URL) as conn:
            cars = fetch_cars(conn, user_id)

            with conn.cursor() as cur:
                # последние записи ТОЛЬКО этого пользователя
                cur.execute("""
                    SELECT j.id,
                           COALESCE(c.title, j.car, '—') AS car_title,
                           j.category, j.mileage, j.job, j.cost, j.created_at
                    FROM jobs j
                    LEFT JOIN cars c
                      ON c.id = j.car_id AND c.user_id = %s
                    WHERE j.user_id = %s
                    ORDER BY j.id DESC
                    LIMIT 50;
                """, (user_id, user_id))
                rows = cur.fetchall()

                # сводка ТОЛЬКО по авто/работам этого пользователя
                cur.execute("""
                    SELECT
                        c.id, c.title,
                        COALESCE(SUM(j.cost), 0),
                        COALESCE(SUM(CASE WHEN j.category='part' THEN j.cost ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN j.category='work' THEN j.cost ELSE 0 END), 0),
                        COUNT(j.id)
                    FROM cars c
                    LEFT JOIN jobs j
                      ON j.car_id = c.id AND j.user_id = %s
                    WHERE c.user_id = %s
                    GROUP BY c.id, c.title
                    ORDER BY 3 DESC, c.title ASC;
                """, (user_id, user_id))
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

    # ✅ ВСТАВИТЬ ВОТ ЭТО (проверка владельца авто)
    user_id = current_user_id()  # если ты ещё не добавил user_id выше в add_job()
    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM cars WHERE id=%s AND user_id=%s;", (car_id, user_id))
            if not cur.fetchone():
                errors.append("Этот автомобиль не найден (или не принадлежит вам).")

    # если не тот авто — возвращаем главную с ошибкой (как ты делаешь выше)
    if errors:
        init_db()
        with psycopg.connect(DATABASE_URL) as conn:
            cars = fetch_cars(conn, user_id)  # <-- важно: с user_id
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT j.id,
                           COALESCE(c.title, j.car, '—') AS car_title,
                           j.category, j.mileage, j.job, j.cost, j.created_at
                    FROM jobs j
                    LEFT JOIN cars c ON c.id = j.car_id AND c.user_id=%s
                    WHERE j.user_id=%s
                    ORDER BY j.id DESC
                    LIMIT 50;
                """, (user_id, user_id))
                rows = cur.fetchall()

                cur.execute("""
                    SELECT
                        c.id, c.title,
                        COALESCE(SUM(j.cost), 0),
                        COALESCE(SUM(CASE WHEN j.category='part' THEN j.cost ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN j.category='work' THEN j.cost ELSE 0 END), 0),
                        COUNT(j.id)
                    FROM cars c
                    LEFT JOIN jobs j ON j.car_id=c.id AND j.user_id=%s
                    WHERE c.user_id=%s
                    GROUP BY c.id, c.title
                    ORDER BY 3 DESC, c.title ASC;
                """, (user_id, user_id))
                summary_rows = cur.fetchall()

        return page("Добавить работу", render_index_page(cars, rows, summary_rows, errors=errors, form=form)), 400

    if cost < 0:
        errors.append("Стоимость не может быть отрицательной.")
    if mileage < 0:
        errors.append("Пробег не может быть отрицательным.")

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        # “пробег назад”
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(MAX(mileage), 0) FROM jobs WHERE car_id=%s AND user_id=%s;", (car_id, user_id))
            max_mileage = cur.fetchone()[0] or 0
        if mileage < max_mileage:
            errors.append(f"Пробег не может быть меньше предыдущего для этого авто (минимум {max_mileage}).")

        if errors:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT j.id,
                           COALESCE(c.title, j.car, '—') AS car_title,
                           j.category, j.mileage, j.job, j.cost, j.created_at
                    FROM jobs j
                    LEFT JOIN cars c
                      ON c.id = j.car_id AND c.user_id = %s
                    WHERE j.user_id = %s
                    ORDER BY j.id DESC
                    LIMIT 50;
                """, (user_id, user_id))
                rows = cur.fetchall()

                cur.execute("""
                    SELECT
                        c.id, c.title,
                        COALESCE(SUM(j.cost), 0),
                        COALESCE(SUM(CASE WHEN j.category='part' THEN j.cost ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN j.category='work' THEN j.cost ELSE 0 END), 0),
                        COUNT(j.id)
                    FROM cars c
                    LEFT JOIN jobs j
                      ON j.car_id = c.id AND j.user_id = %s
                    WHERE c.user_id = %s
                    GROUP BY c.id, c.title
                    ORDER BY 3 DESC, c.title ASC;
                """, (user_id, user_id))
                summary_rows = cur.fetchall()

            cars = fetch_cars(conn, user_id)
            return page("Добавить работу", render_index_page(cars, rows, summary_rows, errors=errors, form=form)), 400

        # всё ок — сохраняем
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO jobs (car_id, user_id, mileage, job, cost, category) VALUES (%s,%s,%s,%s,%s,%s);",
                (car_id, user_id, mileage, job_text, cost, category),
            )
        conn.commit()

    return redirect(f"/cars/{car_id}")

@app.get("/cars/<int:car_id>")
@login_required
def car_jobs(car_id: int):
    user_id = current_user_id()
    init_db()

    # --- читаем фильтры из query params ---
    q = (request.args.get("q") or "").strip()
    category = (request.args.get("category") or "").strip()   # work / part / ""
    mileage_from = (request.args.get("m_from") or "").strip()
    mileage_to = (request.args.get("m_to") or "").strip()
    date_from = (request.args.get("d_from") or "").strip()    # YYYY-MM-DD
    date_to = (request.args.get("d_to") or "").strip()        # YYYY-MM-DD

    # --- строим WHERE динамически ---
    where = ["j.car_id = %s", "j.user_id = %s"]
    params = [car_id, user_id]

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
            # авто должно принадлежать пользователю
            cur.execute(
                "SELECT id, title FROM cars WHERE id=%s AND user_id=%s;",
                (car_id, user_id)
            )
            car = cur.fetchone()
            if not car:
                return "Автомобиль не найден", 404

            # текущий пробег по авто (только записи пользователя)
            cur.execute(
                "SELECT COALESCE(MAX(mileage), 0) FROM jobs WHERE car_id=%s AND user_id=%s;",
                (car_id, user_id)
            )
            current_mileage = cur.fetchone()[0] or 0

            # напоминания (только пользователя)
            cur.execute("""
                SELECT id, title, interval_km, interval_days, last_mileage, last_date, is_active
                FROM reminders
                WHERE car_id=%s AND user_id=%s
                ORDER BY is_active DESC, id DESC;
            """, (car_id, user_id))
            reminders = cur.fetchall()

            # выборка работ с учётом фильтров (where_sql уже включает j.user_id = %s у тебя)
            cur.execute(f"""
                SELECT j.id, j.mileage, j.job, j.cost, j.category, j.created_at
                FROM jobs j
                WHERE {where_sql}
                ORDER BY j.id DESC
                LIMIT 500;
            """, params)
            jobs = cur.fetchall()

            # суммы по отфильтрованным данным
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
    reminders_html = '<div class="grid grid-2"><div class="card glass card-total"><h2>Напоминания (ТО)</h2>'

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
    reminders_html += '</div>'

    if not reminders:
        reminders_html += '<div class="card glass card-total"><p><i>Пока нет напоминаний.</i></p></div>'
    else:
        reminders_html += '<div class="card glass card-total"><ul>'
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
                f'<li class="table-block"><b>{status}{escape(title)}</b>{active_txt} — '
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

    delete_car_html = f"""
      <form method="POST" action="/cars/{car_id}/delete">
        <button class="danger" type="submit"
                onclick="return confirm('Удалить автомобиль и все его записи?');">
          🗑 Удалить автомобиль
        </button>
      </form>
    """

    html = f"""
    <div class="header">
        <a href="/">← назад</a>
        {delete_car_html}
    </div>
    
    <h1>Работы: {escape(car[1])}</h1>

    {reminders_html}
    
    <div class="card glass card-total">
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
    </div>

    <div class="card glass card-total">
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
    </div>
    </div>

    <div class="grid total">
    <div class="card glass card-total">
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

    html += "</ul></div></div></div>"
    return page(f"Авто: {car[1]}", html)


@app.get("/jobs/<int:job_id>/edit")
@login_required
def edit_job_form(job_id: int):
    user_id = current_user_id()
    init_db()

    with psycopg.connect(DATABASE_URL) as conn:
        # список машин только пользователя (для select)
        cars = fetch_cars(conn, user_id)

        with conn.cursor() as cur:
            # запись должна принадлежать пользователю
            cur.execute("""
                SELECT id, car_id, category, mileage, job, cost
                FROM jobs
                WHERE id=%s AND user_id=%s;
            """, (job_id, user_id))
            row = cur.fetchone()

    if not row:
        return "Запись не найдена", 404

    _, car_id, category, mileage, job_text, cost = row

    cars_options = ""
    for cid, title, image_key in cars:
        selected = "selected" if cid == car_id else ""
        cars_options += f'<option value="{cid}" {selected}>{escape(title)}</option>'

    work_selected = "selected" if category == "work" else ""
    part_selected = "selected" if category == "part" else ""

    return page("Редактировать запись", f"""
      <div class="header">
        <a href="/cars/{car_id}">← назад</a>
      </div>

      <div class="card glass">
        <h2>Редактировать запись #{job_id}</h2>

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
          <input name="job" placeholder="Описание" required value="{escape(job_text)}">
          <input name="cost" placeholder="Стоимость (₽)" type="number" required value="{cost}">
          <button type="submit">Сохранить</button>
        </form>

        <form method="POST" action="/jobs/{job_id}/delete" style="margin-top:12px;">
          <button class="danger" type="submit" onclick="return confirm('Удалить запись?');">🗑 Удалить</button>
        </form>
      </div>
    """)

@app.post("/jobs/<int:job_id>/edit")
@login_required
def edit_job_save(job_id: int):
    user_id = current_user_id()

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
            # 1) проверяем что выбранное авто принадлежит пользователю
            cur.execute("SELECT 1 FROM cars WHERE id=%s AND user_id=%s;", (car_id, user_id))
            if not cur.fetchone():
                return "Автомобиль не найден", 404

            # 2) обновляем только свою запись
            cur.execute("""
                UPDATE jobs
                SET car_id=%s, category=%s, mileage=%s, job=%s, cost=%s
                WHERE id=%s AND user_id=%s
                RETURNING car_id;
            """, (car_id, category, mileage, job_text, cost, job_id, user_id))

            updated = cur.fetchone()
        conn.commit()

    if not updated:
        return "Запись не найдена", 404

    return redirect(f"/cars/{updated[0]}")

@app.post("/jobs/<int:job_id>/delete")
@login_required
def delete_job(job_id: int):
    user_id = current_user_id()
    init_db()

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1️⃣ Проверяем, что запись принадлежит пользователю
            cur.execute("""
                SELECT car_id
                FROM jobs
                WHERE id=%s AND user_id=%s;
            """, (job_id, user_id))
            row = cur.fetchone()

            if not row:
                return "Запись не найдена", 404

            car_id = row[0]

            # 2️⃣ Удаляем ТОЛЬКО свою запись
            cur.execute("""
                DELETE FROM jobs
                WHERE id=%s AND user_id=%s;
            """, (job_id, user_id))

        conn.commit()

    return redirect(f"/cars/{car_id}")


@app.post("/cars/<int:car_id>/delete")
@login_required
def delete_car(car_id: int):
    user_id = current_user_id()
    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cars WHERE id=%s AND user_id=%s;", (car_id, user_id))
        conn.commit()
    return redirect("/")


@app.post("/reminders/add")
@login_required
def reminder_add():
    user_id = current_user_id()          # ← ① ВОТ ЗДЕСЬ
    car_id = int(request.form["car_id"])
    title = (request.form.get("title") or "").strip()

    interval_km = request.form.get("interval_km") or ""
    interval_days = request.form.get("interval_days") or ""
    last_mileage = request.form.get("last_mileage") or "0"
    last_date = request.form.get("last_date") or date.today().isoformat()

    ikm = int(interval_km) if interval_km.isdigit() else None
    idays = int(interval_days) if interval_days.isdigit() else None
    lm = int(last_mileage) if str(last_mileage).lstrip("-").isdigit() else 0

    if not title:
        return redirect(f"/cars/{car_id}")

    if (ikm is None or ikm <= 0) and (idays is None or idays <= 0):
        return redirect(f"/cars/{car_id}")

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            # ← ② ВОТ ИМЕННО СЮДА
            cur.execute(
                "SELECT 1 FROM cars WHERE id=%s AND user_id=%s;",
                (car_id, user_id)
            )
            if not cur.fetchone():
                return redirect("/")   # авто не этого пользователя

            # ← ③ И ТОЛЬКО ПОТОМ INSERT
            cur.execute("""
                INSERT INTO reminders (
                    car_id, user_id, title,
                    interval_km, interval_days,
                    last_mileage, last_date, is_active
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s::date, TRUE);
            """, (car_id, user_id, title, ikm, idays, lm, last_date))

        conn.commit()

    return redirect(f"/cars/{car_id}")

@app.post("/reminders/<int:reminder_id>/done")
@login_required
def reminder_done(reminder_id: int):
    user_id = current_user_id()   # ← ВОТ ЗДЕСЬ
    car_id = int(request.form["car_id"])
    current_mileage = int(request.form.get("current_mileage") or 0)

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE reminders
                SET last_mileage=%s,
                    last_date=CURRENT_DATE
                WHERE id=%s AND user_id=%s;
            """, (current_mileage, reminder_id, user_id))

        conn.commit()

    return redirect(f"/cars/{car_id}")

@app.post("/reminders/<int:reminder_id>/toggle")
@login_required
def reminder_toggle(reminder_id: int):
    user_id = current_user_id()   # ← ВОТ ЗДЕСЬ
    car_id = int(request.form["car_id"])

    init_db()
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE reminders
                SET is_active = NOT is_active
                WHERE id=%s AND user_id=%s;
            """, (reminder_id, user_id))

        conn.commit()

    return redirect(f"/cars/{car_id}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
