import tensorflow as tf
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image
import numpy as np
import cv2
import pytesseract
import os

# --- КОНФІГУРАЦІЯ PYTESSERACT ---
# ВАЖЛИВО: Замініть 'path/to/tesseract' на фактичний шлях до вашого виконуваного файлу Tesseract OCR.
# Для Windows це може бути щось на зразок r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Для Linux/macOS він зазвичай знаходиться в PATH, але якщо ні, вкажіть його тут.
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class PhotoAINavigatorProcessor:
    """
    Модуль обробки зображень для PhotoAI Navigator.
    Надає функціональність для автоматичного тегування, OCR та базового семантичного пошуку.
    """
    def __init__(self):
        print("Ініціалізація модуля PhotoAI Navigator Processor...")
        # Завантаження попередньо навченої моделі MobileNetV2 для класифікації зображень.
        # 'weights='imagenet'' гарантує використання ваг, навчених на ImageNet.
        try:
            self.image_tagging_model = MobileNetV2(weights='imagenet')
            print("Модель MobileNetV2 успішно завантажена.")
        except Exception as e:
            print(f"Помилка завантаження моделі MobileNetV2: {e}")
            print("Переконайтеся, що у вас є підключення до Інтернету для завантаження ваг,")
            print("або що ваги вже завантажені локально.")
            self.image_tagging_model = None

    def _preprocess_image_for_model(self, img_path):
        """
        Допоміжна функція для завантаження та попередньої обробки зображення для моделі MobileNetV2.
        """
        img = image.load_img(img_path, target_size=(224, 224)) # MobileNetV2 очікує вхід 224x224
        img_array = image.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0) # Додаємо вимір пакету (batch dimension)
        img_array = preprocess_input(img_array) # Попередня обробка відповідно до вимог MobileNetV2
        return img_array

    def auto_tag_image(self, image_path, top_n=5):
        """
        Автоматично тегує зображення за допомогою попередньо навченої моделі MobileNetV2.

        Аргументи:
            image_path (str): Шлях до файлу зображення.
            top_n (int): Кількість найкращих тегів для повернення.

        Повертає:
            list: Список рядків, де кожен рядок є згенерованим тегом.
                  Повертає порожній список, якщо обробка не вдалася або модель не завантажена.
        """
        if self.image_tagging_model is None:
            print("Помилка: Модель тегування зображень не завантажена.")
            return []

        if not os.path.exists(image_path):
            print(f"Помилка: Зображення не знайдено за шляхом: {image_path}")
            return []

        try:
            processed_image = self._preprocess_image_for_model(image_path)
            predictions = self.image_tagging_model.predict(processed_image)
            # Декодування передбачень у читабельні мітки (теги)
            decoded_predictions = decode_predictions(predictions, top=top_n)[0]

            tags = [label for (imagenet_id, label, score) in decoded_predictions]
            print(f"Теги для {os.path.basename(image_path)}: {tags}")
            return tags
        except Exception as e:
            print(f"Помилка під час автоматичного тегування для {image_path}: {e}")
            return []

    def extract_text_from_image(self, image_path):
        """
        Витягує текст із зображення за допомогою Tesseract OCR.

        Аргументи:
            image_path (str): Шлях до файлу зображення.

        Повертає:
            str: Витягнутий текст із зображення.
                 Повертає порожній рядок, якщо обробка не вдалася або текст не знайдено.
        """
        if not os.path.exists(image_path):
            print(f"Помилка: Зображення не знайдено за шляхом: {image_path}")
            return ""

        try:
            # Завантаження зображення за допомогою OpenCV
            img = cv2.imread(image_path)
            if img is None:
                print(f"Помилка: Не вдалося завантажити зображення за допомогою OpenCV за шляхом: {image_path}")
                return ""

            # Перетворення в відтінки сірого для кращої точності OCR
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Використання pytesseract для вилучення тексту
            text = pytesseract.image_to_string(gray_img)
            # Друк перших 50 символів витягнутого тексту для зручності
            print(f"Витягнутий текст з {os.path.basename(image_path)}: '{text.strip()[:50]}...'")
            return text.strip()
        except pytesseract.TesseractNotFoundError:
            print("Помилка: Tesseract не встановлено або не знайдено у вашому PATH.")
            print("Будь ласка, встановіть Tesseract OCR та переконайтеся, що він доступний,")
            print("або налаштуйте pytesseract.pytesseract.tesseract_cmd.")
            return ""
        except Exception as e:
            print(f"Помилка під час OCR для {image_path}: {e}")
            return ""

    def semantic_search_placeholder(self, query, image_metadata_list):
        """
        Заповнювач для функціональності семантичного пошуку.
        У реальному застосунку це включатиме:
        1. Генерацію вбудовувань (embeddings) для запиту.
        2. Генерацію вбудовувань для вмісту зображень (наприклад, з виявлення об'єктів, розуміння сцени).
        3. Зберігання цих вбудовувань у векторній базі даних (наприклад, FAISS, Pinecone).
        4. Виконання пошуку за схожістю.

        Для цього прикладу виконується простий пошук за ключовими словами в тегах та тексті OCR.

        Аргументи:
            query (str): Пошуковий запит (наприклад, "кіт грає в парку").
            image_metadata_list (list): Список словників, де кожен словник містить
                                        'path', 'tags' та 'ocr_text' для зображення.
                                        Приклад: [{'path': 'img1.jpg', 'tags': ['кіт', 'парк'], 'ocr_text': 'Ласкаво просимо до парку'}]

        Повертає:
            list: Список шляхів до зображень, які відповідають запиту.
        """
        print(f"Виконання базового семантичного пошуку за запитом: '{query}'")
        query_lower = query.lower()
        matching_images = []

        for metadata in image_metadata_list:
            image_path = metadata.get('path')
            tags = metadata.get('tags', [])
            ocr_text = metadata.get('ocr_text', '')

            # Перевірка, чи слова запиту є в тегах або тексті OCR
            # Це дуже просте зіставлення ключових слів, а не справжній семантичний пошук
            found_in_tags = any(query_word in tag.lower() for query_word in query_lower.split() for tag in tags)
            found_in_ocr = query_lower in ocr_text.lower()

            if found_in_tags or found_in_ocr:
                matching_images.append(image_path)

        print(f"Знайдено {len(matching_images)} відповідних зображень.")
        return matching_images

# --- ПРИКЛАД ВИКОРИСТАННЯ ---
if __name__ == "__main__":
    # Створення фіктивного зображення для тестування, якщо воно не існує.
    # У реальному застосунку ви б замінили це на фактичні шляхи до зображень.
    dummy_image_path = "test_image_photoai.jpg"
    if not os.path.exists(dummy_image_path):
        print(f"Створення фіктивного зображення '{dummy_image_path}' для тестування...")
        try:
            # Створення простого білого зображення з текстом
            dummy_img = np.zeros((300, 500, 3), dtype=np.uint8) + 255 # Білий фон
            cv2.putText(dummy_img, "Hello PhotoAI Navigator!", (50, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(dummy_img, "Welcome to the Park!", (50, 200),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.imwrite(dummy_image_path, dummy_img)
            print(f"Фіктивне зображення '{dummy_image_path}' створено.")
        except Exception as e:
            print(f"Не вдалося створити фіктивне зображення. Переконайтеся, що OpenCV встановлено. Помилка: {e}")
            dummy_image_path = None # Позначаємо як недоступне для тестування

    if dummy_image_path:
        processor = PhotoAINavigatorProcessor()

        print("
--- Тестування автоматичного тегування ---")
        tags = processor.auto_tag_image(dummy_image_path)
        print(f"Згенеровані теги: {tags}")

        print("
--- Тестування OCR ---")
        extracted_text = processor.extract_text_from_image(dummy_image_path)
        print(f"Витягнутий текст: '{extracted_text}'")

        print("
--- Тестування заповнювача семантичного пошуку ---")
        # Імітація деяких метаданих зображень, які зберігалися б у SQLite
        # У реальному сценарії вони надходили б із запиту до бази даних
        sample_image_metadata = [
            {'path': dummy_image_path, 'tags': tags, 'ocr_text': extracted_text},
            {'path': 'another_image_with_cat.jpg', 'tags': ['кіт', 'тварина', 'домашній улюбленець'], 'ocr_text': 'Мій милий кіт'},
            {'path': 'birthday_party.png', 'tags': ['день народження', 'вечірка', 'торт'], 'ocr_text': 'З Днем Народження!'},
            {'path': 'park_scene.jpeg', 'tags': ['парк', 'дерево', 'природа'], 'ocr_text': 'Прекрасний день у парку'}
        ]

        search_results_cat = processor.semantic_search_placeholder("кіт грає", sample_image_metadata)
        print(f"Результати пошуку за 'кіт грає': {search_results_cat}")

        search_results_park = processor.semantic_search_placeholder("парк", sample_image_metadata)
        print(f"Результати пошуку за 'парк': {search_results_park}")

        search_results_birthday = processor.semantic_search_placeholder("мій день народження", sample_image_metadata)
        print(f"Результати пошуку за 'мій день народження': {search_results_birthday}")

        search_results_hello = processor.semantic_search_placeholder("Hello Navigator", sample_image_metadata)
        print(f"Результати пошуку за 'Hello Navigator': {search_results_hello}")

    else:
        print("
Приклад використання пропущено, оскільки фіктивне зображення не вдалося створити.")
