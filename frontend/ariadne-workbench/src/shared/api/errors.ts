export class AriadneApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly body: string,
  ) {
    super(message);
    this.name = "AriadneApiError";
  }
}

export function apiErrorCode(error: unknown) {
  if (!(error instanceof AriadneApiError)) return undefined;
  try {
    const body = JSON.parse(error.body) as { error?: { code?: string } };
    return body.error?.code;
  } catch {
    return undefined;
  }
}
