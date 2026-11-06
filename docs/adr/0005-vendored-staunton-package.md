# 把 staunton 2.0.0 内联进仓库，用 `--package-path` 解析

ADR-0002 决定过「零外部包」，理由之一正是 `@preview` 包在本机拉不动。棋谱必须用 staunton（用户指定）。后续核实：本机并非完全断网，走 Schannel 的客户端（typst、curl、PowerShell）卡在 TLS 凭证上，走 OpenSSL 的（Python、Node/npm）能连出去——所以「拉不动」只对 Typst 自己成立。即便如此，让每个使用者先联网、再往自己的全局缓存里塞一个包，仍然不是 skill 该有的前提。决定：把发布包按原样内联到仓库，构建时用 `--package-path` 指过去，import 行保持 `@preview/staunton:2.0.0` 不变——用的仍是那个包、锁死那个版本，但不依赖运行时联网。

## Considered Options

- **只认本地缓存**：仓库保持苗条且纯 MIT，但在拿不到网络的机器上，棋谱功能等于不可用，用户会以为功能坏了。
- **自己实现棋盘排版**：绕开许可与体积问题，但要重写 FEN/PGN 解析与棋子绘制，正是 staunton 已经做完的事。

## Consequences

- README / INSTALL 里「运行时不联网」这句话继续成立；代价是仓库多出约 0.5 MB，升级包要手工替换并重跑验证。
- 棋子的 cburnett / merida SVG 是 GPL-2.0-or-later，与仓库的 MIT 不同：该子目录单独挂 LICENSE 与 NOTICE，其余代码仍为 MIT，交付物（PDF）不受影响。
- 若内联包最终编译不过，回退到「只认本地缓存 + doctor 明确报错」的方案，而不是假装支持。
