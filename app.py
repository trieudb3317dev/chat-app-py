
import uvicorn
# FastAPI application factory/wiring
from fastapi import FastAPI
from middleware.request_logger import RequestLoggerMiddleware

# Import routers from controllers
from controllers.root import router as root_router
from controllers.user import router as user_router
from controllers.admin import router as admin_router

app = FastAPI()

# include routers
app.include_router(root_router)
app.include_router(user_router)
app.include_router(admin_router)

# install middleware
app.add_middleware(RequestLoggerMiddleware)


if __name__ == "__main__":
    # run with reload enabled when started directly
    print("Starting server with reload enabled...")
    # pass the application as an import string so uvicorn's reloader works correctly
    print("Running uvicorn... http://localhost:8000")
    uvicorn.run("app:app", host="localhost", port=8000, reload=True)