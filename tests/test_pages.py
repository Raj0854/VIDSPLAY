def test_page_and_section_builder(auth_client, client):
    # 1. Create page
    page_res = auth_client.post("/api/pages", json={
        "title": "Anime Hub",
        "slug": "anime",
        "meta_description": "Stream the best anime",
        "is_published": True,
        "add_to_navbar": True,
    })
    assert page_res.status_code == 201
    page = page_res.get_json()["page"]
    assert page["slug"] == "anime"
    page_id = page["id"]

    # 2. Add section to page
    sec_res = auth_client.post(f"/api/pages/{page_id}/sections", json={
        "section_type": "hero",
        "title": "Welcome to Anime Hub",
        "subtitle": "Discover shonen, action and drama",
        "config": {"align": "center"},
        "is_visible": True,
    })
    assert sec_res.status_code == 201
    sec = sec_res.get_json()["section"]
    assert sec["section_type"] == "hero"

    # 3. Fetch page by slug from public API
    pub_page_res = client.get("/api/pages/anime")
    assert pub_page_res.status_code == 200
    fetched_page = pub_page_res.get_json()["page"]
    assert len(fetched_page["sections"]) >= 1

    # 4. Duplicate page
    dup_res = auth_client.post(f"/api/pages/{page_id}/duplicate")
    assert dup_res.status_code == 201
    dup_page = dup_res.get_json()["page"]
    assert "Copy" in dup_page["title"]

    # 5. Delete original page
    del_res = auth_client.delete(f"/api/pages/{page_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True
