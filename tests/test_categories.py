def test_category_crud_and_reorder(auth_client):
    # 1. Create category
    res = auth_client.post("/api/categories", json={
        "name": "Anime",
        "description": "Japanese animations",
        "icon": "bi-stars",
        "is_active": True,
    })
    assert res.status_code == 201
    cat = res.get_json()["category"]
    assert cat["name"] == "Anime"
    assert cat["slug"] == "anime"

    # 2. Update category
    cat_id = cat["id"]
    update_res = auth_client.put(f"/api/categories/{cat_id}", json={
        "name": "Anime & Manga",
        "description": "Updated description",
    })
    assert update_res.status_code == 200
    assert update_res.get_json()["category"]["name"] == "Anime & Manga"

    # 3. Delete category
    del_res = auth_client.delete(f"/api/categories/{cat_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True
