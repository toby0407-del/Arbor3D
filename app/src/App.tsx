import { useState } from "react";
import { authenticate } from "./data/staff";
import {
  clearSession,
  readSession,
  writeSession,
  type Session,
} from "./lib/session";
import { LandscapeGate } from "./components/LandscapeGate";
import { useOnlineStatus } from "./hooks/useOnlineStatus";
import { LoginPage } from "./pages/LoginPage";
import { SitePickerPage } from "./pages/SitePickerPage";

type Screen = "login" | "sites";

export default function App() {
  const online = useOnlineStatus();
  const [session, setSession] = useState<Session | null>(() => readSession());
  const [screen, setScreen] = useState<Screen>(() =>
    readSession() ? "sites" : "login",
  );

  return (
    <LandscapeGate>
      {!online ? (
        <div className="offline-banner" role="status">
          離線模式：已開啟的頁面與影像可繼續使用，人工量測會暫存在此裝置。
        </div>
      ) : null}
      {screen === "login" || !session ? (
        <LoginPage
          onLogin={(workId, password) => {
            const staff = authenticate(workId, password);
            if (!staff) return false;
            setSession(writeSession(staff));
            setScreen("sites");
            return true;
          }}
        />
      ) : (
        <SitePickerPage
          session={session}
          onLogout={() => {
            clearSession();
            setSession(null);
            setScreen("login");
          }}
        />
      )}
    </LandscapeGate>
  );
}
