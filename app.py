from aiohttp import web
from db import get_pool, init_db


def row_to_dict(row) -> dict:
    d = dict(row)
    d["created_at"] = d["created_at"].isoformat()
    return d


# ── GET /ads/{id} ─────────────────────────────────────────────────────────────
async def get_ad(request: web.Request) -> web.Response:
    ad_id = int(request.match_info["id"])
    async with request.app["pool"].acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM advertisement WHERE id = $1", ad_id
        )
    if not row:
        raise web.HTTPNotFound(text="Advertisement not found")
    return web.json_response(row_to_dict(row))


# ── POST /ads ─────────────────────────────────────────────────────────────────
async def create_ad(request: web.Request) -> web.Response:
    data = await request.json()
    required = ("title", "description", "owner")
    missing  = [f for f in required if f not in data]
    if missing:
        raise web.HTTPBadRequest(text=f"Missing fields: {', '.join(missing)}")

    async with request.app["pool"].acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO advertisement (title, description, owner)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            data["title"], data["description"], data["owner"],
        )
    return web.json_response(row_to_dict(row), status=201)


# ── PATCH /ads/{id} ───────────────────────────────────────────────────────────
async def update_ad(request: web.Request) -> web.Response:
    ad_id  = int(request.match_info["id"])
    data   = await request.json()
    fields = {k: v for k, v in data.items() if k in ("title", "description", "owner")}

    if not fields:
        raise web.HTTPBadRequest(text="No valid fields to update")

    set_clause = ", ".join(f"{k} = ${i + 2}" for i, k in enumerate(fields))
    values     = list(fields.values())

    async with request.app["pool"].acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE advertisement SET {set_clause} WHERE id = $1 RETURNING *",
            ad_id, *values,
        )
    if not row:
        raise web.HTTPNotFound(text="Advertisement not found")
    return web.json_response(row_to_dict(row))


# ── DELETE /ads/{id} ──────────────────────────────────────────────────────────
async def delete_ad(request: web.Request) -> web.Response:
    ad_id = int(request.match_info["id"])
    async with request.app["pool"].acquire() as conn:
        result = await conn.execute(
            "DELETE FROM advertisement WHERE id = $1", ad_id
        )
    if result == "DELETE 0":
        raise web.HTTPNotFound(text="Advertisement not found")
    return web.json_response({"deleted": ad_id})


# ── Жизненный цикл ────────────────────────────────────────────────────────────
async def on_startup(app: web.Application) -> None:
    app["pool"] = await get_pool()
    await init_db(app["pool"])


async def on_cleanup(app: web.Application) -> None:
    await app["pool"].close()


# ── Роутинг ───────────────────────────────────────────────────────────────────
app = web.Application()
app.router.add_get   ("/ads/{id}", get_ad)
app.router.add_post  ("/ads",      create_ad)
app.router.add_patch ("/ads/{id}", update_ad)
app.router.add_delete("/ads/{id}", delete_ad)
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8080)
