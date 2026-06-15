# AlphaSniper Mobile Cloud V1

这是给 iPhone Safari / GitHub Pages 使用的静态前端版本。

## 你上传 GitHub 的文件

把这些文件放到 GitHub Pages 仓库根目录：

- `index.html`
- `app.js`
- `style.css`
- `manifest.json`

然后打开你的 GitHub Pages 地址即可。

## 重要：行情数据说明

GitHub Pages 只能托管静态网页，不能运行后端。浏览器直接抓 Yahoo 行情时，Safari 可能会被跨域限制拦截。

如果页面扫描失败，请把 `worker-cloudflare.js` 部署到 Cloudflare Workers，然后在网页右上角 `设置` 里填入 Worker 地址，例如：

```text
https://your-worker-name.your-account.workers.dev
```

## Cloudflare Worker 部署步骤

1. 打开 Cloudflare Workers。
2. 新建 Worker。
3. 删除默认代码。
4. 复制 `worker-cloudflare.js` 的全部内容粘贴进去。
5. 保存并部署。
6. 复制 Worker 地址。
7. 回到 AlphaSniper 页面 → 设置 → 填入 Worker 地址 → 保存。

## 使用流程

1. 手机 Safari 打开你的 GitHub Pages 页面。
2. 先选 `核心高流动性池（推荐）`。
3. 扫描数量先用 30 或 50。
4. 点击 `开始扫描`。
5. 只看 `可买` 和 `等回踩`。
6. 点股票查看买入区、止损、止盈。
7. 下单前必须用券商价格复核。
8. 如果价格不一致，用 `输入券商真实现价重算`。

## 交易定位

这是人工下单决策工具，不是自动交易机器人。它不会连接券商，也不会替你下单。
