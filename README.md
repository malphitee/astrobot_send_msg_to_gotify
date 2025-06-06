# AstrBot Gotify 转发插件

一个功能强大的 AstrBot 插件，用于监听指定用户的消息并自动转发到 Gotify 推送服务。

## ✨ 主要功能

- 🎯 **精准监听**：支持监听多个指定用户 ID 的消息
- 🔍 **智能过滤**：支持关键词包含/排除规则，灵活控制转发条件
- 📝 **自定义模板**：支持自定义消息标题和内容模板
- ⚡ **异步处理**：高性能异步消息处理，不影响机器人主要功能
- 🛠️ **易于配置**：通过 AstrBot 管理面板可视化配置
- 📊 **状态监控**：提供插件状态查看和连接测试功能

## 📋 系统要求

- AstrBot >= 3.5.13
- Python >= 3.8
- Gotify 服务器

## 🚀 安装方法

### 方法一：通过 AstrBot 插件市场安装

1. 打开 AstrBot 管理面板
2. 进入插件管理页面
3. 搜索 "send_message_to_gotify"
4. 点击安装

### 方法二：手动安装

1. 下载插件源码到 AstrBot 插件目录：
```bash
cd AstrBot/data/plugins
git clone https://github.com/malphitee/astrobot_send_msg_to_gotify.git
```

2. 安装依赖：
```bash
pip install aiohttp>=3.8.0
```

3. 重启 AstrBot 或在管理面板重载插件

## ⚙️ 配置说明

在 AstrBot 管理面板的插件配置中设置以下参数：

### 基础配置

| 配置项 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `gotify_server` | string | ✅ | Gotify 服务器地址 | `https://push.example.com` |
| `gotify_token` | string | ✅ | Gotify 应用令牌 | `A4f8kL9mN2p7` |
| `monitored_users` | list | ✅ | 监听的用户 ID 列表 | `["12345678", "87654321"]` |

### 高级配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `enable_filter` | bool | `false` | 是否启用关键词过滤 |
| `include_keywords` | list | `[]` | 包含关键词列表（消息必须包含其中之一） |
| `exclude_keywords` | list | `[]` | 排除关键词列表（包含这些关键词的消息不转发） |
| `gotify_priority` | int | `5` | Gotify 消息优先级（0-10） |
| `enable_logging` | bool | `true` | 是否启用详细日志 |

### 消息模板配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `title_template` | string | `来自 {sender_name} 的消息` | 消息标题模板 |
| `message_template` | text | `发送者：{sender_name}\n时间：{timestamp}\n内容：{message_content}` | 消息内容模板 |

#### 可用模板变量

- `{sender_name}` - 发送者姓名
- `{user_id}` - 发送者 ID
- `{message_content}` - 消息内容
- `{timestamp}` - 时间戳
- `{platform}` - 消息平台名称

## 📖 使用指南

### 1. 获取 Gotify Token

1. 登录您的 Gotify 管理后台
2. 创建新的应用程序
3. 复制生成的 Token

### 2. 获取用户 ID

不同平台的用户 ID 获取方式：
- **QQ**：QQ 号码
- **微信**：微信号或通过开发者工具获取
- **Telegram**：用户的数字 ID

### 3. 配置插件

1. 在 AstrBot 管理面板找到插件配置
2. 填写 Gotify 服务器地址和 Token
3. 添加要监听的用户 ID
4. 根据需要配置过滤规则和消息模板
5. 保存配置

### 4. 测试连接

使用以下指令测试 Gotify 连接：
```
/gotify_test
```

### 5. 查看状态

使用以下指令查看插件状态：
```
/gotify_status
```

### 6. 调试用户信息

如果遇到用户信息获取问题（特别是 Telegram 用户），可使用调试指令：
```
/gotify_debug
```
此指令会显示详细的用户信息结构，帮助排查问题。

## 💡 使用场景

### 场景一：监控客户消息
监听特定客户的消息，及时响应重要沟通：
```json
{
  "monitored_users": ["客户QQ号"],
  "filter_keywords": {
    "enable_filter": true,
    "include_keywords": ["紧急", "重要", "问题"]
  }
}
```

### 场景二：团队通知
监听团队成员的重要通知：
```json
{
  "monitored_users": ["成员1", "成员2", "成员3"],
  "message_template": {
    "title_template": "团队消息 - {sender_name}",
    "message_template": "👥 团队成员：{sender_name}\n⏰ 时间：{timestamp}\n💬 内容：{message_content}"
  }
}
```

### 场景三：关键词监控
过滤包含特定关键词的消息：
```json
{
  "filter_keywords": {
    "enable_filter": true,
    "include_keywords": ["订单", "支付", "退款"],
    "exclude_keywords": ["测试", "无关"]
  }
}
```

## 🔧 常见问题

### Q: 插件加载失败怎么办？
A: 检查以下几点：
1. 确保 AstrBot 版本 >= 3.5.13
2. 检查依赖是否安装：`pip install aiohttp>=3.8.0`
3. 查看 AstrBot 日志了解具体错误

### Q: 消息没有转发到 Gotify
A: 排查步骤：
1. 使用 `/gotify_test` 测试连接
2. 检查用户 ID 是否正确
3. 检查过滤规则是否过于严格
4. 查看插件日志

### Q: 如何获取微信用户 ID？
A: 微信用户 ID 获取较为复杂，建议：
1. 使用微信机器人的开发者工具
2. 查看消息日志中的发送者信息
3. 联系技术支持获取帮助

### Q: Telegram 用户显示为"未知用户"怎么办？
A: Telegram 用户信息获取有以下几种情况：
1. **用户设置了用户名**：会显示 `@username`
2. **用户只有昵称**：会显示 `FirstName LastName`
3. **隐私设置限制**：可能只显示用户ID

解决方案：
- 使用 `/gotify_debug` 查看实际的用户信息结构
- 检查机器人是否有获取用户信息的权限
- 考虑让用户主动设置 Telegram 用户名

### Q: 支持哪些消息平台？
A: 插件支持 AstrBot 接入的所有平台：
- QQ（个人号/官方接口）
- 微信（个人号/公众平台）
- Telegram
- 飞书
- 钉钉
- 企业微信

## 📝 更新日志

### v1.1.0 (2025-06-07)
- 🔧 **智能用户信息获取**：大幅改进用户姓名获取逻辑
- 💬 **Telegram 支持优化**：专门优化 Telegram 用户信息处理
  - 支持 `first_name + last_name` 组合显示
  - 支持 `@username` 显示
  - 无用户名时回退到用户ID
- 🔍 **多平台兼容**：增强 QQ、微信等平台的用户信息获取
- 🐞 **调试功能**：新增 `/gotify_debug` 指令帮助排查用户信息问题
- 📝 **文档更新**：完善 Telegram 相关的使用说明和问题排查

### v1.0.0 (2025-06-07)
- ✨ 首次发布
- 🎯 支持多用户监听
- 🔍 支持关键词过滤
- 📝 支持自定义消息模板
- ⚡ 异步消息处理
- 🛠️ 可视化配置界面

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/新功能`
3. 提交更改：`git commit -am '添加新功能'`
4. 推送分支：`git push origin feature/新功能`
5. 提交 Pull Request

## 📄 许可证

本项目使用 [GNU Affero General Public License v3.0](LICENSE) 许可证。

## 🙏 致谢

- [AstrBot](https://astrbot.app) - 强大的多平台聊天机器人框架
- [Gotify](https://gotify.net) - 简单的推送通知服务

## 🐞 问题反馈

- [GitHub Issues](https://github.com/malphitee/astrobot_send_msg_to_gotify/issues)

---

**⭐ 如果这个插件对您有帮助，请给个 Star 支持一下！**
