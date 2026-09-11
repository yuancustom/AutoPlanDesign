# P3 V3 同步核验范围

任务 P3-UX-01，日期 2026-09-11。

## 本轮实际执行

- 仓库版 13 个运行时文件的 Git blob SHA 与本地待测文件逐一核对一致。
- Node.js 22.16.0 对 sample.js 和 app-1.js 至 app-8.js 的语法检查通过。
- 新 build_standalone.py 生成独立 HTML，使用仓库内压缩示例图。
- Chromium / Playwright 1.57.0 重新运行原版交互断言：**62 项通过，0 个捕获的 JavaScript 错误，无外部服务请求**。
- 覆盖 1440×900、1280×800、1024×768、390×844，最后一种 DPR=2；采用 page.set_content，存储降级模式通过。
- 第一次执行被当前工具主机 120 秒时限结束；再次完整运行后 62 项通过，没有通过删除断言来绕过失败。

## 本地主机限制

尝试目录 HTTP 载入时，当前受限浏览器返回 `net::ERR_BLOCKED_BY_ADMINISTRATOR`。因此本轮不把目录导航、文件导航或 IndexedDB 刷新恢复标为本地通过。qa/smoke_test.py 保留这些断言，在 GitHub Actions 或用户本机正常浏览器环境执行；不修改浏览器管理策略来绕过限制。

## CI 与历史证据

.github/workflows/p3-prototype.yml 会从本次提交构建，再分别跑原 62 项交互回归和目录/独立页载入检查。实时结果以 Actions 的该提交 run 为准；publication-test.json 是提交前快照，不是 CI 成功回执。截图、完整 JSON 和独立 HTML 存在对应运行 artifact。

原完整包中的测试报告只描述历史单页版本；这里描述的是本轮重新构建后的版本。测试脚本只适配路径和 Chromium 可执行文件配置，交互断言未简化。

## 始终未测试

真实图纸识别、模型推理、BIMFACE、真实 DXF/PDF/GLB 导出、用户 Mac Safari、服务端多用户审计、工程规范。程序三维与定时进度不是上述功能的验收证据。
