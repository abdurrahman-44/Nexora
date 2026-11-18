import React, { createContext, useContext, useEffect, useState } from "react";
import {
  apiRequest,
  setActiveBranch,
  setActiveOrganization,
  setAuthSession,
} from "../api/client";

export interface UserSession {
  id: string;
  email: string;
  full_name: string;
  organization_id: string;
  organization_name: string;
  currency: string;
  timezone: string;
  date_format: string;
  branch_id: string | null;
  department_id: string | null;
  mfa_enabled: boolean;
  is_super_admin: boolean;
  theme_preference: "dark" | "light";
  roles: string[];
  permissions: string[];
  organizations: Array<{
    id: string;
    name: string;
    code: string;
    currency: string;
    timezone: string;
    is_demo: boolean;
  }>;
  branches: Array<{ id: string; name: string; code: string; city: string }>;
  departments: Array<{ id: string; name: string; code: string }>;
}

interface AuthContextValue {
  user: UserSession | null;
  loading: boolean;
  theme: "dark" | "light";
  selectedBranchId: string;
  login: (email: string, password: string, totpCode?: string) => Promise<{ mfa_required?: boolean }>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  switchOrganization: (orgId: string) => Promise<void>;
  switchBranch: (branchId: string) => void;
  toggleTheme: () => Promise<void>;
  hasPermission: (perm: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSession | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedBranchId, setSelectedBranchId] = useState<string>("ALL");
  const [theme, setTheme] = useState<"dark" | "light">(
    () => (localStorage.getItem("nexora_theme") as "dark" | "light") || "dark"
  );

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "light") {
      root.classList.remove("dark");
      root.classList.add("light");
    } else {
      root.classList.remove("light");
      root.classList.add("dark");
    }
    localStorage.setItem("nexora_theme", theme);
  }, [theme]);

  const refreshProfile = async () => {
    try {
      const me = await apiRequest<UserSession>("/auth/me");
      setUser(me);
      if (me.theme_preference) {
        setTheme(me.theme_preference);
      }
    } catch {
      setUser(null);
      setAuthSession(null, null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (sessionStorage.getItem("nexora_access_token")) {
      refreshProfile();
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string, totpCode?: string) => {
    const res = await apiRequest<any>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, totp_code: totpCode || null }),
    });
    if (res.mfa_required) {
      return { mfa_required: true };
    }
    setAuthSession(res.access_token, res.user.organization_id);
    setUser(res.user);
    return { mfa_required: false };
  };

  const logout = async () => {
    try {
      await apiRequest("/auth/logout", { method: "POST" });
    } catch {
      // Ignore logout network error
    }
    setAuthSession(null, null);
    setUser(null);
  };

  const switchOrganization = async (orgId: string) => {
    setActiveOrganization(orgId);
    await refreshProfile();
  };

  const switchBranch = (branchId: string) => {
    setSelectedBranchId(branchId);
    setActiveBranch(branchId === "ALL" ? null : branchId);
  };

  const toggleTheme = async () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    if (user) {
      try {
        await apiRequest("/auth/theme", {
          method: "PUT",
          body: JSON.stringify({ theme: next }),
        });
      } catch {
        // Ignore
      }
    }
  };

  const hasPermission = (perm: string): boolean => {
    if (!user) return false;
    if (user.is_super_admin || user.permissions.includes("*")) return true;
    return user.permissions.includes(perm);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        theme,
        selectedBranchId,
        login,
        logout,
        refreshProfile,
        switchOrganization,
        switchBranch,
        toggleTheme,
        hasPermission,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
