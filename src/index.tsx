import { ButtonItem, Field, ModalRoot, PanelSection, PanelSectionRow, showModal, staticClasses, TextField, ToggleField } from "@decky/ui";
import { definePlugin } from "@decky/api";
import { useCallback, useEffect, useState } from "react";
import { rpc } from "./api";

type VPNSettings = {enabled: boolean; autostart: boolean; server: string; port: number; sni: string; insecure: boolean; auth_set: boolean; obfs_set: boolean; configured: boolean};
type VPNStatus = {config: VPNSettings; active: boolean; installed: boolean; error: string};
type DPIStatus = {enabled: boolean; profile: "sni" | "strong"; active: boolean; error: string};
type Status = {vpn: VPNStatus; dpi: DPIStatus; version: string};

function ServerModal({initial, save, closeModal}: {initial: VPNSettings; save: (value: Record<string, unknown>) => Promise<void>; closeModal?: () => void}) {
  const [server, setServer] = useState(initial.server);
  const [port, setPort] = useState(String(initial.port));
  const [auth, setAuth] = useState("");
  const [obfs, setObfs] = useState("");
  const [sni, setSni] = useState(initial.sni);
  const [insecure, setInsecure] = useState(initial.insecure);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return <ModalRoot onCancel={closeModal}><PanelSection title="Сервер Hysteria2">
    <PanelSectionRow><TextField label="Адрес сервера" value={server} onChange={e => setServer(e.target.value.trim())} /></PanelSectionRow>
    <PanelSectionRow><TextField label="UDP-порт" value={port} mustBeNumeric onChange={e => setPort(e.target.value)} /></PanelSectionRow>
    <PanelSectionRow><TextField label={initial.auth_set ? "Пароль (пусто — сохранить)" : "Пароль"} value={auth} bIsPassword onChange={e => setAuth(e.target.value)} /></PanelSectionRow>
    <PanelSectionRow><TextField label={initial.obfs_set ? "Salamander (пусто — сохранить)" : "Salamander (если включён на сервере)"} value={obfs} bIsPassword onChange={e => setObfs(e.target.value)} /></PanelSectionRow>
    <PanelSectionRow><TextField label="TLS SNI" value={sni} onChange={e => setSni(e.target.value.trim())} /></PanelSectionRow>
    <PanelSectionRow><ToggleField label="Пропустить проверку сертификата" description="Снижает защиту соединения" checked={insecure} onChange={setInsecure} /></PanelSectionRow>
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
  </PanelSection></ModalRoot>;
}

function ProfileModal({selected, save, closeModal}: {selected: DPIStatus["profile"]; save: (profile: DPIStatus["profile"]) => Promise<void>; closeModal?: () => void}) {
  const [error, setError] = useState("");
  const choose = (profile: DPIStatus["profile"]) => { void save(profile).then(() => closeModal?.()).catch(e => setError(String(e))); };
  return <ModalRoot onCancel={closeModal}><PanelSection title="Обход DPI">
    <PanelSectionRow><ButtonItem onClick={() => choose("sni")}>SNI split + 2 fake{selected === "sni" ? " ✓" : ""}</ButtonItem></PanelSectionRow>
    <PanelSectionRow><ButtonItem onClick={() => choose("strong")}>Усиленный TLS split{selected === "strong" ? " ✓" : ""}</ButtonItem></PanelSectionRow>
    <PanelSectionRow><Field label="UDP игр" description="Прямое подключение, без фейковых пакетов" /></PanelSectionRow>
    {error && <PanelSectionRow><div role="alert">{error}</div></PanelSectionRow>}
  </PanelSection></ModalRoot>;
}

function LogsModal({value, closeModal}: {value: string; closeModal?: () => void}) {
  return <ModalRoot onCancel={closeModal}><PanelSection title="Логи соединения">
    <PanelSectionRow><textarea aria-label="Логи" readOnly value={value} style={{width:"100%",height:260,background:"#17212c",color:"#fff"}} /></PanelSectionRow>
    <PanelSectionRow><ButtonItem onClick={closeModal}>Закрыть</ButtonItem></PanelSectionRow>
  </PanelSection></ModalRoot>;
}

function Content() {
  const [status, setStatus] = useState<Status>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const reload = useCallback(async () => { try { setStatus(await rpc<Status>("status")); } catch (e) { setError(String(e)); } }, []);
  useEffect(() => { void reload(); const timer = setInterval(() => void reload(), 5000); return () => clearInterval(timer); }, [reload]);
  const change = async (operation: string, payload: Record<string, unknown>) => {
    setBusy(true); setError("");
    try { setStatus(await rpc<Status>(operation, payload)); }
    catch (e) { setError(String(e)); throw e; }
    finally { setBusy(false); }
  };
  const openLogs = (operation: string) => {
    void rpc<{text: string}>(operation).then(r => showModal(<LogsModal value={r.text} />)).catch(e => setError(String(e)));
  };
  return <PanelSection>
    <PanelSectionRow><ToggleField label="Локальный обход DPI" checked={!!status?.dpi.enabled}
      description={status?.dpi.active ? "SpoofDPI: прямой маршрут" : status?.dpi.enabled ? "Нет соединения — откройте логи" : "Выключено"}
      disabled={busy || !status}
      onChange={enabled => { void change("set_mode", {mode: enabled ? "dpi" : "off"}).catch(() => {}); }} /></PanelSectionRow>
    <PanelSectionRow><ToggleField label="Hysteria2 VPN" checked={!!status?.vpn.config.enabled}
      description={status?.vpn.active ? "Весь TCP/UDP через VPS" : status?.vpn.config.enabled ? "Нет соединения — откройте логи" : "Выключен"}
      disabled={busy || !status?.vpn.config.configured}
      onChange={enabled => { void change("set_mode", {mode: enabled ? "vpn" : "off"}).catch(() => {}); }} /></PanelSectionRow>
    {(error || status?.dpi.error || status?.vpn.error) && <PanelSectionRow><div role="alert" style={{fontSize:13,color:"#ffb4a9",overflowWrap:"anywhere"}}>{error || status?.dpi.error || status?.vpn.error}</div></PanelSectionRow>}
    <PanelSectionRow><Field label="Стратегия DPI" description={status?.dpi.profile === "strong" ? "Усиленный TLS split" : "SNI split + 2 fake"}
      onActivate={() => status && showModal(<ProfileModal selected={status.dpi.profile} save={profile => change("dpi_set_profile", {profile})} />)} /></PanelSectionRow>
    <PanelSectionRow><Field label="Сервер VPN" description={status?.vpn.config.server || "Настроить Hysteria2"}
      onActivate={() => status && showModal(<ServerModal initial={status.vpn.config} save={value => change("save_server", value)} />)} /></PanelSectionRow>
    <PanelSectionRow><ToggleField label="VPN после перезагрузки" checked={!!status?.vpn.config.autostart}
      disabled={busy || !status?.vpn.config.configured}
      onChange={autostart => { void change("set_autostart", {autostart}).catch(() => {}); }} /></PanelSectionRow>
    <PanelSectionRow><Field label="Логи DPI" onActivate={() => openLogs("dpi_logs")} /></PanelSectionRow>
    <PanelSectionRow><Field label="Логи VPN" onActivate={() => openLogs("logs")} /></PanelSectionRow>
  </PanelSection>;
}

export default definePlugin(() => ({
  name: "SpoofDPI Armada",
  titleView: <div className={staticClasses.Title}>SpoofDPI Armada</div>,
  content: <Content />,
  icon: <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L3 6v6c0 5 6 9 9 11 3-2 9-6 9-11V6Z" /></svg>,
}));
