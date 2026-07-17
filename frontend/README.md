# theNanGuos frontend

本地音乐 Agent 创作工作台，使用 React、TypeScript、Vite 和 React Flow。

```bash
npm install
npm run dev
```

开发服务器默认通过 Vite 将同源的 `/api` 和 `/works` 请求代理到
`http://127.0.0.1:8000`，因此使用远程开发环境或端口转发访问前端时也能连接后端。
可通过 `VITE_API_PROXY_TARGET` 指定开发代理目标；构建前端时可通过
`VITE_API_BASE` 指定独立部署的 API 地址。

```bash
npm run lint
npm run build
npm run test:e2e
```
