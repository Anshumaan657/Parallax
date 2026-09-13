import type { AgentStateType } from "../graph/state.js";
import { HumanMessage, SystemMessage } from "@langchain/core/messages";
import { NotionRestTool } from "../tools/notion.js";
import { GeminiGateway } from "../reasoning/gemini-gateway.js";
import {
  PolicyRecommendationSchema,
  type PolicyRecommendation,
} from "../schemas/policy-recommendation.js";

const notion = new NotionRestTool();
const model = new GeminiGateway();

export async function analyzeNotionDocument(
  state: AgentStateType,
): Promise<Partial<AgentStateType>> {
  try {
    const pageId = notion.extractPageId(
      state.mission,
    );

    if (!pageId) {
      return {
        currentStep: "analyze_notion_document",
        errors: [
          "No Notion page ID or Notion URL was found in the mission.",
        ],
      };
    }

    const document =
      await notion.getPageContent(pageId);

    const response = await model.invoke([
      new SystemMessage(
        `You are the reasoning layer of Parallax.

Read the provided Notion policy document and determine the single best operational action that a product/project team should take based only on the document.

Return ONLY valid JSON matching this structure:
{
  "recommendation": "single best action",
  "rationale": "why this action is supported by the document",
  "suggestedJiraSummary": "concise Jira task title",
  "suggestedJiraDescription": "detailed Jira task description"
}

Do not invent facts that are not supported by the document.`,
      ),
      new HumanMessage(
        `Mission:
${state.mission}

Notion document:
${document.title}

${document.content}`,
      ),
    ]);

    const jsonStart = response.indexOf("{");
    const jsonEnd = response.lastIndexOf("}");

    if (
      jsonStart === -1 ||
      jsonEnd === -1 ||
      jsonEnd <= jsonStart
    ) {
      throw new Error(
        "Gemini did not return a JSON object.",
      );
    }

    const cleanedResponse = response.slice(
      jsonStart,
      jsonEnd + 1,
    );

    const parsed: PolicyRecommendation =
      PolicyRecommendationSchema.parse(
        JSON.parse(cleanedResponse),
      );

    return {
      currentStep: "analyze_notion_document",
      evidence: [document],
      policyRecommendation: parsed,
      slackSummary:
        `Recommended action: ${parsed.recommendation}\n\n` +
        `Rationale: ${parsed.rationale}`,
    };
  } catch (error) {
    return {
      currentStep: "analyze_notion_document",
      errors: [
        `Failed to analyze Notion document: ${
          error instanceof Error
            ? error.message
            : String(error)
        }`,
      ],
    };
  }
}