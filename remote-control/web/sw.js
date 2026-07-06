// 最小 service worker:只负责让 Edge/Chrome 认定这个站点满足"安装为应用"的条件,
// 不做任何离线缓存(这是个需要实时状态的控制面板,缓存旧数据反而有害)。
self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", () => {
  // 故意不拦截任何请求,全部直通网络。
});
