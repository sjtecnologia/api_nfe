from scripts.reconstruct_contract_evidence import source_inventory


def test_contract_templates_are_not_client_proof():
    sources = source_inventory()

    assert len(sources) == 3
    assert all(source["client_related"] is False for source in sources)
    assert all(source["used_as_client_proof"] is False for source in sources)
    assert all(source["source_confidence"] == "LOW" for source in sources)
