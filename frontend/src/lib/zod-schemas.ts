/**
 * Zod schemas for runtime validation of API responses.
 *
 * TypeScript types are compile-time only. Zod validates data at the boundary
 * where JSON crosses from the network into our application. Each schema is
 * the single source of truth — the TypeScript type is inferred from Zod.
 *
 * Matches @sofia's Pydantic schemas in app/scoring/schemas.py exactly.
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Enum schemas
// ---------------------------------------------------------------------------

export const RiskLevelSchema = z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]);

export const DecisionSchema = z.enum(["APPROVE", "REVIEW", "DECLINE"]);

// ---------------------------------------------------------------------------
// POST /v1/risk/score — Request (used in form validation)
// ---------------------------------------------------------------------------

export const RiskScoreRequestSchema = z.object({
  transaction_id: z
    .string()
    .min(1, "Transaction ID is required")
    .max(255, "Transaction ID must be 255 characters or fewer"),
  customer_id: z
    .string()
    .min(1, "Customer ID is required")
    .max(255, "Customer ID must be 255 characters or fewer"),
  amount_cents: z
    .number()
    .int("Amount must be a whole number")
    .positive("Amount must be greater than zero"),
  currency: z
    .string()
    .regex(/^[A-Z]{3}$/, "Currency must be a 3-letter ISO 4217 code")
    .default("USD"),
  merchant_id: z
    .string()
    .min(1, "Merchant ID is required")
    .max(255, "Merchant ID must be 255 characters or fewer"),
  merchant_category: z
    .string()
    .max(255, "Merchant category must be 255 characters or fewer")
    .nullish(),
  merchant_country: z
    .string()
    .regex(/^[A-Z]{2}$/, "Country must be a 2-letter ISO 3166-1 code")
    .nullish(),
});

export type RiskScoreRequestFromSchema = z.infer<typeof RiskScoreRequestSchema>;

// ---------------------------------------------------------------------------
// POST /v1/risk/score — Response (used to validate backend responses at BFF)
// ---------------------------------------------------------------------------

export const RiskScoreResponseSchema = z.object({
  request_id: z.string(),
  transaction_id: z.string(),
  risk_score: z.number().min(0).max(1),
  risk_level: RiskLevelSchema,
  decision: DecisionSchema,
  reason_codes: z.array(z.string()),
  processing_ms: z.number().int().nonnegative(),
  engine_version: z.string(),
});

export type RiskScoreResponseFromSchema = z.infer<
  typeof RiskScoreResponseSchema
>;

// ---------------------------------------------------------------------------
// Error response (4xx / 5xx)
// ---------------------------------------------------------------------------

export const ErrorResponseSchema = z.object({
  error_code: z.string(),
  message: z.string(),
  request_id: z.string().nullish(),
  details: z.record(z.string(), z.unknown()).nullish(),
});

export type ErrorResponseFromSchema = z.infer<typeof ErrorResponseSchema>;

// ---------------------------------------------------------------------------
// GET /v1/health
// ---------------------------------------------------------------------------

export const HealthResponseSchema = z.object({
  status: z.string(),
  timestamp: z.string(),
  version: z.string(),
});

export type HealthResponseFromSchema = z.infer<typeof HealthResponseSchema>;
