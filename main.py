from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import re
import aiohttp
from typing import Optional, Dict, Any, List, Tuple

DEFAULT_CONFIG = {
    "enabled": True,
    "pattern": r"【(?P<code>[^】]+)】.*?(?P<price>\d+)块",
    "api_url": "",
    "max_matches": 0,
    "timeout": 5,
    "headers": [],
}

@register("astrbot_plugin_lingbao_market", "QiChen", "监听灵宝市集分享码", "1.0.1")
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self._raw_config = config or {}
        self.config: Dict[str, Any] = {}
        self._regex: Optional[re.Pattern] = None
        self._api_url: str = ""
        self._max_matches: int = 1
        self._timeout: int = 5
        self._headers: Dict[str, str] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """加载配置并编译正则。"""
        if not self._raw_config:
            logger.error("未获取到配置，插件初始化终止")
            return
        self.config = dict(DEFAULT_CONFIG)
        self.config.update(dict(self._raw_config))

        enabled = bool(self.config.get("enabled", True))
        pattern = str(self.config.get("pattern", "") or "").strip()
        self._api_url = str(self.config.get("api_url", "") or "").strip()
        self._max_matches = int(self.config.get("max_matches", 1) or 1)
        self._timeout = int(self.config.get("timeout", 5) or 5)
        headers_list: List[Dict[str, str]] = self.config.get("headers") or []
        self._headers = {
            str(item.get("key")).strip(): str(item.get("value")).strip()
            for item in headers_list
            if item and str(item.get("key", "")).strip()
        }

        logger.info(
            "配置载入完成 enabled=%s pattern=%r api_url=%s max_matches=%s timeout=%s headers=%s",
            enabled,
            pattern,
            self._api_url,
            self._max_matches,
            self._timeout,
            self._headers,
        )

        if not enabled:
            logger.info("插件已被配置关闭，不处理消息")
            return
        if not pattern:
            logger.warning("pattern 未配置，插件停用")
            return
        if not self._api_url:
            logger.warning("api_url 未配置，插件停用")
            return
        if not self._api_url.lower().startswith(("http://", "https://")):
            logger.error("api_url 格式错误，必须以 http:// 或 https:// 开头，当前值: %s", self._api_url)
            return
        try:
            self._regex = re.compile(pattern)
        except re.error as exc:
            logger.error("正则表达式无效: %s", exc)
            return

        self._session = aiohttp.ClientSession()
        logger.info("插件初始化完成，当前使用的后端地址=%s", self._api_url)


    @filter.event_message_type(filter.EventMessageType.ALL)
    async def forward_matches(self, event: AstrMessageEvent):
        """监听所有消息，匹配配置正则并转发到后端。"""
        if not self._regex or not self._api_url:
            logger.debug("正则或接口地址未就绪，跳过本次消息")
            return
        text = event.message_str or ""
        matches = list(self._regex.finditer(text))
        if not matches:
            return

        limited = matches if self._max_matches <= 0 else matches[: self._max_matches]
        for match_obj in limited:
            await self._dispatch_match(match_obj)

    async def _dispatch_match(self, match_obj: re.Match):
        if not self._session:
            logger.debug("HTTP 会话未初始化，无法转发")
            return
        # 优先使用命名分组 code/price，其次位置分组
        code = None
        price = None
        if match_obj.groupdict():
            code = match_obj.groupdict().get("code")
            price = match_obj.groupdict().get("price")
        if code is None or price is None:
            groups = match_obj.groups()
            if len(groups) >= 2:
                code, price = groups[0], groups[1]

        # 确保 code 是字符串，price 是整数
        try:
            code_str = str(code) if code is not None else ""
            price_int = int(price) if price is not None else 0
        except ValueError:
            logger.error("价格转换失败，无法转换为整数: price=%s", price)
            return

        payload = {"code": code_str, "price": price_int}
        logger.debug("发送负载：%s", payload)
        try:
            async with self._session.post(
                self._api_url,
                json=payload,
                headers=self._headers,
                timeout=self._timeout,
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    logger.error("转发失败 status=%s body=%s payload=%s", resp.status, body, payload)
                else:
                    logger.info("转发成功 status=%s payload=%s", resp.status, payload)
        except Exception:
            logger.exception("转发匹配内容时出现异常，url=%s payload=%s", self._api_url, payload)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        if self._session:
            await self._session.close()
            self._session = None
