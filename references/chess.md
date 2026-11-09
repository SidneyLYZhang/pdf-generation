# 棋谱

三种围栏：`fen`（别名 `chess`）、`pgn`、`notation`。棋盘和走法记谱由内联的 staunton 2.0.0 排版，**构建不需要联网**。

## 一个局面

````markdown
```fen {#fig:italian caption="意大利开局" size=6cm}
r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3
```
````

- 围栏正文就是 FEN 那一行（Lichess 的「复制 FEN」直接粘）。
- **棋盘总是带编号**（staunton 给每张图编号），写 `caption` 只是加题注文字；`{#fig:italian}` 让 `@fig:italian` 能引用。
- 中文文档的编号前缀是「棋图」，与普通图片的「图」分开计数——Typst 按种类计数，混排时两个「图 1」会分不清。

## 棋局里的某一步

````markdown
```pgn {at="17w"}
[White "Morphy"]
[Black "Allies"]
[Date "1858.??.??"]

1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7
8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7
14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0
```
````

`at` 是「步数 + 颜色」：`17w` / `17b`，必须落在棋局实际存在的步数内。棋手与年份来自 PGN 头，会显示在棋盘上方；不给 `caption` 时题注是 `Position after 17. Rd8#` 这类英文串。

## 标注

````markdown
```fen {flip=true labels=false arrows="f3e5,f1c4" highlight="e5,d4" check=true last-move="arrow" theme="wikipedia"}
r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3
```
````

| 选项 | 作用 | 默认 |
|------|------|------|
| `caption` | 题注文字（编号总是有的） | 无 |
| `#fig:xxx` | 图标签，供 `@fig:` 引用 | 无 |
| `size` | 棋盘尺寸（`6cm` / `50%`），超出可用宽度会自动收 | 6.4cm |
| `flip` | 翻转棋盘（黑方在下） | `false` |
| `labels` | 坐标标签 | `true` |
| `check` | 将军高亮 | `false` |
| `last-move` | 上一手标注：`none` / `arrow` / `squares`；只有 `pgn` 有上一步可标 | `none` |
| `theme` | 配色：`wikipedia` / `wood` 之外的 11 个内置名（报错时会列全） | `staunton-default` |
| `arrows` | 箭头，逗号分隔的 `起点终点`，如 `f3e5,f1c4` | 无 |
| `highlight` | 高亮格子，如 `e5,d4` | 无 |
| `at` | 仅 `pgn`：出某一手的局面 | 无 |

## 走法记谱

````markdown
```notation {figurine=true variations=true comments=true}
1. e4 {很好的开局} (1... c5 2. Nf3) e5 2. Nf3! Nc6 *
```
````

| 选项 | 作用 | 默认 |
|------|------|------|
| `figurine` | 用棋子符号代替 N/B/R/Q/K | `false` |
| `variations` | 显示变着 `(1... c5 …)` | `false` |
| `nags` | 显示 `!?` 这类评注符号 | `false` |
| `comments` | 显示 `{...}` 注释 | `false` |
| `move-numbers` | 显示回合数 | `true` |

注释、变着和 `!?` 只存在于「棋局」里，所以 `notation` 围栏的内容总是先按 PGN 解析（内部走 `game()`），
只写裸走法也能用。

## 坑

- 选项名写错会直接报错并列出合法项；`{orientation=black}` 这种 staunton 本身会静默忽略的写法在这里是硬错误。
- `at` 只能用在 `pgn` 上，超出棋局实际步数会渲染失败。
- 自动题注（`White to move`、`Position after 3. Bb5`）是 staunton 的英文串，中文文档只把编号前缀换成「棋图」；要中文题注就自己写 `caption`。
- 语言是按正文比例判的：棋谱内容很长、中文很少的文档可能被判成英文，这时用 `--set text.lang=zh` 强制。
- `last-move` 在 `fen` 上没有效果（没有上一步），写了也不报错。
- 只有国际象棋（以及 staunton 支持的正规变体）；象棋、将棋不在支持范围。
