# -*- coding: utf-8 -*-
import json
import numbers
import os
import re
import time

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

    _POSITION_GRID_STOCK_CODE = "d_2102"        #证券代码
    _POSITION_GRID_STOCK_NAME = "d_2103"        #证券名称
    _POSITION_GRID_HOLD_SHARES = "d_2117"       #证券数量
    _POSITION_GRID_SELLABLE_SHARES = "d_2121"   #可卖数量
    _POSITION_GRID_FROZEN_SHARES = "d_2118"     #冻结数量
    _POSITION_GRID_COST_PRICE = "d_2122"        #成本价
    _POSITION_GRID_MARKET_PRICE = "d_2124"      #当前价
    _POSITION_GRID_MARKET_VALUE = "d_2125"      #最新市值
    _POSITION_GRID_FLOAT_PNL = "d_2147"         #浮动盈亏
    _POSITION_GRID_PNL_PCT = "d_3616"           #盈亏比例（%）

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
        ret = json.loads(r)
        ths_positons = ret["result"]["list"]
        position_list = []
        for pos in ths_positons:
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


    def _get(self, url):
        return self.s.get(url).text

    def _post(self, url, params):
        return self.s.post(url, data=params).text
