"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";
import { AuthUser, getMe, apiLogout } from "@/lib/api";

interface AuthContextType {
  user: AuthUser | null;
  loading: boolean;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  logout: async () => {},
  refresh: async () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const refresh = async () => {
    const me = await getMe();
    setUser(me);
    setLoading(false);
  };

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (loading) return;
    // 로그인 안 되어있으면 로그인 페이지로 이동
    if (!user && pathname !== "/login") {
      router.replace("/login");
    }
    // 로그인 되어있는데 로그인 페이지면 메인으로
    if (user && pathname === "/login") {
      router.replace("/tasks");
    }
  }, [user, loading, pathname, router]);

  const handleLogout = async () => {
    await apiLogout();
    setUser(null);
    router.replace("/login");
  };

  // 로그인 페이지는 보호하지 않음
  if (pathname === "/login") {
    return (
      <AuthContext.Provider value={{ user, loading, logout: handleLogout, refresh }}>
        {children}
      </AuthContext.Provider>
    );
  }

  // 로딩 중
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-500">로딩 중...</div>
      </div>
    );
  }

  // 로그인 안됨 → 리다이렉트 대기
  if (!user) {
    return null;
  }

  return (
    <AuthContext.Provider value={{ user, loading, logout: handleLogout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}
