from fastapi import FastAPI, Form, File, UploadFile, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 数据库
from database import engine, Base

GLOBAL_PREFIX = "/api"

app = FastAPI(
    title="首页图片与服务接口",
    version="1.0",
    max_request_size=500 * 1024 * 1024
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://www.ytfreeie.com",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 建表
Base.metadata.create_all(bind=engine)


@app.get("/", summary="首页")
def root():
    return {
        "code": 200,
        "message": "服务运行正常",
        "document": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
