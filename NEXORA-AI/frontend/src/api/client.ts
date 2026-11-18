/**
 * NEXORA ERP — REST API v1 Client with Multi-Tenant Scoping & Automatic Token Refresh
 */

const API_BASE = "/api/v1";

let accessTokenMemory: string | null = sessionStorage.getItem("nexora_access_token");
let activeOrgIdMemory: string | null = sessionStorage.getItem("nexora_org_id");
let activeBranchIdMemory: string | null = sessionStorage.getItem("nexora_branch_id");

export function setAuthSession(token: string | null, orgId?: string | null) {
  accessTokenMemory = token;
  if (token) {
    sessionStorage.setItem("nexora_access_token", token);
  } else {
    sessionStorage.removeItem("nexora_access_token");
  }
  if (orgId !== undefined) {
    activeOrgIdMemory = orgId;
    if (orgId) {
      sessionStorage.setItem("nexora_org_id", orgId);
    } else {
      sessionStorage.removeItem("nexora_org_id");
    }
  }
}

export function setActiveOrganization(orgId: string) {
  activeOrgIdMemory = orgId;
  sessionStorage.setItem("nexora_org_id", orgId);
}

export function setActiveBranch(branchId: string | null) {
  activeBranchIdMemory = branchId;
  if (branchId) {
    sessionStorage.setItem("nexora_branch_id", branchId);
  } else {
    sessionStorage.removeItem("nexora_branch_id");
  }
}

export function getActiveBranch(): string | null {
  return activeBranchIdMemory;
}

export async function apiRequest<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (accessTokenMemory) {
    headers.set("Authorization", `Bearer ${accessTokenMemory}`);
  }
  if (activeOrgIdMemory) {
    headers.set("X-Organization-ID", activeOrgIdMemory);
  }
  if (activeBranchIdMemory) {
    headers.set("X-Branch-ID", activeBranchIdMemory);
  }

  let response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (response.status === 401 && path !== "/auth/login" && path !== "/auth/refresh") {
    const refreshResp = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
    });
    if (refreshResp.ok) {
      const refreshData = await refreshResp.json();
      setAuthSession(refreshData.access_token, refreshData.user?.organization_id);
      headers.set("Authorization", `Bearer ${refreshData.access_token}`);
      response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
        credentials: "include",
      });
    }
  }

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const msg =
      data?.error?.message ||
      data?.detail ||
      `Request failed with status ${response.status}`;
    throw new Error(msg);
  }
  return data as T;
}
