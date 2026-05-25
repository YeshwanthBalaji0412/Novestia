const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
}

export class ApiClientError extends Error {
  code: string;
  status: number;
  details: Record<string, unknown>;

  constructor(
    error: ApiErrorBody["error"],
    status: number,
  ) {
    super(error.message);
    this.code = error.code;
    this.status = status;
    this.details = error.details;
    this.name = "ApiClientError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let body: ApiErrorBody;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      throw new ApiClientError(
        {
          code: "NETWORK_ERROR",
          message: `Request failed with status ${response.status}`,
          details: {},
        },
        response.status,
      );
    }
    throw new ApiClientError(body.error, response.status);
  }

  return response.json() as Promise<T>;
}

export function createApiClient(token?: string | null) {
  return {
    get: <T>(path: string, options?: RequestInit) =>
      request<T>(path, { ...options, method: "GET" }, token),

    post: <T>(path: string, body?: unknown, options?: RequestInit) =>
      request<T>(
        path,
        {
          ...options,
          method: "POST",
          body: body ? JSON.stringify(body) : undefined,
        },
        token,
      ),

    patch: <T>(path: string, body?: unknown, options?: RequestInit) =>
      request<T>(
        path,
        {
          ...options,
          method: "PATCH",
          body: body ? JSON.stringify(body) : undefined,
        },
        token,
      ),

    delete: <T>(path: string, options?: RequestInit) =>
      request<T>(path, { ...options, method: "DELETE" }, token),
  };
}
