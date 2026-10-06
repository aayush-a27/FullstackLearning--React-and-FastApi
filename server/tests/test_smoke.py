async def test_register_and_me(auth_client):
    response = await auth_client.get("/users/me")
    assert response.status_code == 200
    assert response.json()["email"] == auth_client.user["email"]
