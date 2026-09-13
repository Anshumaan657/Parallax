export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <main className="grid min-h-dvh place-items-center bg-background px-4 py-10">{children}</main>;
}
