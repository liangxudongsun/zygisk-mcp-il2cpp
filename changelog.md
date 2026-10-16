# Zygisk IL2CPP MCP 2.8.3 更新说明

更新日期：2026-10-17

作者：洋葱落日 && DUM

这次主要补齐 JavaScript Frida，并统一 HTTP 与 Python MCP 的使用体验，原有功能继续保留。

## 本次更新 [issues#8](https://github.com/ssyclr/zygisk-mcp-il2cpp/issues/8)

- 新增 `frida_script`：AI 可以直接运行 Frida JavaScript，管理脚本、收发消息、查看异常和卸载脚本。支持原生函数 Hook、参数／返回值修改及内存操作，无需另开 frida-server。
- HTTP 与 Python MCP 共用设备端工具、具名参数、返回结果和功能开关，保留旧原生别名；修复长脚本、失败任务状态和链条结果不一致的问题。
- 修复 `_Rim` 等材质属性因可选 API 缺失而无法写入的问题，兼容整数属性 ID；必要的类型、对象与作用域校验继续保留。
- 修复字符串交叉引用分页时，跨页 ARM64 地址计算指令可能导致引用遗漏的问题。

## 使用提醒

JavaScript 引擎目前支持 Android ARM64；Java 桥接需要另外打包到脚本中。脚本可能改变游戏状态，卸载不会自动恢复任意内存写入。游戏重启后旧地址、任务 ID 和脚本失效，需要重新定位，避免复用旧地址。

升级时请同步更新手机模块与 Python MCP 文件，重新连接并刷新工具列表。原生 HTTP 用户仍可直接通过端口连接。版本更新不代表已验证所有设备与游戏的兼容性。

模块版本为 `v2.8.3`，versionCode 为 `283`；Python MCP、原生 HTTP MCP、WebUI 和悬浮窗标题同步更新。

[MCP 使用说明](mcp/README.md)