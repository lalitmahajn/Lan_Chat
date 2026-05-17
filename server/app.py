"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.database import create_tables, shutdown_db
from server.routes import auth_routes, chat_routes, file_routes, admin_routes, user_routes

logger = logging.getLogger("lan_chat")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting LAN Chat Server...")
    await create_tables()
    logger.info("Database tables ready.")
    
    from server.database import get_session_factory
    from server.config import server_config
    import secrets
    
    factory = get_session_factory()
    async with factory() as db:
        await server_config.load_from_db(db)
        if not server_config.jwt_secret:
            secret = secrets.token_hex(32)
            await server_config.save_to_db(db, {"jwt_secret": secret})
    
    # mDNS registration
    from client.discovery import register_service, unregister_service
    mdns = register_service(server_config.server_port, server_config.server_name)
    
    yield
    
    logger.info("Shutting down...")
    if mdns:
        unregister_service(mdns)
    await shutdown_db()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="LAN Chat Server",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — allow all for LAN
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    app.include_router(auth_routes.router)
    app.include_router(chat_routes.router)
    app.include_router(file_routes.router)
    app.include_router(admin_routes.router)
    app.include_router(user_routes.router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app
