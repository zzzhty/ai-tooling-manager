/** The IPC contract deliberately contains no saved secret or configuration values. */
export interface SafeError { code: string; message?: string }
export interface KeyView { id: string; name: string; mask: string; updatedUtc: string }
export interface TargetMapping {
  Id: string; Label: string; FilePath: string; Pointer: string; KeyId: string;
  BearerPrefix: boolean; ReplaceVariables: boolean; TemplateId?: string | null;
}
export interface TemplateField { pointer: string; label: string; kind: string }
export interface TemplateView { id: string; name: string; fields: TemplateField[] }
export interface TemplateCandidate extends TemplateView { schema: unknown }
export interface SnapshotView { keys: KeyView[]; targets: TargetMapping[]; templates: TemplateView[]; storageKind?: string; storageReady?: boolean; demo?: boolean }
export type UsageStatus = 'ok' | 'unknown' | 'unsupported_auth' | 'unsupported_plan_type' | 'unsupported_version' | 'expired' | 'authentication_failed' | 'rate_limited' | 'stale' | 'unavailable' | 'protocol_error';
export type GlmRegion = 'china' | 'international';
export type GlmPlanKind = 'personal' | 'team' | 'api_balance';
export interface UsageWindow { id: string; label: string; kind: string; usedPercent: number | null; remainingPercent: number | null; windowDurationMins: number | null; resetsAt: string | null; status: UsageStatus }
export interface UsageSnapshot { provider: 'codex' | 'glm'; region: 'global' | GlmRegion; authKind: 'chatgpt_oauth' | 'coding_plan_key' | 'api_key'; source: string; observedAt: string | null; checkedAt: string | null; status: UsageStatus; planName: string | null; windows: UsageWindow[]; credits: { hasCredits: boolean | null; unlimited: boolean | null; balance: number | null } | null; warnings: string[] }
export interface FieldView { label: string; pointer: string; before: string; after: string; status: string }
export interface FileView { path: string; fields: FieldView[]; encoding: string; changed: boolean; error: SafeError | null }
export interface PreviewView { id: string; files: FileView[] }
export type Outcome = 'applied' | 'skipped' | 'conflict' | 'failed' | 'appliedUnverified' | 'outcomeUnknown';
export interface FileResult {
  path: string; outcome: Outcome; message: string; code: string | null;
  backupPath: string | null; temporaryPath: string | null;
}
export interface BackupView { backupPath: string; filePath: string; createdUtc: string | null; error: SafeError | null }
export interface DesktopApi {
  snapshot(): Promise<SnapshotView>;
  saveKey(id: string | null, name: string, secret: string): Promise<string>;
  deleteKey(id: string): Promise<void>;
  saveTarget(target: TargetMapping): Promise<string>;
  deleteTarget(id: string): Promise<void>;
  preview(selected: string[]): Promise<PreviewView>;
  applyPreview(id: string, confirmed: boolean): Promise<FileResult[]>;
  cancelPreview(): Promise<void>;
  listBackups(): Promise<BackupView[]>;
  previewRollback(backupPath: string): Promise<PreviewView>;
  inferTemplate(filePath: string): Promise<TemplateCandidate>;
  saveTemplate(candidateId: string, name: string, selectedPointers: string[], schema?: string): Promise<string>;
  deleteTemplate(id: string): Promise<void>;
  pickFile(): Promise<string | null>;
  initializeStorage(confirmed: boolean): Promise<void>;
  configureCodexCli(cliPath: string, profilePath: string, confirmed: boolean): Promise<void>;
  disconnectCodexCli(): Promise<void>;
  queryCodexUsage(confirmed: boolean): Promise<UsageSnapshot>;
  queryGlmUsage(region: GlmRegion, planKind: GlmPlanKind, keyId: string | null, confirmed: boolean): Promise<UsageSnapshot>;
}

