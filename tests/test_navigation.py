def test_navigation_crud(auth_client, client):
    # 1. Create navbar tab
    create_res = auth_client.post("/api/navigation", json={
        "label": "Trending Hub",
        "target_type": "custom",
        "target_url": "/trending",
        "visibility": "all",
        "is_active": True,
    })
    assert create_res.status_code == 201
    item = create_res.get_json()["item"]
    assert item["label"] == "Trending Hub"
    assert item["resolved_url"] == "/trending"
    item_id = item["id"]

    # 2. Public API receives it
    pub_res = client.get("/api/navigation")
    items = pub_res.get_json()["items"]
    assert any(i["id"] == item_id for i in items)

    # 3. Update tab
    update_res = auth_client.put(f"/api/navigation/{item_id}", json={
        "label": "Top Trending",
        "visibility": "desktop",
    })
    assert update_res.status_code == 200
    assert update_res.get_json()["item"]["label"] == "Top Trending"
    assert update_res.get_json()["item"]["visibility"] == "desktop"

    # 4. Delete tab
    del_res = auth_client.delete(f"/api/navigation/{item_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True


def test_public_page_uses_one_category_navigation_bar(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.get_data(as_text=True).count("<nav") == 1
