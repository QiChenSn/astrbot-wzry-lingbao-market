# 灵宝市集监听

## 介绍

监听群聊消息中指定格式的内容，发送至用户后端接口。

## 配置

配置项已在 `metadata.yaml` 的 `config` 段定义，安装后可在 AstrBot 前端或 `config.yaml` 中填写。可参考 `config.example.yaml`：

```yaml
enabled: true
pattern: "(?<!\\d)(\\d{6})(?!\\d)"   # 匹配规则，示例为 6 位数字
api_url: "https://your-backend.example.com/lingbao"  # 接收 POST 的后端接口
max_matches: 1        # 每条消息最多转发几个匹配，<=0 表示全部
timeout: 5            # 请求超时（秒）
headers:              # 可选附加头
  Authorization: "Bearer YOUR_TOKEN"
```

## 行为
- 插件启用且配置合法时，监听所有消息。
- 使用正则 `pattern` 查找匹配，按 `max_matches` 限制数量。
- 对每个匹配发送 POST 到 `api_url`，JSON 体为 `{"data": "匹配到的内容"}`，附带 `headers`。
- 请求失败会记录日志（包含状态码和响应体）。

## 指令
- `/helloworld` 示例指令，回复 hello 消息。

## 依赖
- `aiohttp`（已在代码中引用，请在部署环境安装）。
