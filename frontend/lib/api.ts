export type RetrievedTerm = {
  term_name: string;
  official_definition: string;
  source_name: string;
  source_page: number | null;
  related_terms: string[];
  similarity: number | null;
};

export type ChatAnswer = {
  term: string;
  one_line: string;
  easy_explanation: string;
  example: string;
  related_terms: string[];
  source_name: string;
  source_page: number | null;
};

export type ChatResponse = {
  query: string;
  answer: ChatAnswer | null;
  retrieved_terms: RetrievedTerm[];
  failure_message: string | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

async function parseResponse(response: Response): Promise<ChatResponse> {
  if (!response.ok) {
    throw new Error("서버 응답에 실패했습니다.");
  }

  return response.json();
}

export async function askQuestion(query: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/questions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
  });

  return parseResponse(response);
}

export async function getTerm(term: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/terms/${encodeURIComponent(term)}`);

  return parseResponse(response);
}
