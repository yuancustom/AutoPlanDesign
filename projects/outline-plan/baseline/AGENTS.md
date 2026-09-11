# Agent entry point

先读取 `skills/outline-floorplan-local/SKILL.md`、`README.md` 和 `docs/IMPLEMENTATION_REPORT.md`。

只完成 02 L 形三层试点。禁止擅自扩展到十栋、下载多套大模型、污染既有 Conda 环境、自动转云生成、提交权重/字体/凭据。几何图、API dry-run、mock 测试、真实本机推理必须分别记录。

用户在 2026-09-10 明确要求删除非 main 分支并直接提交 main。之后按这一授权在 main 上做普通新增提交；写入前读取最新分支头，不 force push、不重写历史、不重新创建功能分支或 PR，除非用户另有要求。不要删除 main。

验收：`python -m pytest -q`；`python scripts/run_pilot.py --mode dry-run --job examples/l_shape_job.json --out runs/new-unique-run`。真实生成使用 `--mode render --ack-concept-only`，且必须在用户本机服务完成。几何叠线后的最终图不能证明模型原图通过验收。
