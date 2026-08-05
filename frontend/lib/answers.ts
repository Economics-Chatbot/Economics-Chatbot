import type {
  Answer,
  AnswerDoneData,
  AnswerEventName,
  AnswerStreamEvent,
  AnswerStartData,
  DeltaData,
  DoneData,
  ErrorData,
  FailureData,
  SuggestionsData,
} from "../types/answers";

export type AnswerCard = {
  index: number;
  term: string;
  text: string;
  answer?: Answer;
  status: "streaming" | "completed" | "failure" | "error";
  message?: string;
};

export type StreamHandlers = {
  onAnswerStart: (data: AnswerStartData) => void;
  onDelta: (data: DeltaData) => void;
  onAnswerDone: (data: AnswerDoneData) => void;
  onSuggestions: (data: SuggestionsData) => void;
  onFailure: (data: FailureData) => void;
  onError: (data: ErrorData) => void;
  onDone: (data: DoneData) => void;
};

function parseBlock(block: string): { event: AnswerEventName; data: unknown } | null {
  let event: AnswerEventName | undefined;
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7) as AnswerEventName;
    if (line.startsWith("data: ")) data.push(line.slice(6));
  }
  if (!event || data.length === 0) return null;
  return { event, data: JSON.parse(data.join("\n")) };
}

export function parseSseBuffer(buffer: string): {
  events: AnswerStreamEvent[];
  remainder: string;
} {
  const blocks = buffer.split("\n\n");
  const remainder = blocks.pop() ?? "";
  const events = blocks
    .map(parseBlock)
    .filter((event): event is AnswerStreamEvent => event !== null);
  return { events, remainder };
}

export async function streamAnswers(
  query: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(
    `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"}/api/answers`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
      signal,
    },
  );
  if (!response.ok || !response.body) throw new Error(`답변 요청 실패 (${response.status})`);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const handle = (event: AnswerStreamEvent) => {
    switch (event.event) {
      case "answer_start": return handlers.onAnswerStart(event.data as AnswerStartData);
      case "delta": return handlers.onDelta(event.data as DeltaData);
      case "answer_done": return handlers.onAnswerDone(event.data as AnswerDoneData);
      case "suggestions": return handlers.onSuggestions(event.data as SuggestionsData);
      case "failure": return handlers.onFailure(event.data as FailureData);
      case "error": return handlers.onError(event.data as ErrorData);
      case "done": return handlers.onDone(event.data as DoneData);
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const parsed = parseSseBuffer(buffer);
    buffer = parsed.remainder;
    parsed.events.forEach(handle);
    if (done) break;
  }
  if (buffer.trim()) parseSseBuffer(`${buffer}\n\n`).events.forEach(handle);
}
