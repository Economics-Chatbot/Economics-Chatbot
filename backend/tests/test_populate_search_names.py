from scripts.populate_search_names import extract_search_names


def test_extracts_abbreviation_and_english_name() -> None:
    definition = "가계처분가능소득(PDI; Personal Disposable Income)은 가계의 소득이다."

    assert extract_search_names("가계처분가능소득", definition) == [
        "PDI",
        "Personal Disposable Income",
    ]


def test_supports_english_then_abbreviation_and_single_alias() -> None:
    assert extract_search_names("국내총생산", "국내총생산(Gross Domestic Product; GDP)") == [
        "Gross Domestic Product",
        "GDP",
    ]
    assert extract_search_names("국내총생산", "국내총생산(GDP)는 생산의 합계다.") == ["GDP"]


def test_ignores_unrelated_parentheses_and_term_name() -> None:
    definition = "국내총생산(국내총생산; GDP)와 국내총생산(Other Term)은 별개다."

    assert extract_search_names("국내총생산", definition) == ["GDP"]


def test_uses_only_first_direct_parenthesis_and_removes_prefixes() -> None:
    definition = (
        "가산금리(또는 스프레드, spread)라고 한다. "
        "기간 가산금리(텀스프레드, term spread)라고 한다."
    )

    assert extract_search_names("가산금리", definition) == ["스프레드", "spread"]


def test_supports_all_separators_and_deduplicates() -> None:
    definition = "용어(혹은 별칭，별칭; 일명 Alias；Alias)"

    assert extract_search_names("용어", definition) == ["별칭", "Alias"]


def test_ignores_units_symbols_and_numeric_values() -> None:
    definition = "가계순저축률(%, ‰, bp, bps, ℃, ℓ, kg, m, cm, km, $, ₩, €, ¥, 100, 10%, +, -, M2)"

    assert extract_search_names("가계순저축률", definition) == ["M2"]


def test_ignores_descriptions_and_accepts_only_allowed_name_shapes() -> None:
    definition = "특정금전신탁(지정, 국내, Gross Domestic Product, GDP, spread, 2024, [])"

    assert extract_search_names("특정금전신탁", definition) == [
        "Gross Domestic Product",
        "GDP",
        "spread",
    ]


def test_extracts_title_parenthetical_and_deduplicates_body_alias() -> None:
    definition = "가상자산공개(ICO; Initial Coin Offering)는 자금을 모집한다."

    assert extract_search_names("가상자산공개(ICO)", definition) == [
        "ICO",
        "Initial Coin Offering",
    ]


def test_title_parenthetical_is_removed_from_body_lookup() -> None:
    definition = "가상자산공개(ICO; Initial Coin Offering)는 설명이다."

    assert extract_search_names("가상자산공개(다른 명칭)", definition) == [
        "다른 명칭",
        "ICO",
        "Initial Coin Offering",
    ]
