import { ButtonItem, DropdownItem, Focusable, ModalRoot, PanelSection, PanelSectionRow, TextField } from "@decky/ui";
import { useRef, useState } from "react";
import type { Profile } from "../types";
import type { Labels } from "../i18n";

export function TextEditor({title, initial, labels: t, save, closeModal}: {title: string; initial: string; labels: Labels; save?: (value: string) => Promise<void>; closeModal?: () => void}) {
  const [value, setValue] = useState(initial);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLTextAreaElement>(null);
  return <ModalRoot onCancel={closeModal}>
    <PanelSection title={title}>
      <PanelSectionRow><div style={{fontSize: 14, paddingBottom: 12}}>{t.hint}</div></PanelSectionRow>
      <Focusable onActivate={() => ref.current?.focus()}>
        <textarea ref={ref} aria-label={title} value={value} readOnly={!save} onChange={e => setValue(e.target.value)}
          style={{boxSizing: "border-box", width: "100%", minHeight: 220, maxHeight: 350, resize: "vertical", background: "#18212d", color: "#fff", fontSize: 16, padding: 12}} />
      </Focusable>
      {error && <div style={{color: "#ffb4a9", whiteSpace: "pre-wrap"}}>{error}</div>}
      {save && <PanelSectionRow><ButtonItem disabled={busy} onClick={async () => {
        setBusy(true); try { await save(value); closeModal?.(); } catch(e) {setError(String(e));} finally {setBusy(false);}
      }}>{busy ? t.busy : t.save}</ButtonItem></PanelSectionRow>}
      <PanelSectionRow><ButtonItem onClick={async () => {try {await navigator.clipboard.writeText(value); setError(t.copied);} catch(e) {setError(String(e));}}}>{t.copy}</ButtonItem></PanelSectionRow>
      <PanelSectionRow><ButtonItem onClick={closeModal}>{t.close}</ButtonItem></PanelSectionRow>
    </PanelSection>
  </ModalRoot>;
}

export function ProfileEditor({initial, labels: t, save, closeModal}: {initial: Profile; labels: Labels; save: (p: Profile) => Promise<void>; closeModal?: () => void}) {
  const [p, setP] = useState(initial);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  return <ModalRoot onCancel={closeModal}><PanelSection title={t.strategy}>
    <PanelSectionRow><TextField label={t.id} value={p.id} onChange={e => setP({...p, id: e.target.value})} /></PanelSectionRow>
    <PanelSectionRow><TextField label={t.name} value={p.name} onChange={e => setP({...p, name: e.target.value})} /></PanelSectionRow>
    <PanelSectionRow><DropdownItem label={t.method} selectedOption={p.method} rgOptions={[{data:"multisplit",label:"multisplit"},{data:"multidisorder",label:"multidisorder"}]} onChange={o => setP({...p, method: o.data})} /></PanelSectionRow>
    <PanelSectionRow><TextField label={t.position} mustBeNumeric value={String(p.position)} onChange={e => setP({...p,position:Number(e.target.value)})} /></PanelSectionRow>
    <PanelSectionRow><TextField label={t.repeats} mustBeNumeric value={String(p.repeats)} onChange={e => setP({...p,repeats:Number(e.target.value)})} /></PanelSectionRow>
    {error && <div style={{color:"#ffb4a9"}}>{error}</div>}
    <PanelSectionRow><ButtonItem disabled={busy} onClick={async () => {setBusy(true);try {await save(p);closeModal?.();} catch(e) {setError(String(e));} finally {setBusy(false);}}}>{t.save}</ButtonItem></PanelSectionRow>
    <PanelSectionRow><ButtonItem onClick={closeModal}>{t.close}</ButtonItem></PanelSectionRow>
  </PanelSection></ModalRoot>;
}
