from hypothesis import given
from hypothesis import strategies as st

from erdos.core.models import ProblemRecord, ProblemStatus


@given(
    id=st.integers(min_value=1, max_value=10000),
    title=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
    prize=st.integers(min_value=0, max_value=1_000_000),
)
def test_problem_record_roundtrips(id: int, title: str, prize: int) -> None:
    """Any valid ProblemRecord should roundtrip through JSON."""
    problem = ProblemRecord(
        id=id,
        title=title,
        statement="Test statement",
        status=ProblemStatus.OPEN,
        prize=prize,
    )
    json_str = problem.model_dump_json()
    restored = ProblemRecord.model_validate_json(json_str)
    assert restored == problem
