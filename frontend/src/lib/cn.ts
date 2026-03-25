/**
 * Utility for merging Tailwind CSS classes with proper conflict resolution.
 * Uses clsx for conditional classes + tailwind-merge for deduplication.
 */

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
