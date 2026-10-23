from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import datetime
import phonenumbers
from phonenumbers import geocoder, carrier
import requests
import whois
import re

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./stark_osint.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class SearchHistory(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(title="STARK OSINT API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class SearchRequest(BaseModel):
    query: str
    type: str = "auto"

# --- НОВЫЕ ФУНКЦИИ ПОИСКА ---

def check_github(username):
    try:
        r = requests.get(f"https://api.github.com/users/{username}", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return f"Найден: {data.get('name', 'Без имени')}", "green", f"https://github.com/{username}", {"Репозиториев": data.get('public_repos', 0), "Подписчиков": data.get('followers', 0)}
        return "Не найден", "gray", f"https://github.com/{username}", {}
    except:
        return "Ошибка API", "gray", f"https://github.com/{username}", {}

def check_reddit(username):
    try:
        r = requests.get(f"https://www.reddit.com/user/{username}/about.json", timeout=5, headers={'User-Agent': 'STARK-OSINT/1.0'})
        if r.status_code == 200:
            data = r.json().get('data', {})
            return "Аккаунт существует", "green", f"https://reddit.com/user/{username}", {"Карма": data.get('total_karma', 0)}
        return "Не найден", "gray", f"https://reddit.com/user/{username}", {}
    except:
        return "Ошибка", "gray", f"https://reddit.com/user/{username}", {}

def check_ip(ip):
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}?lang=ru", timeout=5)
        data = r.json()
        if data.get("status") == "success":
            info = {
                "Страна": data.get('country', 'Неизвестно'),
                "Город": data.get('city', 'Неизвестно'),
                "Провайдер": data.get('isp', 'Неизвестно'),
                "Координаты": f"{data.get('lat')}, {data.get('lon')}"
            }
            return "Информация получена", "green", info
        return "Не удалось определить", "gray", {}
    except:
        return "Ошибка сети", "gray", {}

def check_vk(username):
    try:
        r = requests.get(f"https://m.vk.com/{username}", timeout=5, headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'})
        if r.status_code == 200 and "Ничего не найдено" not in r.text and "Запрашиваемая страница не найдена" not in r.text:
            return "Аккаунт существует", "green", f"https://vk.com/{username}"
        return "Не найден", "gray", f"https://vk.com/{username}"
    except:
        return "Ошибка", "gray", f"https://vk.com/{username}"

def check_telegram(username):
    try:
        r = requests.get(f"https://t.me/{username}", timeout=5, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'})
        if "captcha" in r.text.lower() or r.status_code == 429:
            return "Требуется ручная проверка", "gray", f"https://t.me/{username}"
        if r.status_code == 200 and "tgme_page_title" in r.text:
            match = re.search(r'<meta property="og:title" content="(.*?)"', r.text)
            return f"Найден: {match.group(1) if match else 'Да'}", "green", f"https://t.me/{username}"
        return "Не найден", "gray", f"https://t.me/{username}"
    except:
        return "Требуется проверка", "gray", f"https://t.me/{username}"

def get_whois(domain):
    try:
        w = whois.whois(domain)
        info = {
            "Регистратор": str(w.registrar) if w.registrar else "Скрыто",
            "Дата рег.": str(w.creation_date)[:10] if w.creation_date else "Неизвестно",
            "Страна": str(w.country) if w.country else "Неизвестно",
        }
        return info, "green"
    except:
        return {"Ошибка": "Не удалось получить WHOIS"}, "red"

# --- ОСНОВНОЙ ОБРАБОТЧИК ---
@app.post("/api/search")
async def search(req: SearchRequest, db: Session = Depends(get_db)):
    nodes = []
    edges = []
    query = req.query.strip()
    
    db.add(SearchHistory(query=query))
    db.commit()
    
    root_id = "root"
    nodes.append({"id": root_id, "type": "root", "data": {"label": f"Запрос: {query}"}})

    def add_node(node_id, title, status, color, info, links=None):
        nodes.append({"id": node_id, "type": "card", "data": {"title": title, "status": status, "statusColor": color, "info": info, "links": links or []}})
        edges.append({"id": f"{root_id}-{node_id}", "source": root_id, "target": node_id})

    # 1. Телефон
    if query.startswith("+") or (query.isdigit() and len(query) in [10, 11]):
        try:
            parsed = phonenumbers.parse(query if query.startswith("+") else f"+{query}", "RU")
            info = {
                "Страна": geocoder.description_for_number(parsed, "ru") or "Неизвестно",
                "Оператор": carrier.name_for_number(parsed, "ru") or "Неизвестно",
            }
            add_node("phone", "HLR запрос", "Номер существует", "green", info)
        except: pass

    # 2. Email
    elif "@" in query:
        domain = query.split("@")[-1]
        add_node("email", "Email", "Анализ домена", "green", {"Email": query, "Домен": domain}, 
                 [{"name": "Проверить утечки (HIBP)", "url": f"https://haveibeenpwned.com/account/{query}"},
                  {"name": "Epieos (Google аккаунт)", "url": f"https://epieos.com/?q={query}"}])

    # 3. IP-адрес
    elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", query):
        status, color, info = check_ip(query)
        add_node("ip", "IP Информация", status, color, info)

    # 4. Домен
    elif "." in query and not "@" in query:
        info, color = get_whois(query)
        add_node("whois", "WHOIS Домен", "Данные получены" if color=="green" else "Ошибка", color, info)

    # 5. Никнеймы (Соцсети)
    if query.isalnum() and not query.isdigit() and not "." in query and not "@" in query:
        s, c, u = check_vk(query); add_node("vk", "ВКонтакте", s, c, {"Ник": query}, [{"name": "Открыть", "url": u}])
        s, c, u = check_telegram(query); add_node("tg", "Telegram", s, c, {"Ник": query}, [{"name": "Открыть", "url": u}])
        s, c, u, inf = check_github(query); add_node("gh", "GitHub", s, c, inf or {"Ник": query}, [{"name": "Открыть", "url": u}])
        s, c, u, inf = check_reddit(query); add_node("rd", "Reddit", s, c, inf or {"Ник": query}, [{"name": "Открыть", "url": u}])
        add_node("inst", "Instagram", "Требуется Прокси", "gray", {"Ник": query}, [{"name": "Открыть", "url": f"https://www.instagram.com/{query}/"}])

    # 6. Поисковики (всегда)
    add_node("google", "Поиск Google", "Сформирован дорк", "green", {"Запрос": query}, [{"name": "Искать", "url": f"https://www.google.com/search?q=%22{query}%22"}])
    add_node("yandex", "Поиск Яндекс", "Сформирован запрос", "green", {"Запрос": query}, [{"name": "Искать", "url": f"https://yandex.ru/search/?text={query}"}])

    return {"nodes": nodes, "edges": edges}

@app.get("/api/history")
def get_history(db: Session = Depends(get_db)):
    history = db.query(SearchHistory).order_by(SearchHistory.timestamp.desc()).limit(10).all()
    return [{"query": h.query, "time": h.timestamp.strftime("%H:%M")} for h in history]