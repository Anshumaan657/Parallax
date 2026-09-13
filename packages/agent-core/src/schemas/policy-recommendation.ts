import { z } from "zod";

export const PolicyRecommendationSchema = z.object({
  recommendation: z.string(),
  rationale: z.string(),
  suggestedJiraSummary: z.string(),
  suggestedJiraDescription: z.string(),
});

export type PolicyRecommendation = z.infer<
  typeof PolicyRecommendationSchema
>;
