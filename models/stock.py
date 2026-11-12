# models/stock.py
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint, func
from database import Base


class StockBasic(Base):
    __tablename__ = "stock_basic"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增ID")
    symbol = Column(String(20), unique=True, index=True, nullable=False, comment="股票代码")
    name = Column(String(50), nullable=False, comment="股票名称")
    market = Column(String(10), comment="市场板块：sh/sz/bj")
    industry = Column(String(50), comment="所属行业")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")


class StockHistory(Base):
    __tablename__ = "stock_history"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增ID")
    symbol = Column(String(20), index=True, nullable=False, comment="股票代码")
    trade_date = Column(Date, index=True, nullable=False, comment="交易日期")
    open = Column(Float, comment="开盘价")
    high = Column(Float, comment="最高价")
    low = Column(Float, comment="最低价")
    close = Column(Float, comment="收盘价")
    volume = Column(Float, comment="成交量")
    amount = Column(Float, comment="成交额")
    turnover_rate = Column(Float, comment="换手率")

    __table_args__ = (
        UniqueConstraint('symbol', 'trade_date', name='uix_symbol_date'),
    )


class StockFinancial(Base):
    __tablename__ = "stock_financial"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增ID")
    symbol = Column(String(20), index=True, nullable=False, comment="股票代码")
    report_date = Column(Date, index=True, nullable=False, comment="报告期（如 2023-12-31）")

    # 核心财务指标字段
    roe = Column(Float, comment="净资产收益率(ROE)")
    net_profit_growth = Column(Float, comment="净利润同比增长率")
    gross_profit_margin = Column(Float, comment="销售毛利率")
    debt_to_asset_ratio = Column(Float, comment="资产负债率")

    __table_args__ = (
        UniqueConstraint('symbol', 'report_date', name='uix_symbol_report_date'),
    )


class StockStrategyBacktest(Base):
    __tablename__ = "stock_strategy_backtest"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="自增ID")
    strategy_name = Column(String(100), nullable=False, comment="策略名称")
    symbol = Column(String(20), index=True, nullable=False, comment="股票代码")
    total_return = Column(Float, comment="总收益率")
    max_drawdown = Column(Float, comment="最大回撤")
    win_rate = Column(Float, comment="胜率")
    run_date = Column(DateTime, default=func.now(), comment="回测运行时间")