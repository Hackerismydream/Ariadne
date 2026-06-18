export type RuntimeCapability = {
  backendName: string;
  displayName: string;
  available: boolean;
  canAssign: boolean;
  canRun: boolean;
  fallbackOnly: boolean;
};
