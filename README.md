# 灵宝市集监听

## 介绍

监听群聊消息中指定格式的内容，发送至用户后端接口。

## 配置

配置通过 `_conf_schema.json` 定义，安装后可在 AstrBot 前端配置。

- `enabled`：是否启用插件。
- `pattern`：用于匹配消息的正则表达式，**必须包含命名分组 `code` 与 `price`**。默认值：`【(?P<code>[^】]+)】.*?(?P<price>\d+)块`，可匹配示例消息：`王者荣耀【星空之诺M2XLLN】我的小马糕今天897块，复制链接来我的市集出售，马年上分大吉！`，提取 `code=星空之诺M2XLLN`、`price=897`。
- `api_url`：接收匹配内容的后端 POST 接口地址（需以 http:// 或 https:// 开头）。
- `max_matches`：每条消息最多转发几个匹配，`<=0` 表示全部，默认 0。
- `timeout`：请求超时（秒），默认 5。
- `headers`：可选追加的 HTTP 头部列表（每项包含 `key` 与 `value`）。

## 行为
- 插件启用且配置合法时，监听所有消息。
- 使用正则 `pattern` 查找匹配，按 `max_matches` 限制数量。
- 对每个匹配发送 POST 到 `api_url`，JSON 体为 `{"data": {"code": <分享码>, "price": <价格>}}`，并附带配置的 `headers`。
- 请求失败会记录日志（包含状态码和响应体），异常会输出请求的 url 与 payload。


## 依赖
- `aiohttp`。
