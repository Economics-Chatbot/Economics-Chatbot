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
  failure_message: string | null;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function askEconomyMate(query: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error("서버 응답에 실패했습니다.");
  }

  return response.json();
}

