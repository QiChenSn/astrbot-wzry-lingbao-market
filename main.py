from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
import re
import aiohttp
from typing import Optional, Dict, Any, List, Tuple

DEFAULT_CONFIG = {
    "enabled": True,
    "pattern": r"",
    "api_url": "",
    "max_matches": 1,
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
        try:
            self._regex = re.compile(pattern)
        except re.error as exc:
            logger.error("正则表达式无效: %s", exc)
            return

        self._session = aiohttp.ClientSession()
        logger.info("插件初始化完成，当前使用的后端地址=%s", self._api_url)

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令"""
        user_name = event.get_sender_name()
        message_str = event.message_str
        message_chain = event.get_messages()
        logger.info(message_chain)
        yield event.plain_result(f"你好，{user_name}，你发了 {message_str}！")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def forward_matches(self, event: AstrMessageEvent):
        """监听所有消息，匹配配置正则并转发到后端。"""
        if not self._regex or not self._api_url:
            return
        text = event.message_str or ""
        matches = self._regex.findall(text)
        if not matches:
            return

        limited = matches if self._max_matches <= 0 else matches[: self._max_matches]
        for match in limited:
            await self._dispatch_match(str(match))

    async def _dispatch_match(self, matched_text: str):
        if not self._session:
            return
        payload = {"data": matched_text}
        try:
            async with self._session.post(
                self._api_url,
                json=payload,
                headers=self._headers,
                timeout=self._timeout,
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    logger.error("转发失败 status=%s body=%s", resp.status, body)
                else:
                    logger.info("转发成功 status=%s", resp.status)
        except Exception:
            logger.exception("转发匹配内容时出现异常")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        if self._session:
            await self._session.close()
            self._session = None
