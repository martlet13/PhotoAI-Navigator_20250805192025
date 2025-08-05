import sqlite3
import json
import asyncio
from typing import List, Optional, Dict, Set

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
import uvicorn

# --- Конфігурація бази даних ---
DATABASE_FILE = "photo_metadata.db"

def get_db_connection():
    """Створює та повертає з'єднання з базою даних SQLite."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row  # Дозволяє доступ до стовпців за іменем
    return conn

def init_db():
    """Ініціалізує базу даних, створюючи таблицю 'photos', якщо вона не існує."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            date_taken TEXT,
            location TEXT,
            camera_model TEXT,
            tags TEXT
        )
    """)
    conn.commit()
    conn.close()

def db_add_sample_data():
    """Додає зразкові дані до бази даних для тестування."""
    conn = get_db_connection()
    cursor = conn.cursor()
    sample_photos = [
        ("C:/photos/vacation/beach.jpg", "beach.jpg", "2023-07-15 10:30:00", "Пляж", "Canon EOS R5", ["відпустка", "пляж", "літо"]),
        ("C:/photos/city/skyline.png", "skyline.png", "2023-01-20 18:00:00", "Центр міста", "Sony Alpha 7 III", ["місто", "ніч", "архітектура"]),
        ("C:/photos/nature/mountain.jpeg", "mountain.jpeg", "2022-09-01 08:00:00", "Гори", "Nikon D850", ["природа", "похід", "пейзаж"]),
        ("C:/photos/family/birthday.jpg", "birthday.jpg", "2023-03-10 14:00:00", "Дім", "iPhone 13 Pro", ["сім'я", "день народження", "свято"])
    ]
    for path, filename, date_taken, location, camera_model, tags in sample_photos:
        try:
            cursor.execute(
                "INSERT INTO photos (path, filename, date_taken, location, camera_model, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (path, filename, date_taken, location, camera_model, json.dumps(tags))
            )
        except sqlite3.IntegrityError:
            # Пропускаємо, якщо фото з таким шляхом вже існує
            pass
    conn.commit()
    conn.close()

# --- Моделі Pydantic ---
class Photo(BaseModel):
    """Модель даних для фотографії."""
    id: int
    path: str
    filename: str
    date_taken: str  # Формат ISO (YYYY-MM-DD HH:MM:SS)
    location: Optional[str] = None
    camera_model: Optional[str] = None
    tags: List[str] = []  # Список тегів

class PhotoFilter(BaseModel):
    """Модель для параметрів фільтрації фотографій."""
    date_from: Optional[str] = None  # YYYY-MM-DD
    date_to: Optional[str] = None    # YYYY-MM-DD
    tags: Optional[List[str]] = None
    location: Optional[str] = None
    camera_model: Optional[str] = None

class TagUpdate(BaseModel):
    """Модель для оновлення/додавання/видалення тегів."""
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None

class CloudSyncRequest(BaseModel):
    """Модель для запиту синхронізації з хмарним сховищем."""
    service: str  # Наприклад, "google_drive", "dropbox"
    # У реальній реалізації тут можуть бути додаткові поля, такі як облікові дані, ID папки тощо.

# --- Функції взаємодії з базою даних (заглушки) ---
def db_get_photos(filters: PhotoFilter) -> List[Photo]:
    """
    Отримує список фотографій з бази даних, застосовуючи фільтри.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM photos WHERE 1=1"
    params = []

    if filters.date_from:
        query += " AND date_taken >= ?"
        params.append(filters.date_from)
    if filters.date_to:
        query += " AND date_taken <= ?"
        params.append(filters.date_to)
    if filters.location:
        query += " AND location LIKE ?"
        params.append(f"%{filters.location}%")
    if filters.camera_model:
        query += " AND camera_model LIKE ?"
        params.append(f"%{filters.camera_model}%")
    if filters.tags:
        # Для пошуку тегів у JSON-рядку
        for tag in filters.tags:
            query += " AND tags LIKE ?"
            params.append(f"%\"{tag}\"%")

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    photos = []
    for row in rows:
        tags = json.loads(row['tags']) if row['tags'] else []
        photos.append(Photo(
            id=row['id'],
            path=row['path'],
            filename=row['filename'],
            date_taken=row['date_taken'],
            location=row['location'],
            camera_model=row['camera_model'],
            tags=tags
        ))
    return photos

def db_update_photo_tags(photo_id: int, add_tags: Optional[List[str]], remove_tags: Optional[List[str]]) -> bool:
    """
    Оновлює теги для конкретної фотографії в базі даних.
    Повертає True у разі успіху, False, якщо фото не знайдено.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT tags FROM photos WHERE id = ?", (photo_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False  # Фото не знайдено

    current_tags: Set[str] = set(json.loads(row['tags'])) if row['tags'] else set()

    if add_tags:
        current_tags.update(add_tags)
    if remove_tags:
        current_tags.difference_update(remove_tags)

    new_tags_json = json.dumps(list(current_tags))
    cursor.execute("UPDATE photos SET tags = ? WHERE id = ?", (new_tags_json, photo_id))
    conn.commit()
    conn.close()
    return True

# --- Функції інтеграції з хмарними сховищами (заглушки) ---
async def sync_with_google_drive():
    """Заглушка для функції синхронізації з Google Drive."""
    print("Ініціюється синхронізація з Google Drive...")
    # Імітація асинхронної роботи
    await asyncio.sleep(5)
    print("Синхронізація з Google Drive завершена.")
    # У реальному сценарії тут буде логіка взаємодії з Google Drive API:
    # 1. Аутентифікація (OAuth 2.0)
    # 2. Перегляд файлів/папок
    # 3. Завантаження метаданих/мініатюр
    # 4. Оновлення локальної бази даних
    return {"status": "success", "message": "Синхронізація з Google Drive ініційована."}

async def sync_with_dropbox():
    """Заглушка для функції синхронізації з Dropbox."""
    print("Ініціюється синхронізація з Dropbox...")
    # Імітація асинхронної роботи
    await asyncio.sleep(3)
    print("Синхронізація з Dropbox завершена.")
    # Аналогічно Google Drive, але з використанням Dropbox API
    return {"status": "success", "message": "Синхронізація з Dropbox ініційована."}

# --- Ініціалізація FastAPI ---
app = FastAPI(
    title="PhotoAI Navigator API",
    description="API для фільтрації метаданих, керування тегами та інтеграції з хмарними сховищами.",
    version="1.0.0"
)

# --- Обробники подій FastAPI ---
@app.on_event("startup")
async def startup_event():
    """Виконується при запуску програми: ініціалізує БД та додає зразкові дані."""
    init_db()
    db_add_sample_data()  # Додаємо деякі початкові дані для тестування

# --- Кінцеві точки API ---
@app.get("/")
async def read_root():
    """Базова кінцева точка для перевірки роботи API."""
    return {"message": "Ласкаво просимо до PhotoAI Navigator API!"}

@app.get("/photos", response_model=List[Photo])
async def get_photos(
    date_from: Optional[str] = Query(None, description="Фільтрувати фотографії, зроблені з цієї дати (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Фільтрувати фотографії, зроблені до цієї дати (YYYY-MM-DD)"),
    tags: Optional[List[str]] = Query(None, description="Фільтрувати фотографії за тегами (розділені комами)"),
    location: Optional[str] = Query(None, description="Фільтрувати фотографії за місцем розташування"),
    camera_model: Optional[str] = Query(None, description="Фільтрувати фотографії за моделлю камери")
):
    """
    Отримує список фотографій з можливістю фільтрації за датою, тегами, місцем розташування або моделлю камери.
    """
    filters = PhotoFilter(
        date_from=date_from,
        date_to=date_to,
        tags=tags,
        location=location,
        camera_model=camera_model
    )
    photos = db_get_photos(filters)
    return photos

@app.put("/photos/{photo_id}/tags", response_model=Dict[str, str])
async def update_photo_tags(photo_id: int, tag_update: TagUpdate):
    """
    Оновлює або додає теги для конкретної фотографії.
    - `add_tags`: Список тегів для додавання.
    - `remove_tags`: Список тегів для видалення.
    """
    success = db_update_photo_tags(photo_id, tag_update.add_tags, tag_update.remove_tags)
    if not success:
        raise HTTPException(status_code=404, detail="Фотографію не знайдено.")
    return {"message": f"Теги для фотографії {photo_id} успішно оновлено."}

@app.delete("/photos/{photo_id}/tags", response_model=Dict[str, str])
async def delete_photo_tags(photo_id: int, tags_to_delete: List[str]):
    """
    Видаляє вказані теги з фотографії.
    """
    # Використовуємо ту ж функцію оновлення, передаючи теги для видалення
    success = db_update_photo_tags(photo_id, None, tags_to_delete)
    if not success:
        raise HTTPException(status_code=404, detail="Фотографію не знайдено.")
    return {"message": f"Теги успішно видалено з фотографії {photo_id}."}

@app.post("/cloud/sync", response_model=Dict[str, str])
async def initiate_cloud_sync(sync_request: CloudSyncRequest, background_tasks: BackgroundTasks):
    """
    Ініціює синхронізацію з вказаним хмарним сховищем.
    Синхронізація виконується у фоновому режимі.
    """
    if sync_request.service == "google_drive":
        background_tasks.add_task(sync_with_google_drive)
        return {"message": "Синхронізація з Google Drive ініційована у фоновому режимі."}
    elif sync_request.service == "dropbox":
        background_tasks.add_task(sync_with_dropbox)
        return {"message": "Синхронізація з Dropbox ініційована у фоновому режимі."}
    else:
        raise HTTPException(status_code=400, detail="Непідтримуваний хмарний сервіс. Підтримуються: 'google_drive', 'dropbox'.")

# --- Запуск програми ---
if __name__ == "__main__":
    # Для запуску API:
    # 1. Встановіть необхідні бібліотеки: pip install fastapi uvicorn pydantic
    # 2. Запустіть цей файл: python your_file_name.py
    # 3. Відкрийте в браузері: http://127.0.0.1:8000/docs для інтерактивної документації.
    uvicorn.run(app, host="0.0.0.0", port=8000)