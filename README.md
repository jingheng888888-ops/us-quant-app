# AlphaSniper Mobile Cloud V2 - Modal Fix

修复内容：
- 修复 iPhone Safari 上“数据设置”弹窗关不掉的问题。
- 修复 GitHub Pages 首次打开自动显示设置弹窗的问题。
- 现在点“关闭”、点弹窗外空白、或保存设置后都会关闭弹窗。

上传 GitHub Pages：
1. 替换仓库里的 `index.html`、`app.js`、`style.css`、`manifest.json`。
2. `worker-cloudflare.js` 可传可不传；需要 Cloudflare Worker 时再用。
3. 等 GitHub Pages 更新 1-5 分钟。
4. Safari 强制刷新一次；如果还看到旧页面，清理浏览器缓存或在网址后加 `?v=2`。

注意：这是人工下单辅助工具，不是自动下单软件。下单前必须用券商价格复核。
