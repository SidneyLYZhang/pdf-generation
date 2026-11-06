# 排版模板自带，不依赖 Typst Universe 包

`@preview` 包在本机拉不动（沙箱内 Schannel 取不到凭证，`raw.githubusercontent` 同样不通），本地缓存只有 8 个包，chengsi 无法获取；更关键的是生态模板的 API 互不相同（chengsi 传 config 字典，biz-report 传 conf 参数），要把"用户可调排版"统一暴露出来，就得为每个包写一套适配层。决定：skill 自带 `template/`，零外部包依赖，用 Kind 派生版式；chengsi 只作为观感参考（衬线正文、章首留白、细线标题、青绿/靛蓝/赭棕三色）。

## Consequences

- 首次使用不需要联网，也不会因为上游包升级而改变排版。
- 拿不到生态模板的持续更新；需要新观感时，靠改 Knob 或加内置 Preset，而不是换包。
- 引用、定理这类"包生态能力"要自己实现最小可用版本。
