// 最小 service worker:让 Edge/Chrome 认定站点满足"安装为应用"的条件,并处理 Web Push。
// 不做任何离线缓存(这是个需要实时状态的控制面板,缓存旧数据反而有害)。
// SW_VERSION 只用来让浏览器检测到字节变化、触发 SW 更新——本文件没有 Cache Storage,
// 静态资源全部直通网络,所以不需要真正的缓存失效逻辑。
const SW_VERSION = "5"; // P3 集成:预设命令 + 探针状态页

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", () => {
  // 故意不拦截任何请求,全部直通网络。
});

// Web Push:payload 是服务端 push.py 的 JSON(type/run_id/title/body)。
self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { body: event.data ? event.data.text() : "" };
  }
  const title = data.title || "remote-control";
  event.waitUntil(
    self.registration.showNotification(title, {
      body: data.body || "",
      data: { run_id: data.run_id || null },
      // 同一 run 的多条通知折叠(如先"待确认"后"完成"),避免通知轰炸。
      tag: data.run_id ? `rc-${data.run_id}` : undefined,
      icon: "/icons/icon-192.png",
    })
  );
});

// 点通知 → 打开(或聚焦)面板并直达该 run 的详情(app.js 解析 ?run= 参数)。
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const runId = event.notification.data && event.notification.data.run_id;
  const url = runId ? `/?run=${encodeURIComponent(runId)}` : "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if ("navigate" in client && "focus" in client) {
          return client.navigate(url).then((c) => (c ? c.focus() : undefined));
        }
      }
      return self.clients.openWindow(url);
    })
  );
});
