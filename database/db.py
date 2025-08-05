import sqlite3
from typing import List, Dict, Optional, Tuple, Any

class DatabaseManager:
    def __init__(self, db_path: str = 'photo_ai_navigator.db'):
        """
        Ініціалізує DatabaseManager, підключається до бази даних SQLite
        та створює необхідні таблиці, якщо вони не існують.

        Args:
            db_path (str): Шлях до файлу бази даних SQLite.
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Встановлює з'єднання з базою даних SQLite."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            print(f"Помилка підключення до бази даних: {e}")
            # У реальному застосунку можна було б викликати виняток або логувати більш детально.

    def _create_tables(self):
        """Створює таблиці 'images', 'tags' та 'image_tags', якщо вони ще не існують."""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY,
                    file_path TEXT UNIQUE NOT NULL,
                    capture_date TEXT,
                    camera_model TEXT,
                    latitude REAL,
                    longitude REAL
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                )
            ''')
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS image_tags (
                    image_id INTEGER,
                    tag_id INTEGER,
                    PRIMARY KEY (image_id, tag_id),
                    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Помилка створення таблиць: {e}")

    def close(self):
        """Закриває з'єднання з базою даних."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def __enter__(self):
        """Точка входу для менеджера контексту."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Точка виходу для менеджера контексту, забезпечує закриття з'єднання."""
        self.close()

    def add_image(self, file_path: str, capture_date: str, camera_model: Optional[str] = None,
                  latitude: Optional[float] = None, longitude: Optional[float] = None) -> Optional[int]:
        """
        Додає новий запис зображення до бази даних.

        Args:
            file_path (str): Унікальний шлях до файлу зображення.
            capture_date (str): Дата та час зйомки зображення (наприклад, 'YYYY-MM-DD HH:MM:SS').
            camera_model (Optional[str]): Модель камери, яка використовувалася.
            latitude (Optional[float]): Географічна широта.
            longitude (Optional[float]): Географічна довгота.

        Returns:
            Optional[int]: ID щойно доданого зображення, або None, якщо сталася помилка
                           (наприклад, file_path вже існує).
        """
        try:
            self.cursor.execute('''
                INSERT INTO images (file_path, capture_date, camera_model, latitude, longitude)
                VALUES (?, ?, ?, ?, ?)
            ''', (file_path, capture_date, camera_model, latitude, longitude))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Помилка: Зображення зі шляхом файлу '{file_path}' вже існує.")
            return None
        except sqlite3.Error as e:
            print(f"Помилка додавання зображення: {e}")
            return None

    def add_tag(self, tag_name: str) -> Optional[int]:
        """
        Додає новий тег до бази даних. Якщо тег вже існує, повертається його ID.

        Args:
            tag_name (str): Назва тегу.

        Returns:
            Optional[int]: ID тегу, або None, якщо сталася помилка.
        """
        try:
            self.cursor.execute('INSERT INTO tags (name) VALUES (?)', (tag_name,))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            # Тег вже існує, отримуємо його ID
            self.cursor.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
            tag_id = self.cursor.fetchone()
            return tag_id[0] if tag_id else None
        except sqlite3.Error as e:
            print(f"Помилка додавання тегу '{tag_name}': {e}")
            return None

    def link_tag_to_image(self, image_id: int, tag_id: int) -> bool:
        """
        Прив'язує тег до зображення.

        Args:
            image_id (int): ID зображення.
            tag_id (int): ID тегу.

        Returns:
            bool: True, якщо зв'язок успішно створено або вже існував, False в іншому випадку.
        """
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO image_tags (image_id, tag_id)
                VALUES (?, ?)
            ''', (image_id, tag_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Помилка прив'язки тегу {tag_id} до зображення {image_id}: {e}")
            return False

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """
        Отримує всі теги з бази даних.

        Returns:
            List[Dict[str, Any]]: Список словників, кожен з яких представляє тег з 'id' та 'name'.
        """
        self.cursor.execute('SELECT id, name FROM tags ORDER BY name')
        return [{'id': row[0], 'name': row[1]} for row in self.cursor.fetchall()]

    def delete_tag(self, tag_id: int) -> bool:
        """
        Видаляє тег з бази даних та всі його асоціації із зображеннями.

        Args:
            tag_id (int): ID тегу для видалення.

        Returns:
            bool: True, якщо тег успішно видалено, False в іншому випадку.
        """
        try:
            # ON DELETE CASCADE у таблиці image_tags обробляє видалення асоціацій
            self.cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Помилка видалення тегу {tag_id}: {e}")
            return False

    def get_images_by_tags(self, tag_names: List[str]) -> List[Dict[str, Any]]:
        """
        Отримує зображення, які пов'язані з УСІМА вказаними тегами.

        Args:
            tag_names (List[str]): Список назв тегів для фільтрації.

        Returns:
            List[Dict[str, Any]]: Список словників, кожен з яких представляє зображення.
        """
        if not tag_names:
            return []

        placeholders = ','.join(['?' for _ in tag_names])
        query = f'''
            SELECT
                i.id, i.file_path, i.capture_date, i.camera_model, i.latitude, i.longitude
            FROM
                images i
            JOIN
                image_tags it ON i.id = it.image_id
            JOIN
                tags t ON it.tag_id = t.id
            WHERE
                t.name IN ({placeholders})
            GROUP BY
                i.id
            HAVING
                COUNT(DISTINCT t.id) = ?
        '''
        try:
            self.cursor.execute(query, tag_names + [len(tag_names)])
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Помилка отримання зображень за тегами: {e}")
            return []

    def get_images_by_metadata(self, start_date: Optional[str] = None, end_date: Optional[str] = None,
                               camera_model: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Отримує зображення на основі фільтрів метаданих (діапазон дат та/або модель камери).

        Args:
            start_date (Optional[str]): Початкова дата для фільтрації (наприклад, 'YYYY-MM-DD').
            end_date (Optional[str]): Кінцева дата для фільтрації (наприклад, 'YYYY-MM-DD').
            camera_model (Optional[str]): Часткова або повна назва моделі камери для фільтрації.

        Returns:
            List[Dict[str, Any]]: Список словників, кожен з яких представляє зображення.
        """
        query = 'SELECT id, file_path, capture_date, camera_model, latitude, longitude FROM images WHERE 1=1'
        params = []

        if start_date:
            query += ' AND capture_date >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND capture_date <= ?'
            params.append(end_date)
        if camera_model:
            query += ' AND camera_model LIKE ?'
            params.append(f'%{camera_model}%')

        try:
            self.cursor.execute(query, params)
            columns = [description[0] for description in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Помилка отримання зображень за метаданими: {e}")
            return []

    def get_image_by_id(self, image_id: int) -> Optional[Dict[str, Any]]:
        """
        Допоміжна функція для отримання одного зображення за його ID.

        Args:
            image_id (int): ID зображення.

        Returns:
            Optional[Dict[str, Any]]: Словник, що представляє зображення, або None, якщо не знайдено.
        """
        try:
            self.cursor.execute('SELECT id, file_path, capture_date, camera_model, latitude, longitude FROM images WHERE id = ?', (image_id,))
            row = self.cursor.fetchone()
            if row:
                columns = [description[0] for description in self.cursor.description]
                return dict(zip(columns, row))
            return None
        except sqlite3.Error as e:
            print(f"Помилка отримання зображення за ID {image_id}: {e}")
            return None

    def get_tags_for_image(self, image_id: int) -> List[Dict[str, Any]]:
        """
        Допоміжна функція для отримання всіх тегів, пов'язаних з конкретним зображенням.

        Args:
            image_id (int): ID зображення.

        Returns:
            List[Dict[str, Any]]: Список словників, кожен з яких представляє тег.
        """
        try:
            self.cursor.execute('''
                SELECT t.id, t.name
                FROM tags t
                JOIN image_tags it ON t.id = it.tag_id
                WHERE it.image_id = ?
                ORDER BY t.name
            ''', (image_id,))
            return [{'id': row[0], 'name': row[1]} for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Помилка отримання тегів для зображення {image_id}: {e}")
            return []

# Приклад використання (для демонстрації, може бути розміщений в окремому тестовому файлі)
if __name__ == '__main__':
    db_file = 'test_photo_ai_navigator.db'
    # Очищення попередньої тестової БД, якщо існує
    import os
    if os.path.exists(db_file):
        os.remove(db_file)

    print(f"Використовується база даних: {db_file}")

    with DatabaseManager(db_path=db_file) as db:
        print("--- Додавання зображень ---")
        img1_id = db.add_image('/path/to/img1.jpg', '2023-01-15 10:00:00', 'Canon EOS R5', 40.7128, -74.0060)
        img2_id = db.add_image('/path/to/img2.png', '2023-01-20 14:30:00', 'Sony Alpha A7 III', 34.0522, -118.2437)
        img3_id = db.add_image('/path/to/img3.jpeg', '2023-02-01 09:15:00', 'Canon EOS R5', 51.5074, 0.1278)
        img4_id = db.add_image('/path/to/img4.gif', '2023-02-10 18:00:00', 'Nikon D850', None, None)
        img5_id = db.add_image('/path/to/img5.jpg', '2023-03-05 11:20:00', 'Sony Alpha A7 III', 35.6895, 139.6917)

        # Спроба додати дублікат зображення
        db.add_image('/path/to/img1.jpg', '2023-01-15 10:00:00', 'Canon EOS R5', 40.7128, -74.0060)

        print(f"Додані зображення: img1_id={img1_id}, img2_id={img2_id}, img3_id={img3_id}, img4_id={img4_id}, img5_id={img5_id}")

        print("
--- Додавання тегів ---")
        tag_nature_id = db.add_tag('Nature')
        tag_city_id = db.add_tag('City')
        tag_landscape_id = db.add_tag('Landscape')
        tag_portrait_id = db.add_tag('Portrait')
        tag_newyork_id = db.add_tag('New York')
        tag_london_id = db.add_tag('London')
        tag_tokyo_id = db.add_tag('Tokyo')

        # Спроба додати дублікат тегу
        db.add_tag('Nature')

        print(f"Додані теги: Nature={tag_nature_id}, City={tag_city_id}, Landscape={tag_landscape_id}, Portrait={tag_portrait_id}")

        print("
--- Прив'язка тегів до зображень ---")
        if img1_id and tag_city_id and tag_newyork_id:
            db.link_tag_to_image(img1_id, tag_city_id)
            db.link_tag_to_image(img1_id, tag_newyork_id)
            db.link_tag_to_image(img1_id, tag_landscape_id) # img1 - це міський пейзаж

        if img2_id and tag_city_id:
            db.link_tag_to_image(img2_id, tag_city_id)

        if img3_id and tag_city_id and tag_london_id:
            db.link_tag_to_image(img3_id, tag_city_id)
            db.link_tag_to_image(img3_id, tag_london_id)

        if img4_id and tag_nature_id and tag_landscape_id:
            db.link_tag_to_image(img4_id, tag_nature_id)
            db.link_tag_to_image(img4_id, tag_landscape_id)

        if img5_id and tag_city_id and tag_tokyo_id:
            db.link_tag_to_image(img5_id, tag_city_id)
            db.link_tag_to_image(img5_id, tag_tokyo_id)

        print("
--- Всі теги ---")
        all_tags = db.get_all_tags()
        for tag in all_tags:
            print(f"- {tag['name']} (ID: {tag['id']})")

        print("
--- Зображення за тегами (City та Landscape) ---")
        city_landscape_images = db.get_images_by_tags(['City', 'Landscape'])
        for img in city_landscape_images:
            print(f"- {img['file_path']} (ID: {img['id']})")
            tags_for_img = db.get_tags_for_image(img['id'])
            print(f"  Теги: {[t['name'] for t in tags_for_img]}")

        print("
--- Зображення за тегами (Nature) ---")
        nature_images = db.get_images_by_tags(['Nature'])
        for img in nature_images:
            print(f"- {img['file_path']} (ID: {img['id']})")

        print("
--- Зображення за метаданими (Canon EOS R5) ---")
        canon_images = db.get_images_by_metadata(camera_model='Canon EOS R5')
        for img in canon_images:
            print(f"- {img['file_path']} (Камера: {img['camera_model']})")

        print("
--- Зображення за метаданими (Діапазон дат: Січень 2023) ---")
        jan_images = db.get_images_by_metadata(start_date='2023-01-01', end_date='2023-01-31')
        for img in jan_images:
            print(f"- {img['file_path']} (Дата: {img['capture_date']})")

        print("
--- Зображення за метаданими (Sony Alpha A7 III у березні 2023) ---")
        sony_march_images = db.get_images_by_metadata(start_date='2023-03-01', end_date='2023-03-31', camera_model='Sony Alpha A7 III')
        for img in sony_march_images:
            print(f"- {img['file_path']} (Дата: {img['capture_date']}, Камера: {img['camera_model']})")

        print("
--- Видалення тегу (New York) ---")
        if tag_newyork_id:
            deleted = db.delete_tag(tag_newyork_id)
            print(f"Тег 'New York' видалено: {deleted}")

        print("
--- Всі теги після видалення ---")
        all_tags_after_delete = db.get_all_tags()
        for tag in all_tags_after_delete:
            print(f"- {tag['name']} (ID: {tag['id']})")

        print("
--- Зображення за тегами (City та New York) після видалення ---")
        # Це повинно повернути менше зображень або жодного, якщо New York був єдиним відмінним тегом
        city_newyork_images_after_delete = db.get_images_by_tags(['City', 'New York'])
        if not city_newyork_images_after_delete:
            print("Зображень з тегами 'City' та 'New York' не знайдено (оскільки 'New York' було видалено або не було пов'язано з іншими зображеннями).")
        for img in city_newyork_images_after_delete:
            print(f"- {img['file_path']} (ID: {img['id']})")

    print("
Операції з базою даних завершено. З'єднання закрито.")
    # os.remove(db_file) # Розкоментуйте, щоб видалити файл тестової бази даних після запуску