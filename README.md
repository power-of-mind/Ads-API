# Ads API

Асинхронный REST API сайта объявлений на **aiohttp** + **PostgreSQL** (asyncpg).

## Стек

- Python 3.12
- aiohttp 3.9.5
- asyncpg 0.29.0
- PostgreSQL 16
- Docker + Docker Compose

## Структура проекта

```
ads_api/
├── app.py               # хендлеры (GET, POST, PATCH, DELETE)
├── db.py                # пул соединений asyncpg + создание таблицы
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Запуск через Docker (рекомендуется)

```bash
git clone https://github.com/ВАШ_НИК/ads_api.git
cd ads_api
docker-compose up --build
```

API будет доступен на `http://localhost:8080`.

## Запуск без Docker

```bash
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # вписать свой DATABASE_URL
python app.py
```

## Эндпоинты

| Метод  | URL          | Описание                            |
|--------|--------------|-------------------------------------|
| POST   | /ads         | Создать объявление                  |
| GET    | /ads/{id}    | Получить объявление по id           |
| PATCH  | /ads/{id}    | Обновить поля объявления            |
| DELETE | /ads/{id}    | Удалить объявление                  |

## Поля объявления

| Поле        | Тип       | Описание                    |
|-------------|-----------|-----------------------------|
| id          | integer   | Автоинкремент (PK)          |
| title       | string    | Заголовок (макс. 200 симв.) |
| description | text      | Описание                    |
| created_at  | timestamp | Дата создания (авто)        |
| owner       | string    | Владелец (макс. 100 симв.)  |

## Примеры запросов

### Создать объявление
```bash
curl -X POST http://localhost:8080/ads \
  -H "Content-Type: application/json" \
  -d '{"title": "Продам ноутбук", "description": "MacBook Pro 2023", "owner": "ivan@mail.com"}'
```

### Получить объявление
```bash
curl http://localhost:8080/ads/1
```

### Обновить объявление
```bash
curl -X PATCH http://localhost:8080/ads/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Продам ноутбук СРОЧНО"}'
```

### Удалить объявление
```bash
curl -X DELETE http://localhost:8080/ads/1
```