import server


def test_routejson_validation_errors():
    client = server.app.test_client()

    assert client.get("/routejson").status_code == 400
    assert client.get("/routejson?startaddress=A&endaddress=B&routemode=../x").status_code == 400


def test_routejson_requires_ors_key(monkeypatch):
    monkeypatch.setattr(server, "ors_api_key", None)

    assert server.app.test_client().get("/routejson?startaddress=A&endaddress=B").status_code == 503


def test_photon_validates_params():
    client = server.app.test_client()

    assert client.get("/photon").status_code == 400
    assert client.get("/photon?q=Ber&limit=abc").status_code == 400
    assert client.get("/photon?q=Ber&lat=x&lon=y").status_code == 400
