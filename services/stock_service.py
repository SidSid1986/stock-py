# services/stock_service.py
import time
import pandas as pd
import akshare as ak
from sqlalchemy.orm import Session
from models import StockBasic, StockHistory, StockFinancial


def sync_stock_basic(db: Session):
    """
    使用 AKShare 获取 A 股基础代码与名称列表，并同步到 stock_basic 表中
    """
    try:
        print("正在获取 A 股基础代码列表...")
        df = ak.stock_info_a_code_name()

        if df is None or df.empty:
            return {"code": 500, "message": "未能从 akshare 获取到股票数据"}

        count_inserted = 0
        count_updated = 0

        for _, row in df.iterrows():
            symbol = str(row.get("code", "")).strip()
            name = str(row.get("name", "")).strip()

            if not symbol or not name:
                continue

            market = "sh"
            if symbol.startswith("0") or symbol.startswith("3"):
                market = "sz"
            elif symbol.startswith("8") or symbol.startswith("4") or symbol.startswith("9"):
                market = "bj"

            existing_stock = db.query(StockBasic).filter(StockBasic.symbol == symbol).first()

            if existing_stock:
                existing_stock.name = name
                existing_stock.market = market
                count_updated += 1
            else:
                new_stock = StockBasic(
                    symbol=symbol,
                    name=name,
                    market=market
                )
                db.add(new_stock)
                count_inserted += 1

        db.commit()
        return {
            "code": 200,
            "message": "A 股基础数据同步成功",
            "inserted": count_inserted,
            "updated": count_updated
        }

    except Exception as e:
        db.rollback()
        return {"code": 500, "message": f"同步失败: {str(e)}"}


def sync_stock_history_by_symbol(symbol: str, db: Session):
    """
    同步指定 A 股的历史日 K 线行情数据（使用新浪源 ak.stock_zh_a_daily）
    """
    df = None
    max_retries = 3

    market_prefix = "sh" if symbol.startswith("6") else ("bj" if symbol.startswith(("8", "4", "9")) else "sz")
    full_symbol = f"{market_prefix}{symbol}"

    for attempt in range(max_retries):
        try:
            print(f"正在获取 A 股代码: {full_symbol} 的历史行情数据（第 {attempt + 1} 次）...")
            df = ak.stock_zh_a_daily(symbol=full_symbol, adjust="qfq")

            if df is not None and not df.empty:
                break
        except Exception as e:
            print(f"获取历史行情失败: {str(e)}")
            if attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 3
                print(f"触发限制，等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                return {
                    "code": 500,
                    "message": f"接口请求失败或被限流。错误: {str(e)}"
                }

    if df is None or df.empty:
        return {"code": 404, "message": f"未找到股票 {symbol} 的历史行情数据"}

    try:
        count_inserted = 0

        for _, row in df.iterrows():
            trade_date_str = str(row.get("date", row.get("日期", ""))).strip()
            if not trade_date_str:
                continue

            trade_date = pd.to_datetime(trade_date_str).date()

            existing = db.query(StockHistory).filter(
                StockHistory.symbol == symbol,
                StockHistory.trade_date == trade_date
            ).first()

            if not existing:
                history_item = StockHistory(
                    symbol=symbol,
                    trade_date=trade_date,
                    open=float(row.get("open", row.get("开盘", 0))),
                    high=float(row.get("high", row.get("最高", 0))),
                    low=float(row.get("low", row.get("最低", 0))),
                    close=float(row.get("close", row.get("收盘", 0))),
                    volume=float(row.get("volume", row.get("成交量", 0))),
                    amount=float(row.get("amount", row.get("成交额", 0))),
                    turnover_rate=float(row.get("turnover", row.get("换手率", 0))) if pd.notna(
                        row.get("turnover", row.get("换手率", None))) else None
                )
                db.add(history_item)
                count_inserted += 1

        db.commit()
        return {
            "code": 200,
            "message": f"股票 {symbol} 历史行情同步成功",
            "inserted_count": count_inserted
        }

    except Exception as e:
        db.rollback()
        return {"code": 500, "message": f"数据库写入失败: {str(e)}"}


def get_stock_list_service(db: Session, page: int = 1, size: int = 20, keyword: str = None, market: str = None):
    """
    分页获取股票列表，支持按代码、名称关键字、市场（sh/sz/bj）进行多条件筛选
    """
    query = db.query(StockBasic)

    if market:
        query = query.filter(StockBasic.market == market)

    if keyword:
        search_filter = f"%{keyword}%"
        query = query.filter(
            (StockBasic.symbol.like(search_filter)) |
            (StockBasic.name.like(search_filter))
        )

    total = query.count()
    offset = (page - 1) * size
    stocks = query.offset(offset).limit(size).all()

    return {
        "code": 200,
        "total": total,
        "page": page,
        "size": size,
        "data": stocks
    }


def sync_stock_financial_by_symbol(symbol: str, db: Session):
    """
    同步指定 A 股的财务核心指标数据
    """
    try:
        print(f"正在获取 A 股代码: {symbol} 的财务指标数据...")
        df = ak.stock_financial_analysis_indicator(symbol=symbol)

        if df is None or df.empty:
            return {"code": 404, "message": f"未找到股票 {symbol} 的财务数据"}

        count_inserted = 0

        for _, row in df.iterrows():
            report_date_str = str(row.get("日期", row.get("报告期", ""))).strip()
            if not report_date_str:
                continue

            report_date = pd.to_datetime(report_date_str).date()

            existing = db.query(StockFinancial).filter(
                StockFinancial.symbol == symbol,
                StockFinancial.report_date == report_date
            ).first()

            if not existing:
                financial_item = StockFinancial(
                    symbol=symbol,
                    report_date=report_date,
                    roe=float(row.get("净资产收益率", 0)) if pd.notna(row.get("净资产收益率")) else None,
                    net_profit_growth=float(row.get("净利润同比增长率", 0)) if pd.notna(
                        row.get("净利润同比增长率")) else None,
                    gross_profit_margin=float(row.get("销售毛利率", 0)) if pd.notna(row.get("销售毛利率")) else None,
                    debt_to_asset_ratio=float(row.get("资产负债率", 0)) if pd.notna(row.get("资产负债率")) else None
                )
                db.add(financial_item)
                count_inserted += 1

        db.commit()
        return {
            "code": 200,
            "message": f"股票 {symbol} 财务数据同步成功",
            "inserted_count": count_inserted
        }

    except Exception as e:
        db.rollback()
        return {"code": 500, "message": f"财务数据同步失败: {str(e)}"}


def screen_and_analyze_stocks(db: Session, min_roe: float = 12.0, max_debt: float = 65.0):
    """
    多因子选股与买卖点策略引擎：
    筛选出基本面健康（高 ROE、低负债）的股票，并结合最新 K 线评估当前技术面与买入区间。
    """
    try:
        # 1. 查询所有基础股票
        stocks = db.query(StockBasic).all()
        selected_results = []

        for stock in stocks:
            # 获取该股票最新的一期财务数据
            latest_financial = db.query(StockFinancial).filter(
                StockFinancial.symbol == stock.symbol
            ).order_by(StockFinancial.report_date.desc()).first()

            if not latest_financial:
                continue

            roe = latest_financial.roe or 0
            debt = latest_financial.debt_to_asset_ratio or 0

            # 基本面硬性条件过滤（例如 ROE >= 设定值，且资产负债率在安全范围内）
            if roe >= min_roe and debt <= max_debt:

                # 获取该股票最近一天的行情数据来评估价格
                latest_history = db.query(StockHistory).filter(
                    StockHistory.symbol == stock.symbol
                ).order_by(StockHistory.trade_date.desc()).first()

                if not latest_history:
                    continue

                current_close = latest_history.close

                # 简单的均值回归/安全边际估算逻辑（可后续升级为更复杂的 MA/布林带策略）
                # 这里以近期收盘价为基准，模拟计算一个合理的“低吸买入区间”与“目标止盈位”
                suggested_buy_low = round(current_close * 0.92, 2)  # 回调 8% 视为安全买入价
                suggested_buy_high = round(current_close * 0.96, 2)  # 分批建仓上限
                target_sell = round(current_close * 1.15, 2)  # 预期止盈目标涨幅 15%

                selected_results.append({
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "market": stock.market,
                    "latest_roe": roe,
                    "debt_ratio": debt,
                    "current_price": current_close,
                    "strategy_signal": "逢低关注 / 优质标的",
                    "buy_zone": f"{suggested_buy_low} - {suggested_buy_high}",
                    "target_price": target_sell
                })

        return {
            "code": 200,
            "message": "策略筛选与买卖点计算成功",
            "count": len(selected_results),
            "data": selected_results[:50]  # 默认返回前 50 条优质标的供参考
        }

    except Exception as e:
        return {"code": 500, "message": f"策略执行失败: {str(e)}"}