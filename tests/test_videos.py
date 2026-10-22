import io


def test_add_video_via_youtube_url(auth_client):
    res = auth_client.post("/api/videos", json={
        "title": "Inception Trailer HD",
        "source_type": "youtube",
        "source_url": "https://www.youtube.com/watch?v=YoHD9XEInc0",
        "description": "Christopher Nolan masterpiece",
        "category_id": 1,
        "is_published": True,
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    video = data["video"]
    assert video["title"] == "Inception Trailer HD"
    assert video["embed_code"] == "YoHD9XEInc0"
    assert "https://img.youtube.com/vi/YoHD9XEInc0" in video["thumbnail_url"]


def test_validate_youtube_url(auth_client):
    res = auth_client.post("/api/videos/validate-url", json={
        "url": "https://youtu.be/dQw4w9WgXcQ"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["valid"] is True
    assert data["embed_code"] == "dQw4w9WgXcQ"
    assert data["source_type"] == "youtube"


def test_video_playback_url_uses_youtube_embed_code(app):
    from models import Video

    with app.app_context():
        video = Video(
            title="YouTube playback",
            slug="youtube-playback",
            source_type="youtube",
            embed_code="dQw4w9WgXcQ",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )

        assert video.get_playback_url() == "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert video.to_dict()["embed_code"] == "dQw4w9WgXcQ"


def test_validate_invalid_url(auth_client):
    res = auth_client.post("/api/videos/validate-url", json={
        "url": "javascript:alert(1)"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["valid"] is False


def test_public_vs_draft_visibility(auth_client, client):
    # Create draft video
    res = auth_client.post("/api/videos", json={
        "title": "Secret Unreleased Show",
        "source_type": "youtube",
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "is_published": False,
    })
    assert res.status_code == 201
    draft_id = res.get_json()["video"]["id"]

    # Public client cannot see it in catalogue
    pub_res = client.get("/api/videos")
    videos = pub_res.get_json()["videos"]
    assert all(v["id"] != draft_id for v in videos)

    # Public client cannot view it directly
    direct_res = client.get(f"/api/videos/{draft_id}")
    assert direct_res.status_code == 404

    # Admin client CAN see it with include_drafts=1
    admin_res = auth_client.get("/api/videos?include_drafts=1")
    admin_videos = admin_res.get_json()["videos"]
    assert any(v["id"] == draft_id for v in admin_videos)


def test_edit_video(auth_client):
    # Create video
    create_res = auth_client.post("/api/videos", json={
        "title": "Initial Video Title",
        "source_type": "youtube",
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "is_published": True,
    })
    video_id = create_res.get_json()["video"]["id"]

    # Edit video
    edit_res = auth_client.put(f"/api/videos/{video_id}", json={
        "title": "Updated Brand New Title",
        "description": "Updated description content",
        "is_featured": True,
    })
    assert edit_res.status_code == 200
    updated = edit_res.get_json()["video"]
    assert updated["title"] == "Updated Brand New Title"
    assert updated["is_featured"] is True


def test_edit_video_can_replace_source_url(auth_client):
    create_res = auth_client.post("/api/videos", json={
        "title": "Video with replaceable source",
        "source_type": "youtube",
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "is_published": True,
    })
    video_id = create_res.get_json()["video"]["id"]
    assert create_res.get_json()["video"]["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    edit_res = auth_client.put(f"/api/videos/{video_id}", json={
        "source_url": "https://youtu.be/YoHD9XEInc0",
    })

    assert edit_res.status_code == 200
    updated = edit_res.get_json()["video"]
    assert updated["source_type"] == "youtube"
    assert updated["source_url"] == "https://www.youtube.com/watch?v=YoHD9XEInc0"
    assert updated["embed_code"] == "YoHD9XEInc0"


def test_edit_video_rejects_invalid_replacement_source(auth_client):
    create_res = auth_client.post("/api/videos", json={
        "title": "Video with protected source",
        "source_type": "youtube",
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "is_published": True,
    })
    video_id = create_res.get_json()["video"]["id"]

    edit_res = auth_client.put(f"/api/videos/{video_id}", json={
        "source_url": "javascript:alert(1)",
    })

    assert edit_res.status_code == 400
    assert edit_res.get_json()["success"] is False
    unchanged = auth_client.get(f"/api/videos/{video_id}").get_json()["video"]
    assert unchanged["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_admin_video_editor_shows_existing_and_replacement_source_fields(auth_client):
    response = auth_client.get("/admin")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'id="editVideoCurrentSource"' in page
    assert 'id="editVideoSourceUrl"' in page


def test_delete_video(auth_client):
    create_res = auth_client.post("/api/videos", json={
        "title": "Video to Delete",
        "source_type": "youtube",
        "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "is_published": True,
    })
    video_id = create_res.get_json()["video"]["id"]

    delete_res = auth_client.delete(f"/api/videos/{video_id}")
    assert delete_res.status_code == 200
    assert delete_res.get_json()["success"] is True

    # Check it no longer exists
    check_res = auth_client.get(f"/api/videos/{video_id}")
    assert check_res.status_code == 404
