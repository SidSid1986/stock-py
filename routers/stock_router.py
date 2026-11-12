# routers/stock_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services import stock_service
from models import StockHistory, StockFinancial

router = APIRouter(prefix="/stock", tags=["股票分析模块"])


@router.get("/sync-basic", summary="同步 A 股基础股票列表")
def sync_basic_stocks(db: Session = Depends(get_db)):
    """通过 AKShare 抓取全市场股票并写入 MySQL"""
    return stock_service.sync_stock_basic(db)


@router.get("/list", summary="分页获取与筛选股票列表（供前端表格使用）")
def get_stocks(
    page: int = 1,
    size: int = 20,
    keyword: str = None,
    market: str = None,
    db: Session = Depends(get_db)
):
    """支持按关键字（名称/代码）、市场（sh/sz/bj）进行分页筛选"""
    return stock_service.get_stock_list_service(db, page=page, size=size, keyword=keyword, market=market)


@router.post("/sync/history/{symbol}", summary="同步指定股票的历史 K 线行情")
def trigger_sync_stock_history(symbol: str, db: Session = Depends(get_db)):
    """抓取某只股票的完整历史日K线并入库"""
    return stock_service.sync_stock_history_by_symbol(symbol, db)


@router.get("/history/{symbol}", summary="从数据库获取某只股票的历史行情")
def get_stock_history(symbol: str, db: Session = Depends(get_db)):
    """按时间正序返回指定股票的历史行情"""
    history_list = db.query(StockHistory) \
        .filter(StockHistory.symbol == symbol) \
        .order_by(StockHistory.trade_date.asc()) \
        .all()

    return {
        "code": 200,
        "message": "success",
        "count": len(history_list),
        "data": history_list
    }


@router.post("/sync/financial/{symbol}", summary="同步指定股票的财务指标数据")
def trigger_sync_stock_financial(symbol: str, db: Session = Depends(get_db)):
    """抓取某只股票的历年财务报表核心指标并入库"""
    return stock_service.sync_stock_financial_by_symbol(symbol, db)


@router.get("/financial/{symbol}", summary="获取某只股票的财务指标历史")
def get_stock_financials(symbol: str, db: Session = Depends(get_db)):
    """查询指定股票的多期财报分析数据"""
    financial_list = db.query(StockFinancial) \
        .filter(StockFinancial.symbol == symbol) \
        .order_by(StockFinancial.report_date.desc()) \
        .all()

    return {
        "code": 200,
        "message": "success",
        "count": len(financial_list),
        "data": financial_list
    }

@router.get("/strategy/screen", summary="执行多因子量化选股与买卖点提醒策略")
def run_stock_strategy(
    min_roe: float = 12.0,
    max_debt: float = 65.0,
    db: Session = Depends(get_db)
):
    """
    根据基本面（ROE、负债率）和技术面价格，自动筛选优质标的并输出建议买入区间与目标价
    """
    return stock_service.screen_and_analyze_stocks(db, min_roe=min_roe, max_debt=max_debt)