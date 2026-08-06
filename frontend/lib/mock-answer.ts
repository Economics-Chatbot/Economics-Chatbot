import type { RetrievedTerm } from "@/types/answers";

export const MOCK_ANSWER: RetrievedTerm = {
  term_id: 1,
  term_name: "인플레이션",
  official_definition: "상품과 서비스의 전반적인 가격 수준이 지속해서 오르는 현상입니다.",
  related_terms: ["물가", "구매력", "디플레이션"],
};

export const MOCK_ANSWER_CHUNKS = [
  "인플레이션은 상품과 서비스의 가격이 전반적으로 계속 오르는 현상이에요. ",
  "같은 돈으로 살 수 있는 물건의 양이 줄어들기 때문에 돈의 실질 가치가 낮아집니다. ",
  "예를 들어 예전에는 1,000원이던 간식이 1,200원이 되는 경우를 생각할 수 있어요.",
];
