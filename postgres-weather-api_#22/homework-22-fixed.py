import requests
import psycopg
from dotenv import load_dotenv
import os

load_dotenv()

def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def create_tables(connection):
    with connection.cursor() as my_cursor:
        my_cursor.execute('''
            DROP TABLE IF EXISTS posts;
            CREATE TABLE IF NOT EXISTS posts(
                id SERIAL PRIMARY KEY,
                userId INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL
            );
            DROP TABLE IF EXISTS comments;
            CREATE TABLE IF NOT EXISTS comments(
                id SERIAL PRIMARY KEY,
                postId INTEGER NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                body TEXT NOT NULL
            );
            DROP TABLE IF EXISTS albums;
            CREATE TABLE IF NOT EXISTS albums(
                id SERIAL PRIMARY KEY,
                userId INTEGER NOT NULL,
                title TEXT NOT NULL
            );
            DROP TABLE IF EXISTS photos;
            CREATE TABLE IF NOT EXISTS photos(
                id SERIAL PRIMARY KEY,
                albumId INTEGER NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                thumbnailUrl TEXT NOT NULL
            );
            DROP TABLE IF EXISTS todos;
            CREATE TABLE IF NOT EXISTS todos(
                id SERIAL PRIMARY KEY,
                userId INTEGER NOT NULL,
                title TEXT NOT NULL,
                completed BOOLEAN NOT NULL
            );
            DROP TABLE IF EXISTS users;
            CREATE TABLE IF NOT EXISTS users(
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                website TEXT NOT NULL
            );
            DROP TABLE IF EXISTS fake_users;
            CREATE TABLE IF NOT EXISTS fake_users(
                id SERIAL PRIMARY KEY,
                firstName TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL
            );
            DROP TABLE IF EXISTS weather;
            CREATE TABLE IF NOT EXISTS weather (
                id SERIAL PRIMARY KEY,
                city TEXT NOT NULL,
                description TEXT NOT NULL,
                temp REAL NOT NULL,
                wind REAL NOT NULL
            );
        ''')
        connection.commit()

def make_request(url, endpoint_real):
    response = requests.get(f'{url}{endpoint_real}')
    response.raise_for_status()
    return response.json()

def weather_request(w_url, parameter):
    response = requests.get(w_url, params = parameter)
    response.raise_for_status()
    result = response.json()
    print(
        f'\nDescription: {result["weather"][0]["description"]}\n'
        f'Temp: {result["main"]["temp"]}°C\n'
        f'Wind Speed km/h: {result["wind"]["speed"]} m/s'
    )
    return result

def main():
    # как то было без разницы на ругательство про lower case...
    URL = 'https://jsonplaceholder.typicode.com/'
    W_URL = 'https://api.openweathermap.org/data/2.5/weather'
    J_URL = 'https://dummyjson.com/'
    ENDPOINTS_CONFIG = {
        'posts': ['userId', 'title', 'body'],
        'comments': ['postId', 'name', 'email', 'body'],
        'albums': ['userId', 'title'],
        'photos': ['albumId', 'title', 'url', 'thumbnailUrl'],
        'todos': ['userId', 'title', 'completed'],
        'users': ['name', 'username', 'email', 'phone', 'website'],
        'fake_users': ['firstName', 'email', 'phone'],
        'weather': ['city', 'description', 'temp', 'wind']
    }
    print("=== Запуск программы ===")
    user_city = input('Введите название города ИЛИ "exit" для выхода: ').lower()
    try:
        with get_connection() as connection:
            print("Соединение установлено!")
            with connection.cursor() as my_cursor:
                print("Проверка и создание таблиц...")
                create_tables(connection)
                print("Таблицы готовы.\n")
                for endpoint, keys in ENDPOINTS_CONFIG.items():
                    if endpoint not in ('weather', 'fake_users'):
                        data = [tuple(i[k] for k in keys) for i in make_request(URL, endpoint)]
                        columns = ', '.join(keys)
                        with my_cursor.copy(f'COPY {endpoint} ({columns}) FROM STDIN') as copy:
                            for row in data:
                                copy.write_row(row)
                        connection.commit()
                        print(f"[OK] Таблица '{endpoint}': загружено {len(data)} строк.")
                    elif endpoint == 'fake_users':
                        data = [tuple(i[k] for k in keys) for i in make_request(J_URL, 'users')['users']]
                        columns = ', '.join(keys)
                        with my_cursor.copy(f'COPY {endpoint} ({columns}) FROM STDIN') as copy:
                            for row in data:
                                copy.write_row(row)
                        connection.commit()
                        print(f"[OK] Таблица '{endpoint}': загружено {len(data)} строк.")
                weather_keys = ENDPOINTS_CONFIG['weather']
                columns = ', '.join(weather_keys)
                placeholders = ', '.join(['%s' for _ in weather_keys])
                while user_city != 'exit':
                    parameters = {
                        'q': user_city,
                        'appid': os.getenv("WEATHER_API_KEY"),
                        'units': 'metric'
                    }
                    try:
                        data = weather_request(W_URL, parameters)
                        my_cursor.execute(
                            f'INSERT INTO weather({columns}) VALUES ({placeholders})',
                            (
                                user_city,
                                data["weather"][0]["description"],
                                data["main"]["temp"],
                                data["wind"]["speed"]
                            )
                        )
                        connection.commit()
                        print(f"✅ Данные для города {user_city.title()} успешно сохранены в Базу Данных!")
                    except requests.exceptions.HTTPError:
                        print('❌ Город НЕ найден, попробуйте снова!')
                    user_city = input('\nВведите название города ИЛИ "exit" для выхода: ').lower()
    except Exception as error:
        print(f"Что-то пошло не так: {error}")

if __name__ == '__main__':
    main()