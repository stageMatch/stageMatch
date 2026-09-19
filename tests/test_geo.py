from matching import geo


def test_flatten_address():
    assert geo.flattenAddress("Via Roma ££ 1 ££ 24100 ££ Bergamo") == "Via Roma, 1, 24100, Bergamo"
    assert geo.flattenAddress("  ££  ") is None
    assert geo.flattenAddress(None) is None
    assert geo.flattenAddress("") is None


def test_parse_route_summary():
    data = {"features": [{"properties": {"summary": {"distance": 2500, "duration": 600}}}]}

    assert geo.parseRouteSummary(data) == (2.5, 10.0)
    assert geo.parseRouteSummary({"error": "x"}) == (None, None)
    assert geo.parseRouteSummary({"features": []}) == (None, None)
    assert geo.parseRouteSummary({"features": [{"properties": {"summary": {"distance": 1000}}}]}) == (1.0, None)
