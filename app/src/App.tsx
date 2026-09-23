import { lazy, Suspense, useEffect, useState } from "react";
import {
  clearSession,
  readSession,
  writeSession,
  type Session,
} from "./lib/session";
import { LandscapeGate } from "./components/LandscapeGate";
import { useOnlineStatus } from "./hooks/useOnlineStatus";
import { currentSession, demoLogin, entraLogin, login, logout } from "./lib/authApi";
import { LoginPage } from "./pages/LoginPage";

const SitePickerPage = lazy(() =>
  import("./pages/SitePickerPage").then((module) => ({
    default: module.SitePickerPage,
  })),
);

type Screen = "login" | "sites";

export default function App() {
  const online = useOnlineStatus();
  const [session, setSession] = useState<Session | null>(() => readSession());
  const [screen, setScreen] = useState<Screen>(() =>
    readSession() ? "sites" : "login",
  );
  const sessionWorkId = session?.workId;

  useEffect(() => {
    if (!sessionWorkId || !online) return;
    void currentSession()
      .then((verified) => setSession(writeSession(verified)))
      .catch(() => {
        clearSession();
        setSession(null);
        setScreen("login");
      });
  }, [online, sessionWorkId]);

  return (
    <LandscapeGate>
      {!online ? (
        <div className="offline-banner" role="status">
          離線模式：已開啟的頁面與影像可繼續使用，人工量測會暫存在此裝置。
        </div>
      ) : null}
      {screen === "login" || !session ? (
        <LoginPage
          onMicrosoftLogin={async () => {
            try {
              const staff = await entraLogin();
              setSession(writeSession(staff));
              setScreen("sites");
              return true;
            } catch {
              return false;
            }
          }}
          onLogin={async (workId, password, demo) => {
            try {
              const staff = demo ? await demoLogin(workId) : await login(workId, password);
              setSession(writeSession(staff));
              setScreen("sites");
              return true;
            } catch {
              return false;
            }
          }}
        />
      ) : (
        <Suspense fallback={<div className="route-loading">正在載入地點資料…</div>}>
          <SitePickerPage
            session={session}
            onLogout={() => {
              void logout().catch(() => undefined);
              clearSession();
              setSession(null);
              setScreen("login");
            }}
          />
        </Suspense>
      )}
    </LandscapeGate>
  );
}
