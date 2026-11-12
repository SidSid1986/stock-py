from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from models import StockBasic, StockHistory, StockFinancial, StockStrategyBacktest
from routers import stock_router

GLOBAL_PREFIX = "/api"

app = FastAPI(
    title="A股量化与高级分析系统后端",
    version="1.0.0",
    description="为 Electron 桌面端提供的高性能 A 股数据分析与回测接口",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# 启动时自动在 stock_admin 中创建表
Base.metadata.create_all(bind=engine)

# 注册带后缀的股票路由
app.include_router(stock_router.router, prefix=GLOBAL_PREFIX)

@app.get("/", summary="后端根目录")
def root():
    return {
        "code": 200,
        "message": "A股分析系统后端服务运行正常",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app="main:app", host="127.0.0.1", port=8000, reload=True)