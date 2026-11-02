import { ButtonItem, ConfirmModal, DropdownItem, PanelSection, PanelSectionRow, showModal, staticClasses, ToggleField } from "@decky/ui";
import { definePlugin } from "@decky/api";
import { useCallback, useEffect, useState } from "react";
import { rpc } from "./api";
import { ProfileEditor, TextEditor } from "./components/Editors";
import { text } from "./i18n";
import type { Config, Profile, Status } from "./types";

function Content() {
  const [s, setS] = useState<Status>();
  const [page, setPage] = useState("dashboard");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [connection, setConnection] = useState("");
  const t = text[s?.config.language || "ru"];
  const reload = useCallback(async () => {try {setS(await rpc<Status>("status"));} catch(e) {setError(String(e));}}, []);
  useEffect(() => {void reload(); const id = setInterval(() => void reload(), 10000); return () => clearInterval(id);}, [reload]);
  const act = async <T,>(op: string, payload: Record<string, unknown> = {}): Promise<T> => {
    setBusy(true); setError("");
    try {const r = await rpc<T>(op,payload); await reload(); return r;}
    catch(e) {setError(String(e)); throw e;}
    finally {setBusy(false);}
  };
  const fire = (op: string, payload: Record<string, unknown> = {}) => {void act(op,payload).catch(() => {});};
  const configure = (p: Partial<Config>) => fire("configure",p);
  const confirm = (title: string, description: string, fn: () => void) => showModal(<ConfirmModal strTitle={title} strDescription={description} onOK={fn} />);
  const viewText = (title: string, value: unknown) => showModal(<TextEditor title={title} initial={typeof value === "string" ? value : JSON.stringify(value,null,2)} labels={t} />);
  const editDomains = (key: "domains" | "exclude") => {
    if (!s) return;
    showModal(<TextEditor title={key === "domains" ? t.include : t.exclude} initial={s.config[key].join("\n")} labels={t} save={async value => {
      await act("save_domains",{domains:s.config.domains.join("\n"),exclude:s.config.exclude.join("\n"),[key]:value});
    }} />);
  };
  const editProfile = (p: Profile) => showModal(<ProfileEditor initial={{...p}} labels={t} save={async value => {await act("save_profile",{...value});}} />);
  const disabled = busy || !!s?.tuning;
  const button = (label: string, fn: () => void, block = disabled) => <PanelSectionRow><ButtonItem layout="below" disabled={block} onClick={fn}>{label}</ButtonItem></PanelSectionRow>;
  return <>
    <PanelSection>
      <PanelSectionRow><DropdownItem label={t.section} selectedOption={page} rgOptions={(["dashboard","strategies","domains","diagnostics","settings"] as const).map(data => ({data,label:t[data]}))} onChange={o => setPage(o.data)} /></PanelSectionRow>
      {(error || s?.error) && <PanelSectionRow><div role="alert" style={{fontSize:14,color:"#ffb4a9",overflowWrap:"anywhere",whiteSpace:"pre-wrap"}}>{error || s?.error}</div></PanelSectionRow>}
      {!s && button(t.refresh,() => void reload(),false)}
    </PanelSection>
    {s && page === "dashboard" && <PanelSection title="Zapret2 Armada">
      <PanelSectionRow><ToggleField label={t.enable} checked={s.config.enabled} disabled={disabled} onChange={enabled => configure({enabled})} /></PanelSectionRow>
      <PanelSectionRow><div style={{fontSize:15,lineHeight:1.6}}>
        <b>nfqws2: {s.engine_running ? t.active : t.inactive}</b><br />
        systemd: {s.service_active ? t.active : t.inactive}<br />
        {t.strategy}: {s.config.profiles.find(p => p.id === s.config.active)?.name}<br />
        {connection || t.connection}<br />
        Plugin {s.plugin_version}<br />{s.engine_version}<br />
        {s.os.split("\n").find(v => v.startsWith("PRETTY_NAME="))?.replace('PRETTY_NAME=', '').replace(/"/g,'')}
      </div></PanelSectionRow>
      {button(t.refresh,() => void reload(),busy)}
      {button(t.restart,() => fire("restart"))}
      {button(t.diagnose,() => setPage("diagnostics"))}
      <PanelSectionRow><div style={{fontSize:13,color:"#d5c394"}}>{t.warning}</div></PanelSectionRow>
    </PanelSection>}
    {s && page === "strategies" && <PanelSection title={t.strategies}>
      <PanelSectionRow><DropdownItem label={t.strategy} disabled={disabled} selectedOption={s.config.active} rgOptions={s.config.profiles.map(p => ({data:p.id,label:p.name}))} onChange={o => configure({active:o.data})} /></PanelSectionRow>
      <PanelSectionRow><ToggleField label={t.udp} description={t.udpInfo} checked={s.config.udp} disabled={disabled} onChange={udp => configure({udp})} /></PanelSectionRow>
      {button(t.edit,() => editProfile(s.config.profiles.find(p => p.id === s.config.active)!))}
      {button(t.newProfile,() => editProfile({id:`custom-${Date.now()}`,name:"Custom",method:"multisplit",position:1,repeats:1}))}
      {button(t.importProfile,() => showModal(<TextEditor title={t.importProfile} initial={JSON.stringify(s.config.profiles[0],null,2)} labels={t} save={async value => {await act("save_profile",JSON.parse(value));}} />))}
      {button(t.restore,() => fire("restore"))}
      {!s.tuning && button(t.tune,() => confirm(t.tune,t.tuneInfo,() => fire("start_tune")))}
      {s.tuning && <><PanelSectionRow><div>{s.progress || t.busy}</div></PanelSectionRow>{button(t.cancel,() => fire("cancel_tune"),busy)}</>}
      {s.tune_result && <>
        {button("JSON: " + t.tune,() => viewText(t.tune,s.tune_result),busy)}
        {s.tune_result.suggestion && !s.tune_result.error && button(`${t.apply}: ${s.tune_result.suggestion}`,() => confirm(t.apply,s.tune_result!.suggestion!,() => fire("apply_suggestion")))}
      </>}
    </PanelSection>}
    {s && page === "domains" && <PanelSection title={t.domains}>
      {button(`${t.include} (${s.config.domains.length})`,() => editDomains("domains"))}
      {button(`${t.exclude} (${s.config.exclude.length})`,() => editDomains("exclude"))}
      {button(t.testDomains,() => showModal(<TextEditor title={t.testDomains} initial={s.config.test_domains.join("\n")} labels={t} save={async value => {await act("configure",{test_domains:value.split(/\s+/).filter(Boolean)});}} />))}
      {button(t.export,() => {void act("export").then(r => viewText(t.export,r)).catch(() => {});})}
      {button(t.update,() => confirm(t.update,t.updateInfo,() => fire("update_domains")))}
      {button(t.seed,() => fire("restore_seed"))}
    </PanelSection>}
    {s && page === "diagnostics" && <PanelSection title={t.diagnostics}>
      {button(t.diagnose,() => {void act<{network:{control:{https:boolean};targets:{https:boolean}[]}}>("diagnose").then(r => {
        setConnection(`HTTPS: ${r.network.targets.filter(v => v.https).length}/${r.network.targets.length}; Internet: ${r.network.control.https ? "OK" : "ERROR"}`);
        viewText(t.diagnostics,r);
      }).catch(() => {});})}
      {button(t.logs,() => {void act<{text:string}>("logs").then(r => viewText(t.logs,r.text)).catch(() => {});})}
      {button(t.install,() => fire("install"))}
      {button(t.recover,() => confirm(t.recover,"inet zapret2_armada",() => fire("recover_firewall")))}
    </PanelSection>}
    {s && page === "settings" && <PanelSection title={t.settings}>
      <PanelSectionRow><ToggleField label={t.auto} checked={s.config.autostart} disabled={disabled} onChange={autostart => configure({autostart})} /></PanelSectionRow>
      <PanelSectionRow><DropdownItem label={t.language} selectedOption={s.config.language} rgOptions={[{data:"ru",label:"Русский"},{data:"en",label:"English"}]} onChange={o => configure({language:o.data})} /></PanelSectionRow>
      {button(t.reset,() => confirm(t.reset,t.warning,() => fire("reset")))}
    </PanelSection>}
  </>;
}

export default definePlugin(() => ({name:"Zapret2 Armada",titleView:<div className={staticClasses.Title}>Zapret2 Armada</div>,content:<Content />,icon:<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L3 6v6c0 5 6 9 9 11 3-2 9-6 9-11V6Z" /></svg>}));
