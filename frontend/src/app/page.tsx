/**
 * Root page — Server Component.
 *
 * Redirects to /dashboard. An analyst landing on / should immediately
 * see their case queue.
 */

import { redirect } from "next/navigation";

export default function HomePage(): never {
  redirect("/dashboard");
}
