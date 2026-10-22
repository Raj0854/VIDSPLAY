import mimetypes
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import inspect, text


def upgrade_legacy_sqlite_schema(engine):
    if engine.dialect.name != "sqlite":
        return

    tables = set(inspect(engine).get_table_names())
    if not tables:
        return

    with engine.begin() as connection:
        _add_columns(connection, tables, "admin_users", {
            "email": "VARCHAR(120)",
            "role": "VARCHAR(20) NOT NULL DEFAULT 'admin'",
            "is_active_account": "BOOLEAN NOT NULL DEFAULT 1",
            "last_login": "DATETIME",
            "updated_at": "DATETIME",
        })
        if "admin_users" in tables:
            columns = _column_names(inspect(engine), "admin_users")
            if "email" in columns:
                connection.execute(text(
                    "UPDATE admin_users SET email = username || '@vidsplay.local' "
                    "WHERE email IS NULL OR email = ''"
                ))
                connection.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_admin_users_email_compat "
                    "ON admin_users (email)"
                ))
            if "created_at" in columns:
                connection.execute(text(
                    "UPDATE admin_users SET updated_at = created_at WHERE updated_at IS NULL"
                ))

        _add_columns(connection, tables, "categories", {
            "name": "VARCHAR(100)",
            "icon": "VARCHAR(80) NOT NULL DEFAULT 'bi-folder'",
            "display_order": "INTEGER NOT NULL DEFAULT 0",
            "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        })
        if "categories" in tables:
            columns = _column_names(inspect(engine), "categories")
            if "title" in columns:
                connection.execute(text(
                    "UPDATE categories SET name = title WHERE name IS NULL OR name = ''"
                ))
            if "order_index" in columns:
                connection.execute(text(
                    "UPDATE categories SET display_order = order_index "
                    "WHERE display_order = 0"
                ))
            if "is_visible" in columns:
                connection.execute(text(
                    "UPDATE categories SET is_active = is_visible "
                    "WHERE is_active = 1"
                ))

        _add_columns(connection, tables, "videos", {
            "source_url": "VARCHAR(500)",
            "storage_key": "VARCHAR(500)",
            "embed_code": "TEXT",
            "thumbnail_url": "VARCHAR(500)",
            "views_count": "INTEGER NOT NULL DEFAULT 0",
            "is_published": "BOOLEAN NOT NULL DEFAULT 1",
            "is_featured": "BOOLEAN NOT NULL DEFAULT 0",
            "duration": "VARCHAR(50)",
            "file_size": "BIGINT",
        })
        if "videos" in tables:
            columns = _column_names(inspect(engine), "videos")
            if "original_url" in columns:
                connection.execute(text(
                    "UPDATE videos SET source_url = original_url "
                    "WHERE source_url IS NULL OR source_url = ''"
                ))
            if "thumbnail" in columns:
                connection.execute(text(
                    "UPDATE videos SET thumbnail_url = thumbnail "
                    "WHERE thumbnail_url IS NULL OR thumbnail_url = ''"
                ))
            if "status" in columns:
                connection.execute(text(
                    "UPDATE videos SET is_published = CASE WHEN status = 'published' "
                    "THEN 1 ELSE 0 END"
                ))
            if {"original_url", "playback_url", "source_type"} <= columns:
                rows = connection.execute(text(
                    "SELECT id, original_url, playback_url, source_type, embed_code "
                    "FROM videos WHERE source_type = 'youtube'"
                )).mappings()
                for row in rows:
                    video_id = row["id"]
                    embed_code = row["embed_code"] or _youtube_id(
                        row["playback_url"] or row["original_url"]
                    )
                    if embed_code:
                        connection.execute(
                            text("UPDATE videos SET embed_code = :embed_code WHERE id = :id"),
                            {"embed_code": embed_code, "id": video_id},
                        )

        _add_columns(connection, tables, "navigation_items", {
            "target_type": "VARCHAR(20) NOT NULL DEFAULT 'category'",
            "target_url": "VARCHAR(255)",
            "page_id": "INTEGER",
            "parent_id": "INTEGER",
            "icon": "VARCHAR(50)",
            "display_order": "INTEGER NOT NULL DEFAULT 0",
            "visibility": "VARCHAR(20) NOT NULL DEFAULT 'all'",
            "is_active": "BOOLEAN NOT NULL DEFAULT 1",
            "updated_at": "DATETIME",
        })
        if "navigation_items" in tables:
            columns = _column_names(inspect(engine), "navigation_items")
            if "url" in columns:
                connection.execute(text(
                    "UPDATE navigation_items SET target_url = url "
                    "WHERE target_url IS NULL OR target_url = ''"
                ))
            if "item_type" in columns:
                connection.execute(text(
                    "UPDATE navigation_items SET target_type = item_type"
                ))
            if "order_index" in columns:
                connection.execute(text(
                    "UPDATE navigation_items SET display_order = order_index"
                ))
            if "is_enabled" in columns:
                connection.execute(text(
                    "UPDATE navigation_items SET is_active = is_enabled"
                ))
            if {"is_mobile", "is_desktop"} <= columns:
                connection.execute(text(
                    "UPDATE navigation_items SET visibility = CASE "
                    "WHEN is_mobile = 1 AND is_desktop = 1 THEN 'all' "
                    "WHEN is_mobile = 1 THEN 'mobile' ELSE 'desktop' END"
                ))
            if "created_at" in columns:
                connection.execute(text(
                    "UPDATE navigation_items SET updated_at = created_at "
                    "WHERE updated_at IS NULL"
                ))

        _add_columns(connection, tables, "pages", {
            "meta_description": "VARCHAR(300)",
            "template": "VARCHAR(50) NOT NULL DEFAULT 'default'",
        })

        _add_columns(connection, tables, "media_assets", {
            "filename": "VARCHAR(255)",
            "original_name": "VARCHAR(255)",
            "mime_type": "VARCHAR(100)",
            "uploaded_at": "DATETIME",
        })
        if "media_assets" in tables:
            columns = _column_names(inspect(engine), "media_assets")
            if {"filename", "original_name", "mime_type"} <= columns:
                name_column = "name" if "name" in columns else "original_name"
                rows = connection.execute(text(
                    f"SELECT id, {name_column} AS legacy_name, file_path, filename, "
                    "original_name, mime_type FROM media_assets"
                )).mappings()
                for row in rows:
                    path = row["file_path"] or ""
                    legacy_name = row["legacy_name"] or ""
                    filename = Path(path).name or legacy_name or f"asset-{row['id']}"
                    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                    connection.execute(text(
                        "UPDATE media_assets SET filename = :filename, "
                        "original_name = :original_name, mime_type = :mime_type "
                        "WHERE id = :id"
                    ), {
                        "filename": row["filename"] or filename,
                        "original_name": row["original_name"] or legacy_name or filename,
                        "mime_type": row["mime_type"] or mime_type,
                        "id": row["id"],
                    })
            columns = _column_names(inspect(engine), "media_assets")
            if "created_at" in columns:
                connection.execute(text(
                    "UPDATE media_assets SET uploaded_at = created_at "
                    "WHERE uploaded_at IS NULL"
                ))

        _add_columns(connection, tables, "site_settings", {
            "description": "VARCHAR(255)",
            "updated_at": "DATETIME",
        })

        _add_columns(connection, tables, "activity_logs", {
            "user_id": "INTEGER",
            "ip_address": "VARCHAR(50)",
            "timestamp": "DATETIME",
        })
        if "activity_logs" in tables and "created_at" in _column_names(inspect(engine), "activity_logs"):
            connection.execute(text(
                "UPDATE activity_logs SET timestamp = created_at WHERE timestamp IS NULL"
            ))


def _add_columns(connection, tables, table_name, definitions):
    if table_name not in tables:
        return

    existing = _column_names(inspect(connection), table_name)
    for column_name, definition in definitions.items():
        if column_name not in existing:
            connection.execute(text(
                f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}'
            ))
            existing.add(column_name)


def _column_names(inspector, table_name):
    return {column["name"] for column in inspector.get_columns(table_name)}


def _youtube_id(url):
    if not url:
        return None

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if hostname in {"youtu.be", "www.youtu.be"}:
        candidate = parsed.path.strip("/").split("/")[0]
    elif hostname.endswith("youtube.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        else:
            match = re.match(r"^/(?:embed|shorts)/([^/]+)", parsed.path)
            candidate = match.group(1) if match else ""
    else:
        return None

    return candidate if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate) else None
