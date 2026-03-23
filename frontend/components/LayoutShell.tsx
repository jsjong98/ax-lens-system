"use client";

import { usePathname } from "next/navigation";
import AuthProvider from "@/components/AuthProvider";
import Navbar from "@/components/Navbar";

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";

  return (
    <AuthProvider>
      {!isLoginPage && <Navbar />}
      {isLoginPage ? (
        children
      ) : (
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </main>
      )}
    </AuthProvider>
  );
}
