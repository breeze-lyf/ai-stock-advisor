export type BrowserSubscriptionPayload = {
  endpoint: string;
  p256dh: string;
  auth: string;
};

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; i += 1) {
    outputArray[i] = rawData.charCodeAt(i);
  }

  return outputArray;
}

function getSubscriptionKeys(subscription: PushSubscription): BrowserSubscriptionPayload {
  const p256dh = subscription.getKey("p256dh");
  const auth = subscription.getKey("auth");

  if (!p256dh || !auth) {
    throw new Error("浏览器推送订阅缺少必要密钥");
  }

  return {
    endpoint: subscription.endpoint,
    p256dh: window.btoa(String.fromCharCode(...new Uint8Array(p256dh))),
    auth: window.btoa(String.fromCharCode(...new Uint8Array(auth))),
  };
}

export async function subscribeCurrentBrowser(vapidPublicKey: string): Promise<BrowserSubscriptionPayload> {
  if (!("serviceWorker" in navigator)) {
    throw new Error("当前浏览器不支持 Service Worker");
  }
  if (!("PushManager" in window)) {
    throw new Error("当前浏览器不支持 Web Push");
  }

  const registration = await navigator.serviceWorker.register("/sw.js");
  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    throw new Error("浏览器通知权限未授予");
  }

  let subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
    });
  }

  return getSubscriptionKeys(subscription);
}

export async function unsubscribeCurrentBrowser(): Promise<void> {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  const registration = await navigator.serviceWorker.getRegistration("/sw.js");
  if (!registration) {
    return;
  }

  const subscription = await registration.pushManager.getSubscription();
  if (subscription) {
    await subscription.unsubscribe();
  }
}

export async function hasCurrentBrowserSubscription(): Promise<boolean> {
  if (!("serviceWorker" in navigator)) {
    return false;
  }
  const registration = await navigator.serviceWorker.getRegistration("/sw.js");
  if (!registration) {
    return false;
  }
  const subscription = await registration.pushManager.getSubscription();
  return Boolean(subscription);
}

export async function getCurrentBrowserEndpoint(): Promise<string | null> {
  if (!("serviceWorker" in navigator)) {
    return null;
  }
  const registration = await navigator.serviceWorker.getRegistration("/sw.js");
  if (!registration) {
    return null;
  }
  const subscription = await registration.pushManager.getSubscription();
  return subscription?.endpoint || null;
}
