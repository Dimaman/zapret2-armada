export interface Profile { id: string; name: string; method: "multisplit" | "multidisorder"; position: number; repeats: number }
export interface Config { enabled: boolean; autostart: boolean; udp: boolean; language: "ru" | "en"; active: string; profiles: Profile[]; domains: string[]; exclude: string[]; test_domains: string[] }
export interface TuneResult { baseline: unknown; candidates: {profile: string; score?: number; error?: string}[]; suggestion: string | null; error: string }
export interface Status { config: Config; installed: boolean; service_active: boolean; engine_running: boolean; plugin_version: string; engine_version: string; os: string; error: string; tuning: boolean; progress: string; tune_result: TuneResult | null }
