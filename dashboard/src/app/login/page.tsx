import { RadioTower } from "lucide-react";
import { Suspense } from "react";

import { LoginForm } from "@/components/LoginForm";

export default function LoginPage(): JSX.Element {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10 dashboard-grid">
      <section className="w-full max-w-md rounded-lg border border-white/80 bg-[#fffdf6]/90 p-6 shadow-panel backdrop-blur-xl">
        <div className="mb-8 text-center">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-lg bg-ink-900 text-white shadow-control">
            <RadioTower className="h-6 w-6" aria-hidden="true" />
          </div>
          <h1 className="mt-5 font-display text-3xl font-black tracking-normal text-ink-900">
            ReSync Control
          </h1>
          <p className="mt-2 text-sm leading-6 text-ink-500">
            Secure access for camera, zone, and event operations.
          </p>
        </div>
        <Suspense>
          <LoginForm />
        </Suspense>
      </section>
    </main>
  );
}
