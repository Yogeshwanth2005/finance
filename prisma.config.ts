import "dotenv/config";
import { defineConfig, env } from "prisma/config";

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: {
    path: "prisma/migrations",
    seed: "tsx prisma/seed.ts",
  },
  datasource: {
    // Direct (non-pooled) connection: `prisma migrate`/introspection need
    // DDL + shadow-database support that Supabase's pooler doesn't provide.
    // The running app connects separately via DATABASE_URL (src/lib/db.ts).
    url: env("DIRECT_URL"),
  },
});
