import { cookies } from "next/headers";
import type { User } from "@prisma/client";
import { prisma } from "./db";

const COOKIE_NAME = "fin_demo_user_id";
const COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

/**
 * Single auto-provisioned "demo user" per browser, identified by a
 * long-lived httpOnly cookie — no login UI (see design spec, Section 1).
 *
 * Server Components can read cookies but not set them (Next.js
 * restriction: only Server Actions / Route Handlers may call
 * `cookies().set()`). Called from the dashboard (a Server Component)
 * with no cookie yet, this still creates the row (needed to query, even
 * though it'll have no data) but silently can't persist the cookie — the
 * dashboard immediately redirects to /onboarding in that case anyway.
 * The wizard's submit route (a Route Handler) is where the cookie
 * actually gets set for real.
 */
export async function getOrCreateDemoUser(): Promise<User> {
  const cookieStore = await cookies();
  const existingId = cookieStore.get(COOKIE_NAME)?.value;

  if (existingId) {
    const existing = await prisma.user.findUnique({ where: { id: existingId } });
    if (existing) return existing;
  }

  const created = await prisma.user.create({
    data: { email: `demo-${crypto.randomUUID()}@fin.local` },
  });

  try {
    cookieStore.set(COOKIE_NAME, created.id, {
      httpOnly: true,
      maxAge: COOKIE_MAX_AGE_SECONDS,
      sameSite: "lax",
      path: "/",
    });
  } catch {
    // Not callable from a Server Component — see doc comment above.
  }

  return created;
}
