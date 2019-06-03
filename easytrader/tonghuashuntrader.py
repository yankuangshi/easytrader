# -*- coding: utf-8 -*-
import json
import os
import re

import requests

from . import exceptions, helpers, webtrader
from .log import log


class TongHuaShunTrader(webtrader.WebTrader):
    config_path = os.path.dirname(__file__) + "/config/tonghuashun.json"

    _HEADERS = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,fr;q=0.6",
        "Accept-Encoding": "gzip, deflate",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Host": "mncg.10jqka.com.cn",
        "Origin": "http://mncg.10jqka.com.cn",
        "Pragma": "no-cache",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36",
        "Referer": "http://mncg.10jqka.com.cn/cgiwt/index/index",
        "X-Requested-With": "XMLHttpRequest"
    }

    # HTTP RESPONSE
    _HTTP_RESPONSE_OK = 0

    # Position grid
    _POSITION_GRID_STOCK_CODE = "d_2102"  # 证券代码
    _POSITION_GRID_STOCK_NAME = "d_2103"  # 证券名称
    _POSITION_GRID_HOLD_SHARES = "d_2117"  # 证券数量
    _POSITION_GRID_SELLABLE_SHARES = "d_2121"  # 可卖数量
    _POSITION_GRID_FROZEN_SHARES = "d_2118"  # 冻结数量
    _POSITION_GRID_COST_PRICE = "d_2122"  # 成本价
    _POSITION_GRID_MARKET_PRICE = "d_2124"  # 当前价
    _POSITION_GRID_MARKET_VALUE = "d_2125"  # 最新市值
    _POSITION_GRID_FLOAT_PNL = "d_2147"  # 浮动盈亏
    _POSITION_GRID_PNL_PCT = "d_3616"  # 盈亏比例（%）

    # Today entrusts grid
    _TODAY_ENTRUSTS_GRID_STOCK_CODE = "d_2102"  # 证券代码
    _TODAY_ENTRUSTS_GRID_STOCK_NAME = "d_2103"  # 证券名称
    _TODAY_ENTRUSTS_GRID_STATUS = "d_2105"  # 委托状态
    _TODAY_ENTRUSTS_GRID_SHARES = "d_2126"  # 委托股数
    _TODAY_ENTRUSTS_GRID_TX_SHARES = "d_2128"  # 成交股数
    _TODAY_ENTRUSTS_GRID_PRICE = "d_2127"  # 委托价格
    _TODAY_ENTRUSTS_GRID_TX_PRICE = "d_2129"  # 成交均价
    _TODAY_ENTRUSTS_GRID_DIRECTION = "d_2109"  # 委托方向
    _TODAY_ENTRUSTS_GRID_TIME = "d_2140"  # 委托时间
    _TODAY_ENTRUSTS_GRID_DATE = "d_2139"  # 委托日期
    _TODAY_ENTRUSTS_GRID_CONTRACT_NO = "d_2135"  # 合同编号
    _TODAY_ENTRUSTS_GRID_MODE = "d_3680"  # 委托方式（限价或市价）

    # Today trades grid
    _TODAY_TRADES_GRID_STOCK_CODE = "d_2102"  # 证券代码
    _TODAY_TRADES_GRID_STOCK_NAME = "d_2103"  # 证券名称
    _TODAY_TRADES_GRID_DIRECTION = "d_2109"  # 操作方向
    _TODAY_TRADES_GRID_TX_SHARES = "d_2128"  # 成交数量
    _TODAY_TRADES_GRID_TX_PRICE = "d_2129"  # 成交均价
    _TODAY_TRADES_GRID_TX_AMOUNT = "d_2131"  # 成交金额
    _TODAY_TRADES_GRID_CONTRACT_NO = "d_2135"  # 委托单合同编号
    _TODAY_TRADES_GRID_TX_NO = "d_2130"  # 成交单合同编号
    _TODAY_TRADES_GRID_DATE = "d_2141"  # 成交日期

    # Trading param
    _TRADING_TYPE_BUY = "cmd_wt_mairu"  # 委托买入
    _TRADING_TYPE_SELL = "cmd_wt_maichu"  # 委托卖出
    _TRADING_PRICE_MKT = "market"  # market order
    _TRADING_PRICE_LMT = "limit"  # limit order

    _TRADING_ORDER_TYPE_OPPOSITE_SIDE_BEST = "11"   # 深圳交易所对方最优价格
    _TRADING_ORDER_TYPE_SAME_SIDE_BEST = "12"       # 深圳交易所本方最优价格
    _TRADING_ORDER_TYPE_IMMEDIATE_OR_CANCEL = "13"  # 深圳交易所即时成交剩余撤销
    _TRADING_ORDER_TYPE_FIVE_BEST_IMMEDIATE_OR_CANCEL_SZ = "14"     # 深圳最优五档即时成交剩撤
    _TRADING_ORDER_TYPE_FILL_OR_KILL = "15"                         # 深圳全额成交或撤销
    _TRADING_ORDER_TYPE_FIVE_BEST_IMMEDIATE_OR_CANCEL_SH = "21"     # 上海最优五档即时成交剩撤
    _TRADING_ORDER_TYPE_FIVE_BEST_IMMEDIATE_TO_LIMIT = "22"         # 上海五档即成转限价

    def __init__(self, **kwargs):
        super(TongHuaShunTrader, self).__init__()

        self.s = requests.Session()
        self.s.verify = False
        self.s.headers.update(self._HEADERS)
        self.account_config = None

    def autologin(self, **kwargs):
        """
        使用cookies之后不需要自动登录
        :return:
        """
        self._set_cookies(self.account_config["cookies"])

    def _set_cookies(self, cookies):
        cookies_dict = helpers.parse_cookies_str(cookies)
        self.s.cookies.update(cookies_dict)

    def _prepare_account(self, user, password, **kwargs):
        if "sz_gdzh" not in kwargs:
            raise TypeError("同花顺模拟炒股需要设置 sz_gdzh(深市股东账户) 参数")
        if "sh_gdzh" not in kwargs:
            raise TypeError("同花顺模拟炒股需要设置 sh_gdzh(沪市股东账户) 参数")
        if "cookies" not in kwargs:
            raise TypeError("同花顺模拟炒股登录需要设置 cookies 参数")
        self.account_config = {
            "cookies": kwargs["cookies"],
            "sz_gdzh": kwargs["sz_gdzh"],
            "sh_gdzh": kwargs["sh_gdzh"]
        }

    def get_balance(self):
        """
        获取资金账户
        :return:
        """
        url = self.config['balance_url']
        r = self._get(url)
        total_assets = re.search(r'<td id="zzc">(.*?)</td>', r).group(1)  # 总资产
        market_value = re.search(r'<td id="gpsz">(.*?)</td>', r).group(1)  # 总市值
        retrievable_balance = re.search(r'<td id="kqje">(.*?)</td>', r).group(1)  # 可取金额
        current_balance = re.search(r'<td id="zjye">(.*?)</td>', r).group(1)  # 资金余额
        available_balance = re.search(r'<td id="kyye">(.*?)</td>', r).group(1)  # 可用金额
        frozen_balance = re.search(r'<td id="djje">(.*?)</td>', r).group(1)  # 冻结金额
        return {
            "total_assets": float(total_assets),
            "market_value": float(market_value),
            "retrievable_balance": float(retrievable_balance),
            "current_balance": float(current_balance),
            "available_balance": float(available_balance),
            "frozen_balance": float(frozen_balance)
        }

    def get_position(self):
        """
        获取当前持仓
        :return:
        """
        url = self.config['position_url']
        payload = {'gdzh': self.account_config['sh_gdzh'], 'mkcode': '2'}
        r = self._post(url, payload)
        resp_json = json.loads(r)
        ths_positions = resp_json["result"]["list"]
        position_list = []
        for pos in ths_positions:
            position_list.append(
                {
                    "stock_code": pos[self._POSITION_GRID_STOCK_CODE],
                    "stock_name": pos[self._POSITION_GRID_STOCK_NAME],
                    "hold_shares": int(pos[self._POSITION_GRID_HOLD_SHARES]),
                    "sellable_shares": int(pos[self._POSITION_GRID_SELLABLE_SHARES]),
                    "frozen_shares": int(pos[self._POSITION_GRID_FROZEN_SHARES]),
                    "cost_price": float(pos[self._POSITION_GRID_COST_PRICE]),
                    "market_price": float(pos[self._POSITION_GRID_MARKET_PRICE]),
                    "market_value": float(pos[self._POSITION_GRID_MARKET_VALUE]),
                    "float_pnl": float(pos[self._POSITION_GRID_FLOAT_PNL]),
                    "pnl_pct": float(pos[self._POSITION_GRID_PNL_PCT])
                }
            )
        return position_list

    @property
    def today_entrusts(self):
        return self._get_today_entrusts()

    def _get_today_entrusts(self):
        """
        获取当日委托
        :return:
        """
        url = self.config["today_entrusts_url"]
        payload = {"gdzh": self.account_config["sh_gdzh"], "mkcode": "2"}
        r = self._post(url, payload)
        resp_json = json.loads(r)
        ths_entrusts = resp_json["result"]["list"]
        entrust_list = []
        for e in ths_entrusts:
            entrust_list.append(
                {
                    "stock_code": e[self._TODAY_ENTRUSTS_GRID_STOCK_CODE],
                    "stock_name": e[self._TODAY_ENTRUSTS_GRID_STOCK_NAME],
                    "status": e[self._TODAY_ENTRUSTS_GRID_STATUS],
                    "shares": e[self._TODAY_ENTRUSTS_GRID_SHARES],
                    "tx_shares": e[self._TODAY_ENTRUSTS_GRID_TX_SHARES],
                    "price": e[self._TODAY_ENTRUSTS_GRID_PRICE],
                    "tx_price": e[self._TODAY_ENTRUSTS_GRID_TX_PRICE],
                    "direction": e[self._TODAY_ENTRUSTS_GRID_DIRECTION],
                    "time": e[self._TODAY_ENTRUSTS_GRID_TIME],
                    "date": e[self._TODAY_ENTRUSTS_GRID_DATE],
                    "contract_no": e[self._TODAY_ENTRUSTS_GRID_CONTRACT_NO],
                    "mode": e[self._TODAY_ENTRUSTS_GRID_MODE]
                }
            )
        return entrust_list

    @property
    def today_trades(self):
        return self._get_today_trades()

    def _get_today_trades(self):
        """
        获取当日成交
        :return:
        """
        url = self.config['today_trades_url']
        payload = {"gdzh": self.account_config["sh_gdzh"], "mkcode": "2"}
        r = self._post(url, payload)
        resp_json = json.loads(r)
        ths_trades = resp_json["result"]["list"]
        trades_list = []
        for t in ths_trades:
            trades_list.append(
                {
                    "stock_code": t[self._TODAY_TRADES_GRID_STOCK_CODE],
                    "stock_name": t[self._TODAY_TRADES_GRID_STOCK_NAME],
                    "direction": t[self._TODAY_TRADES_GRID_DIRECTION],
                    "tx_shares": t[self._TODAY_TRADES_GRID_TX_SHARES],
                    "tx_price": t[self._TODAY_TRADES_GRID_TX_PRICE],
                    "tx_amount": t[self._TODAY_TRADES_GRID_TX_AMOUNT],
                    "contract_no": t[self._TODAY_TRADES_GRID_CONTRACT_NO],
                    "tx_no": t[self._TODAY_TRADES_GRID_TX_NO],
                    "date": t[self._TODAY_TRADES_GRID_DATE]
                }
            )
        return trades_list

    @property
    def today_recall(self):
        return self._get_today_recall()

    def _get_today_recall(self):
        """
        获取当日可撤单的委托
        :return:
        """
        url = self.config["today_recall_url"]
        payload = {"gdzh": self.account_config["sh_gdzh"], "mkcode": "2"}
        r = self._post(url, payload)
        resp_json = json.loads(r)
        if resp_json["errorcode"] != self._HTTP_RESPONSE_OK:
            log.warning("查询出错")
            return None
        ths_entrusts = resp_json["result"]["list"]
        entrust_recall = []
        for e in ths_entrusts:
            entrust_recall.append(
                {
                    "stock_code": e[self._TODAY_ENTRUSTS_GRID_STOCK_CODE],
                    "stock_name": e[self._TODAY_ENTRUSTS_GRID_STOCK_NAME],
                    "status": e[self._TODAY_ENTRUSTS_GRID_STATUS],
                    "shares": e[self._TODAY_ENTRUSTS_GRID_SHARES],
                    "tx_shares": e[self._TODAY_ENTRUSTS_GRID_TX_SHARES],
                    "price": e[self._TODAY_ENTRUSTS_GRID_PRICE],
                    "tx_price": e[self._TODAY_ENTRUSTS_GRID_TX_PRICE],
                    "direction": e[self._TODAY_ENTRUSTS_GRID_DIRECTION],
                    "time": e[self._TODAY_ENTRUSTS_GRID_TIME],
                    "date": e[self._TODAY_ENTRUSTS_GRID_DATE],
                    "contract_no": e[self._TODAY_ENTRUSTS_GRID_CONTRACT_NO],
                    "mode": e[self._TODAY_ENTRUSTS_GRID_MODE]
                }
            )
        return entrust_recall

    def buy(self, stock_code, order_type="limit", price=0, amount=0):
        """
        委托买入股票
        :param stock_code: 证券代码
        :param order_type: 下单类型，市价单或限价单
        :param price: 价格
        :param amount: 数量
        :param volume: 金额
        :return:
        """
        return self._trade(stock_code, order_type, price, amount)

    def sell(self, stock_code, order_type="limit", price=0, amount=0):
        """
        委托卖出股票
        :param stock_code:
        :param order_type: 下单类型，市价单或限价单
        :param price:
        :param amount:
        :param volume:
        :return:
        """
        return self._trade(stock_code, order_type, price, amount, "sell")

    def cancel_entrust(self, contract_no, date):
        """
        撤销委托单
        :param contract_no: 委托单合同编号
        :param date: 委托日期 格式 yyyyMMdd 如：20190530
        :return:
        """
        url = self.config["cancel_entrust_url"]
        payload = {"htbh": contract_no, "wtrq": date}
        r = self._post(url, payload)
        resp_json = json.loads(r)
        if resp_json["errorcode"] == self._HTTP_RESPONSE_OK:
            return "撤单成功"


    def _trade(self, stock_code, order_type, price, amount, entrust_bs="buy"):
        """
        委托下单
        :param stock_code: 证券代码
        :param order_type: 下单类型，市价单或限价单 MKT/LMT
        :param price: 价格（限价模式有效）
        :param amount: 交易数量
        :param entrust_bs: 委托方向
        :return:
        """
        balance = self.get_balance()
        position_list = self.get_position()
        sellable_stocks = {el["stock_code"]: el["sellable_shares"] for el in position_list}
        # 检测下单金额
        volume = price * amount
        stock_price = self._query_stock_price(stock_code)
        if entrust_bs == "buy" and balance["available_balance"] < volume:
            raise exceptions.TradeError(u"没有足够的可用金额进行操作")
        if entrust_bs == "sell" and stock_code in sellable_stocks and amount > sellable_stocks[stock_code]:
            raise exceptions.TradeError(u"没有足够的可卖股数")
        if price > stock_price["up_limit"] or price < stock_price["down_limit"]:
            raise exceptions.TradeError(u"价格超过涨跌幅限制")
        # 限价单下单
        gdzh = self.account_config["sz_gdzh"] if stock_code[0] == "0" or stock_code[0] == "3" else self.account_config["sh_gdzh"]
        mkcode = '1' if stock_code[0] == "0" or stock_code[0] == "3" else '2'
        if order_type == self._TRADING_PRICE_LMT:
            url = self.config["trade_url"]
            payload = {
                "type": self._TRADING_TYPE_BUY if entrust_bs == "buy" else self._TRADING_TYPE_SELL,
                "stockcode": stock_code,
                "gdzh": gdzh,
                "mkcode": mkcode,
                "price": price,
                "amount": amount
            }
            r = self._post(url, payload)
            resp_json = json.loads(r)
            if resp_json["errorcode"] == self._HTTP_RESPONSE_OK:
                log.debug("下单成功")
                data = resp_json["result"]["data"]
                return {
                    "stock_code": data["stockcode"],
                    "entrust_contract_no": data["htbh"]
                }
            else:
                log.warning("下单失败")
                return None
        # 市价单下单
        if order_type == self._TRADING_PRICE_MKT:
            url = self.config["market_trade_url"]
            payload = {
                "type": self._TRADING_TYPE_BUY if entrust_bs == "buy" else self._TRADING_TYPE_SELL,
                "stockcode": stock_code,
                "gdzh": gdzh,
                "mkcode": mkcode,
                "amount": amount,
                "sjwttype": self._TRADING_ORDER_TYPE_FIVE_BEST_IMMEDIATE_OR_CANCEL_SZ if mkcode == '1' else self._TRADING_ORDER_TYPE_FIVE_BEST_IMMEDIATE_OR_CANCEL_SH
            }
            r = self._post(url, payload)
            resp_json = json.loads(r)
            if resp_json["errorcode"] == self._HTTP_RESPONSE_OK:
                data = resp_json["result"]["data"]
                log.debug("下单成功")
                return {
                    "stock_code": data["stockcode"],
                    "entrust_contract_no": data["htbh"]
                }
            else:
                log.warning("下单失败")
                return None

    def _query_stock_price(self, stock_code):
        """
        查询股票价格（返回股票涨停价和跌停价）
        :param stock_code:
        :return:
        """
        url = self.config["query_price_url"]
        payload = {"type": self._TRADING_TYPE_BUY, "stockcode": stock_code}
        r = self._post(url, payload)
        resp_json = json.loads(r)
        if resp_json["errorcode"] == self._HTTP_RESPONSE_OK:
            data = resp_json["result"]["data"]
            up_limit = data["st_up_limit"]
            down_limit = data["st_down_limit"]
            stock_code = data["stockcode"]
            stock_name = data["st_name"]
            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "up_limit": float(up_limit),
                "down_limit": float(down_limit)
            }


    def _get(self, url):
        return self.s.get(url).text

    def _post(self, url, params):
        return self.s.post(url, data=params).text
