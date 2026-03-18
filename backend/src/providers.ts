import type { ProviderName } from "./types";

export interface TextProvider {
  providerName: ProviderName;
  generateText(systemPrompt: string, userMessage: string, temperature: number): Promise<string>;
}

const providerLabels: Record<ProviderName, string> = {
  openai: "OpenAI",
  claude: "Claude",
  gemini: "Gemini",
};

async function expectJson(response: Response, providerName: ProviderName): Promise<any> {
  const raw = await response.text();
  const data = raw ? JSON.parse(raw) : {};
  if (!response.ok) {
    throw new Error(`${providerLabels[providerName]} request failed: ${raw}`);
  }
  return data;
}

function ensureText(value: string | undefined, providerName: ProviderName): string {
  const trimmed = (value ?? "").trim();
  if (!trimmed) {
    throw new Error(`${providerLabels[providerName]} returned an empty response`);
  }
  return trimmed;
}

export class OpenAIProvider implements TextProvider {
  providerName: ProviderName = "openai";

  constructor(
    private readonly apiKey: string,
    private readonly model = "gpt-4.1-mini",
  ) {}

  async generateText(systemPrompt: string, userMessage: string, temperature: number): Promise<string> {
    const response = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: this.model,
        temperature,
        input: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userMessage },
        ],
      }),
    });

    const data = await expectJson(response, this.providerName);
    if (typeof data.output_text === "string") {
      return ensureText(data.output_text, this.providerName);
    }

    const fallback = Array.isArray(data.output)
      ? data.output
          .flatMap((item: any) => item.content ?? [])
          .map((item: any) => item.text ?? "")
          .join("")
      : "";
    return ensureText(fallback, this.providerName);
  }
}

export class ClaudeProvider implements TextProvider {
  providerName: ProviderName = "claude";

  constructor(
    private readonly apiKey: string,
    private readonly model = "claude-3-5-sonnet-latest",
  ) {}

  async generateText(systemPrompt: string, userMessage: string, temperature: number): Promise<string> {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "x-api-key": this.apiKey,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: this.model,
        max_tokens: 4096,
        temperature,
        system: systemPrompt,
        messages: [{ role: "user", content: userMessage }],
      }),
    });

    const data = await expectJson(response, this.providerName);
    const text = Array.isArray(data.content)
      ? data.content.map((item: any) => item.text ?? "").join("")
      : "";
    return ensureText(text, this.providerName);
  }
}

export class GeminiProvider implements TextProvider {
  providerName: ProviderName = "gemini";

  constructor(
    private readonly apiKey: string,
    private readonly model = "gemini-2.5-flash",
  ) {}

  async generateText(systemPrompt: string, userMessage: string, temperature: number): Promise<string> {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${this.model}:generateContent?key=${encodeURIComponent(this.apiKey)}`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        systemInstruction: {
          parts: [{ text: systemPrompt }],
        },
        contents: [
          {
            role: "user",
            parts: [{ text: userMessage }],
          },
        ],
        generationConfig: {
          temperature,
        },
      }),
    });

    const data = await expectJson(response, this.providerName);
    const text = Array.isArray(data.candidates)
      ? data.candidates
          .flatMap((candidate: any) => candidate.content?.parts ?? [])
          .map((part: any) => part.text ?? "")
          .join("")
      : "";
    return ensureText(text, this.providerName);
  }
}

export function createProvider(providerName: ProviderName, apiKey: string): TextProvider {
  switch (providerName) {
    case "openai":
      return new OpenAIProvider(apiKey);
    case "claude":
      return new ClaudeProvider(apiKey);
    case "gemini":
      return new GeminiProvider(apiKey);
  }
}

export function createProviderFromEnv(): TextProvider {
  const providerName = ((process.env.AI_PLANNER_PROVIDER ?? "gemini").trim().toLowerCase()) as ProviderName;
  const envMap: Record<ProviderName, string> = {
    openai: "OPENAI_API_KEY",
    claude: "ANTHROPIC_API_KEY",
    gemini: "GEMINI_API_KEY",
  };

  if (!(providerName in envMap)) {
    throw new Error(`Unsupported AI_PLANNER_PROVIDER: ${providerName}`);
  }

  const apiKey = (process.env[envMap[providerName]] ?? "").trim();
  if (!apiKey) {
    throw new Error(`${envMap[providerName]} is not configured`);
  }

  return createProvider(providerName, apiKey);
}
