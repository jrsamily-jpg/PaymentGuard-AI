import pytest
from app.services.generation import generate_transactions
from app.services.ingestion import validate_raw, read_synthetic_csv


def test_csv_contract_and_confirmation(tmp_path):
    data = generate_transactions(100)
    path = tmp_path / "cohort.csv"
    data.to_csv(path, index=False)
    assert len(read_synthetic_csv(path, synthetic_confirmed=True)) == 100
    with pytest.raises(ValueError):
        read_synthetic_csv(path, synthetic_confirmed=False)
    data.loc[0, "ip_address"] = "8.8.8.8"
    with pytest.raises(ValueError):
        validate_raw(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", -1),
        ("amount", float("inf")),
        ("currency", "EUR"),
        ("transaction_id", "bad"),
        ("direction", "bad"),
        ("device_trusted", "false"),
        ("recipient_risk", "bad"),
        ("tx_count_24h", -1),
        ("payment_rail", "bad"),
    ],
)
def test_reject_bad_rows(field, value):
    data = generate_transactions(100)
    data[field] = data[field].astype(object)
    data.loc[0, field] = value
    with pytest.raises(ValueError):
        validate_raw(data)
