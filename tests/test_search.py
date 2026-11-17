from dataclasses import replace

import pytest

from python_backend_guidance.catalog import load_guides, search_guides


def test_words_in_exclusions_and_example_code_do_not_admit_a_guide() -> None:
    guide = replace(
        load_guides()[0],
        content="Do not apply this guide to SQLAlchemy transaction rollback.",
    )

    assert search_guides("SQLAlchemy transaction rollback", [guide]) == []


def test_one_generic_keyword_does_not_match_a_different_capability() -> None:
    assert search_guides("CPU bound calculations", load_guides()) == []


@pytest.mark.parametrize("query", ["how can I do this", "Python async code"])
def test_noncapability_queries_have_no_results(query: str) -> None:
    assert search_guides(query, load_guides()) == []


def test_explicit_aliases_and_plural_forms_are_searchable() -> None:
    guide = replace(
        load_guides()[0],
        id="example-guide",
        title="An example",
        description="A description",
        tags=(),
        aliases=("parallel tasks",),
        content="",
    )

    assert search_guides("parallel task", [guide]) == [guide]


def test_equal_scores_are_ordered_by_id_not_input_order() -> None:
    deadline = next(
        guide for guide in load_guides() if guide.id == "apply-operation-deadline"
    )
    first = replace(deadline, id="a-guide")
    second = replace(first, id="b-guide")

    assert search_guides("workflow deadline", [second, first]) == [first, second]


def test_full_capability_outranks_repeated_partial_keywords() -> None:
    broad = replace(
        load_guides()[0],
        id="worker-pool",
        title="Worker pool",
        description="Worker pool",
        tags=("worker-pool",),
        aliases=("worker pool",),
        content="",
    )
    focused = replace(
        broad,
        id="focused",
        title="Parallel worker pool",
        description="",
        tags=(),
        aliases=(),
    )

    assert search_guides("parallel worker pool", [broad, focused])[0] == focused
