import uvicorn

# FastAPI application factory/wiring
from fastapi import FastAPI
from middleware.request_logger import RequestLoggerMiddleware

# Import routers from controllers
from controllers.root import router as root_router
from controllers.user import router as user_router
from controllers.admin import router as admin_router
from controllers.friend import router as friend_router
from controllers.chat import router as chat_router
from controllers.ws import router as ws_router
from scripts.auto_migrate import autogenerate_and_upgrade, should_auto_migrate

app = FastAPI()

# include routers
app.include_router(friend_router)
app.include_router(root_router)
app.include_router(user_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(ws_router)

# install middleware
app.add_middleware(RequestLoggerMiddleware)

# CORS can be added here if needed, e.g.:
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _maybe_auto_migrate():
    # Run automatic autogenerate+upgrade only in development when explicitly enabled.
    try:
        if should_auto_migrate():
            print("AUTO_MIGRATE enabled — running autogenerate+upgrade...")
            autogenerate_and_upgrade()
    except Exception as e:
        # Do not crash the app on migration errors; surface the message in logs.
        print("auto-migrate failed:", e)


if __name__ == "__main__":
    # run with reload enabled when started directly
    print("Starting server with reload enabled...")
    # pass the application as an import string so uvicorn's reloader works correctly
    print("Running uvicorn... http://localhost:8000")
    uvicorn.run("app:app", host="localhost", port=8000, reload=True)
