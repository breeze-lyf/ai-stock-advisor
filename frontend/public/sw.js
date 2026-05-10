self.addEventListener("push", (event) => {
  if (!event.data) {
    return;
  }

  let payload = {};
  try {
    payload = event.data.json();
  } catch {
    payload = { title: "AI Smart Investment Advisor", body: event.data.text() };
  }

  const title = payload.title || "AI Smart Investment Advisor";
  const options = {
    body: payload.body || "你有一条新的通知",
    icon: "/next.svg",
    badge: "/next.svg",
    data: payload.data || {},
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/";
  event.waitUntil(clients.openWindow(targetUrl));
});
