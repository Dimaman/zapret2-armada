import { ButtonItem, Field, ModalRoot, PanelSection, PanelSectionRow, showModal, staticClasses, TextField, ToggleField } from "@decky/ui";
import { definePlugin } from "@decky/api";
import { useCallback, useEffect, useState } from "react";
import { rpc } from "./api";

type Settings = {
  enabled: boolean; autostart: boolean; server: string; port: number;
  sni: string; insecure: boolean; auth_set: boolean; obfs_set: boolean;
  configured: boolean;
};
type Status = { config: Settings; active: boolean; installed: boolean; version: string; error: string };

function ServerModal({initial, save, closeModal}: {
  initial: Settings; save: (value: Record<string, unknown>) => Promise<void>; closeModal?: () => void;
}) {
  const [server, setServer] = useState(initial.server);
  const [port, setPort] = useState(String(initial.port));
  const [auth, setAuth] = useState("");
  const [obfs, setObfs] = useState("");
  const [sni, setSni] = useState(initial.sni);
  const [insecure, setInsecure] = useState(initial.insecure);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return <ModalRoot onCancel={closeModal}>
    <PanelSection title="Сервер Hysteria2">
      <PanelSectionRow><TextField label="Адрес сервера" value={server} onChange={e => setServer(e.target.value.trim())} /></PanelSectionRow>
      <PanelSectionRow><TextField label="UDP-порт" value={port} mustBeNumeric onChange={e => setPort(e.target.value)} /></PanelSectionRow>
      <PanelSectionRow><TextField label={initial.auth_set ? "Пароль (пусто — сохранить)" : "Пароль"} value={auth} bIsPassword onChange={e => setAuth(e.target.value)} /></PanelSectionRow>
      <PanelSectionRow><TextField label={initial.obfs_set ? "Salamander (пусто — сохранить)" : "Salamander (если включён на сервере)"} value={obfs} bIsPassword onChange={e => setObfs(e.target.value)} /></PanelSectionRow>
      <PanelSectionRow><TextField label="TLS SNI (домен сертификата)" value={sni} onChange={e => setSni(e.target.value.trim())} /></PanelSectionRow>
      <PanelSectionRow><ToggleField label="Пропустить проверку сертификата" description="Только если сертификат сервера нельзя проверить. Снижает защиту соединения." checked={insecure} onChange={setInsecure} /></PanelSectionRow>
      {error && <PanelSectionRow><div role="alert" style={{color:"#ffb4a9",whiteSpace:"pre-wrap"}}>{error}</div></PanelSectionRow>}
      <PanelSectionRow><ButtonItem disabled={busy} onClick={async () => {
        setBusy(true); setError("");
        try {
          const data: Record<string, unknown> = {server, port: Number(port), sni, insecure};
          if (auth) data.auth = auth;
          if (obfs) data.obfs_password = obfs;
          await save(data); closeModal?.();
        } catch (e) { setError(String(e)); } finally { setBusy(false); }
      }}>Сохранить</ButtonItem></PanelSectionRow>
    </PanelSection>
  </ModalRoot>;
}

function LogsModal({value, closeModal}: {value: string; closeModal?: () => void}) {
  return <ModalRoot onCancel={closeModal}><PanelSection title="Логи VPN">
    <PanelSectionRow><textarea aria-label="Логи" readOnly value={value}
      style={{width:"100%",height:260,background:"#17212c",color:"#fff",resize:"vertical"}} /></PanelSectionRow>
    <PanelSectionRow><ButtonItem onClick={closeModal}>Закрыть</ButtonItem></PanelSectionRow>
  </PanelSection></ModalRoot>;
}

function Content() {
  const [status, setStatus] = useState<Status>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const reload = useCallback(async () => {
    try { setStatus(await rpc<Status>("status")); } catch (e) { setError(String(e)); }
  }, []);
  useEffect(() => {
    void reload();
    const timer = setInterval(() => void reload(), 5000);
    return () => clearInterval(timer);
  }, [reload]);
  const change = async (operation: string, payload: Record<string, unknown>) => {
    setBusy(true); setError("");
    try { await rpc(operation, payload); await reload(); }
    catch (e) { setError(String(e)); throw e; }
    finally { setBusy(false); }
  };
  const openSettings = () => {
    if (!status) return;
    showModal(<ServerModal initial={status.config} save={value => change("save_server",value)} />);
  };
  return <PanelSection>
    <PanelSectionRow><ToggleField
      label="Hysteria2 VPN"
      description={status?.active ? "Подключено через TUN" : status?.config.enabled ? "Соединение запускается…" : "Выключено"}
      checked={!!status?.config.enabled}
      disabled={busy || !status?.config.configured}
      onChange={enabled => { void change("set_enabled",{enabled}).catch(() => {}); }}
    /></PanelSectionRow>
    {(error || status?.error) && <PanelSectionRow><div role="alert" style={{fontSize:13,color:"#ffb4a9",overflowWrap:"anywhere"}}>{error || status?.error}</div></PanelSectionRow>}
    <PanelSectionRow><Field label="Сервер" description={status?.config.server || "Настроить Hysteria2 для включения"} onActivate={openSettings} /></PanelSectionRow>
    <PanelSectionRow><ToggleField label="Подключать после перезагрузки" checked={!!status?.config.autostart}
      disabled={busy || !status?.config.configured}
      onChange={autostart => {void change("set_autostart",{autostart}).catch(() => {});}} /></PanelSectionRow>
    <PanelSectionRow><Field label="Логи соединения" onActivate={() => {
      void rpc<{text: string}>("logs").then(r => showModal(<LogsModal value={r.text} />)).catch(e => setError(String(e)));
    }} /></PanelSectionRow>
  </PanelSection>;
}

export default definePlugin(() => ({
  name: "Hysteria2 Armada",
  titleView: <div className={staticClasses.Title}>Hysteria2 Armada</div>,
  content: <Content />,
  icon: <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L3 6v6c0 5 6 9 9 11 3-2 9-6 9-11V6Z" /></svg>,
}));
