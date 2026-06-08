from aiohttp import web
from db import get_pool, init_db
from auth import hash_password, check_password, create_token, get_current_user_id


# ── Хелпер: asyncpg Record → dict ─────────────────────────────────────────────

def row_to_dict(row) -> dict:
    """Конвертирует строку из БД в словарь, приводя datetime к строке."""
    d = dict(row)
    if "created_at" in d and d["created_at"]:
        d["created_at"] = d["created_at"].isoformat()
    return d


# ══════════════════════════════════════════════════════════════════════════════
# АУТЕНТИФИКАЦИЯ
# ══════════════════════════════════════════════════════════════════════════════

# ── POST /register ────────────────────────────────────────────────────────────
async def register(request: web.Request) -> web.Response:
    """
    Регистрация нового пользователя.
    Принимает {email, password}, хэширует пароль через bcrypt,
    сохраняет в таблицу users, возвращает id и email.
    """
    data = await request.json()
    if not data.get("email") or not data.get("password"):
        raise web.HTTPBadRequest(text="Fields 'email' and 'password' are required")

    # Хэшируем пароль — в БД никогда не хранится открытый текст
    password_hash = hash_password(data["password"])

    async with request.app["pool"].acquire() as conn:
        # Проверяем что email ещё не занят
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE email = $1", data["email"]
        )
        if existing:
            raise web.HTTPConflict(text="User with this email already exists")

        user = await conn.fetchrow(
            "INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id, email",
            data["email"], password_hash,
        )

    return web.json_response({"id": user["id"], "email": user["email"]}, status=201)


# ── POST /login ───────────────────────────────────────────────────────────────
async def login(request: web.Request) -> web.Response:
    """
    Вход пользователя.
    Проверяет email и пароль, возвращает JWT-токен.
    Токен нужно передавать в заголовке Authorization: Bearer <token>
    для доступа к защищённым маршрутам.
    """
    data = await request.json()
    if not data.get("email") or not data.get("password"):
        raise web.HTTPBadRequest(text="Fields 'email' and 'password' are required")

    async with request.app["pool"].acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, password_hash FROM users WHERE email = $1", data["email"]
        )

    # Если пользователь не найден или пароль неверный — одинаковое сообщение
    # (не раскрываем что именно неверно)
    if not user or not check_password(data["password"], user["password_hash"]):
        raise web.HTTPUnauthorized(text="Invalid email or password")

    token = create_token(user["id"])
    return web.json_response({"token": token})


# ══════════════════════════════════════════════════════════════════════════════
# ОБЪЯВЛЕНИЯ (защищённые маршруты)
# ══════════════════════════════════════════════════════════════════════════════

# ── GET /ads/{id} ─────────────────────────────────────────────────────────────
async def get_ad(request: web.Request) -> web.Response:
    """
    Получить объявление по id.
    Публичный маршрут — авторизация не требуется.
    """
    ad_id = int(request.match_info["id"])
    async with request.app["pool"].acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT a.id, a.title, a.description, a.created_at, u.email AS owner
            FROM advertisement a
            JOIN users u ON u.id = a.owner_id
            WHERE a.id = $1
            """,
            ad_id,
        )
    if not row:
        raise web.HTTPNotFound(text="Advertisement not found")
    return web.json_response(row_to_dict(row))


# ── POST /ads ─────────────────────────────────────────────────────────────────
async def create_ad(request: web.Request) -> web.Response:
    """
    Создать объявление.
    Требует JWT. owner_id берётся из токена — клиент не может
    указать чужого владельца.
    """
    user_id = get_current_user_id(request)  # 401 если нет токена

    data = await request.json()
    if not data.get("title") or not data.get("description"):
        raise web.HTTPBadRequest(text="Fields 'title' and 'description' are required")

    async with request.app["pool"].acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO advertisement (title, description, owner_id)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            data["title"], data["description"], user_id,
        )
    return web.json_response(row_to_dict(row), status=201)


# ── PATCH /ads/{id} ───────────────────────────────────────────────────────────
async def update_ad(request: web.Request) -> web.Response:
    """
    Обновить объявление.
    Требует JWT. Редактировать может только владелец объявления.
    """
    user_id = get_current_user_id(request)
    ad_id   = int(request.match_info["id"])

    async with request.app["pool"].acquire() as conn:
        # Проверяем существование и владельца
        ad = await conn.fetchrow(
            "SELECT owner_id FROM advertisement WHERE id = $1", ad_id
        )
        if not ad:
            raise web.HTTPNotFound(text="Advertisement not found")
        if ad["owner_id"] != user_id:
            raise web.HTTPForbidden(text="You are not the owner of this advertisement")

        data   = await request.json()
        fields = {k: v for k, v in data.items() if k in ("title", "description")}
        if not fields:
            raise web.HTTPBadRequest(text="No valid fields to update")

        set_clause = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
        row = await conn.fetchrow(
            f"UPDATE advertisement SET {set_clause} WHERE id = $1 RETURNING *",
            ad_id, *fields.values(),
        )

    return web.json_response(row_to_dict(row))


# ── DELETE /ads/{id} ──────────────────────────────────────────────────────────
async def delete_ad(request: web.Request) -> web.Response:
    """
    Удалить объявление.
    Требует JWT. Удалить может только владелец объявления.
    """
    user_id = get_current_user_id(request)
    ad_id   = int(request.match_info["id"])

    async with request.app["pool"].acquire() as conn:
        # Проверяем существование и владельца
        ad = await conn.fetchrow(
            "SELECT owner_id FROM advertisement WHERE id = $1", ad_id
        )
        if not ad:
            raise web.HTTPNotFound(text="Advertisement not found")
        if ad["owner_id"] != user_id:
            raise web.HTTPForbidden(text="You are not the owner of this advertisement")

        await conn.execute("DELETE FROM advertisement WHERE id = $1", ad_id)

    return web.json_response({"deleted": ad_id})


# ══════════════════════════════════════════════════════════════════════════════
# ЖИЗНЕННЫЙ ЦИКЛ И РОУТИНГ
# ══════════════════════════════════════════════════════════════════════════════

async def on_startup(app: web.Application) -> None:
    """При старте создаём пул соединений и инициализируем таблицы."""
    app["pool"] = await get_pool()
    await init_db(app["pool"])


async def on_cleanup(app: web.Application) -> None:
    """При остановке закрываем пул соединений."""
    await app["pool"].close()


app = web.Application()

# Маршруты аутентификации (публичные)
app.router.add_post("/register", register)
app.router.add_post("/login",    login)

# Маршруты объявлений (GET публичный, остальные защищены JWT)
app.router.add_get   ("/ads/{id}", get_ad)
app.router.add_post  ("/ads",      create_ad)
app.router.add_patch ("/ads/{id}", update_ad)
app.router.add_delete("/ads/{id}", delete_ad)

app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)