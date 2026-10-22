import os
import re
from html.parser import HTMLParser
from pathlib import Path
from app import create_app, db
from models import AdminUser, Category, Video, NavigationItem, SiteSetting, Page, PageSection

app = create_app("development")


class _VideoCardParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.cards = {}
        self.capture = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        inherited_target = self.stack[-1][1] if self.stack else None
        if attributes.get("data-bs-toggle") == "modal":
            target = attributes.get("data-bs-target")
            if target and target.startswith("#"):
                inherited_target = target

        self.stack.append((tag, inherited_target))
        if not inherited_target:
            return

        card = self.cards.setdefault(
            inherited_target, {"imgpath": "", "title": "", "desc": ""}
        )
        classes = attributes.get("class", "").split()
        if tag == "img" and not card["imgpath"]:
            card["imgpath"] = attributes.get("src", "")
        elif tag == "h5" and "card-title" in classes:
            self.capture = (inherited_target, "title", tag)
        elif tag == "p" and "card-text" in classes and not card["desc"]:
            self.capture = (inherited_target, "desc", tag)

    def handle_endtag(self, tag):
        if self.capture and self.capture[2] == tag:
            self.capture = None

        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.capture:
            target, field, _ = self.capture
            self.cards[target][field] += data


def extract_videos_from_html(html_path: Path):
    if not html_path.exists():
        return []

    content = html_path.read_text(encoding="utf-8", errors="ignore")

    # Map modal IDs to embed URLs
    modal_embeds = {}
    modal_blocks = re.findall(
        r'<div\s+class="(?=[^"]*\bmodal\b)(?=[^"]*\bfade\b)[^"]*"[^>]*id="([^"]+)".*?<iframe[^>]+src="([^"]+)"',
        content,
        re.DOTALL
    )
    for mid, src in modal_blocks:
        modal_embeds["#" + mid] = src
        modal_embeds[mid] = src

    parser = _VideoCardParser()
    parser.feed(content)
    cards = []
    for target, card in parser.cards.items():
        imgpath = card["imgpath"].strip()
        title = re.sub(r"\s+", " ", card["title"]).strip()
        desc = re.sub(r"\s+", " ", card["desc"]).strip()
        if not title:
            continue

        # If imgpath is relative like 'img/...', convert to '/static/img/...'
        if imgpath.startswith("img/"):
            imgpath = "/static/" + imgpath
        elif not imgpath.startswith("/"):
            imgpath = "/" + imgpath

        modal_id = target.lstrip("#")
        embed_url = modal_embeds.get(target) or modal_embeds.get(modal_id) or ""
        yt_id = None
        if embed_url:
            yt_match = re.search(r"embed/([a-zA-Z0-9_-]{11})", embed_url)
            if yt_match:
                yt_id = yt_match.group(1)

        cards.append({
            "title": title,
            "desc": desc,
            "img": imgpath,
            "embed_url": embed_url,
            "yt_id": yt_id,
        })

    return cards


def run_seed():
    with app.app_context():
        print("Creating all database tables...")
        db.create_all()

        # 1. Admin User
        admin = AdminUser.query.filter_by(username="admin").first()
        if not admin:
            username = os.getenv("ADMIN_USERNAME")
            password = os.getenv("ADMIN_PASSWORD")
            if username and password:
                print(f"Creating admin user '{username}' from environment settings...")
                admin = AdminUser(
                    username=username,
                    email=os.getenv("ADMIN_EMAIL", "admin@vidsplay.com"),
                    role="admin",
                    is_active_account=True,
                )
                admin.set_password(password)
                db.session.add(admin)
            else:
                print("No admin created. Run 'flask --app app create-admin' to set credentials.")
        else:
            print("Admin user already exists.")

        # 2. Site Settings
        default_settings = {
            "site_title": "VIDSPLAY",
            "site_tagline": "Your Ultimate Destination for Movies, TV Shows, Web Series, Music & Entertainment",
            "marquee_text": "Welcome to VIDSPLAY - Your Ultimate Destination for Movies, TV Shows, Web Series, Anime, Documentaries, Kids' Content, Music, Sports, and Dance Entertainment!",
            "contact_email": "admin@vidsplay.com",
        }
        for k, v in default_settings.items():
            if not SiteSetting.query.get(k):
                db.session.add(SiteSetting(key=k, value=v))

        # 3. Categories
        category_defs = [
            ("Movies", "movies", "bi-film", "Blockbuster movies and cinema entertainment"),
            ("TV Shows", "tv-shows", "bi-tv", "Popular television serials, comedy and daily soaps"),
            ("Web Series", "web-series", "bi-collection-play", "Engaging multi-episode web series and thrillers"),
            ("Gaming", "gaming", "bi-controller", "Live gaming streams, esports and highlights"),
            ("Documentary", "documentary", "bi-camera-reels", "Insightful documentaries and real-life stories"),
            ("Kids", "kids", "bi-emoji-smile", "Fun, educational animations and stories for kids"),
            ("Music", "music", "bi-music-note-beamed", "Hit music videos, devotional and lyrical tracks"),
            ("Sports", "sports", "bi-trophy", "Match highlights, cricket specials and sports action"),
            ("Dance", "dance", "bi-activity", "Electrifying dance choreographies and viral trends"),
        ]

        cat_map = {}
        for idx, (cname, cslug, cicon, cdesc) in enumerate(category_defs):
            cat = Category.query.filter_by(slug=cslug).first()
            if not cat:
                cat = Category(
                    name=cname,
                    slug=cslug,
                    icon=cicon,
                    description=cdesc,
                    display_order=idx,
                    is_active=True,
                )
                db.session.add(cat)
                db.session.flush()
                print(f"Added category: {cname}")
            cat_map[cslug] = cat

        # 4. Navigation Items
        if NavigationItem.query.count() == 0:
            print("Seeding navigation items...")
            # Home
            db.session.add(NavigationItem(
                label="Home",
                target_type="custom",
                target_url="/",
                display_order=0,
                visibility="all",
                is_active=True,
            ))
            # Categories in navbar
            for idx, (cname, cslug, _, _) in enumerate(category_defs, start=1):
                cat = cat_map[cslug]
                db.session.add(NavigationItem(
                    label=cname,
                    target_type="category",
                    category_id=cat.id,
                    display_order=idx,
                    visibility="all",
                    is_active=True,
                ))

        # 5. Extract and Seed Videos from HTML files
        html_category_mapping = {
            "movies.html": "movies",
            "tv-shows.html": "tv-shows",
            "web-series.html": "web-series",
            "gaming.html": "gaming",
            "documentary.html": "documentary",
            "kids.html": "kids",
            "music.html": "music",
            "sports.html": "sports",
            "dance.html": "dance",
        }

        # Also extract recommended/trending from index.html
        base_dir = Path(__file__).resolve().parent

        # Seed categories' videos
        for html_file, cat_slug in html_category_mapping.items():
            file_path = base_dir / html_file
            extracted = extract_videos_from_html(file_path)
            cat = cat_map.get(cat_slug)

            for item in extracted:
                title = item["title"]
                # Clean title
                clean_title = re.sub(r"\s+", " ", title).strip()
                if not clean_title or len(clean_title) < 2:
                    continue

                existing = Video.query.filter_by(title=clean_title).first()
                if existing:
                    if item["yt_id"] and not existing.source_url:
                        existing.source_type = "youtube"
                        existing.source_url = f"https://www.youtube.com/watch?v={item['yt_id']}"
                        existing.embed_code = item["yt_id"]
                    if item["img"]:
                        existing.thumbnail_url = item["img"]
                    if cat and not existing.category_id:
                        existing.category_id = cat.id
                else:
                    # Generate slug
                    base_slug = re.sub(r"[^\w\s-]", "", clean_title.lower()).strip()
                    base_slug = re.sub(r"[\s_-]+", "-", base_slug)[:80]
                    slug = base_slug
                    cnt = 1
                    while Video.query.filter_by(slug=slug).first():
                        slug = f"{base_slug}-{cnt}"
                        cnt += 1

                    vid = Video(
                        title=clean_title,
                        slug=slug,
                        description=item["desc"],
                        source_type="youtube" if item["yt_id"] else "external",
                        source_url=(
                            f"https://www.youtube.com/watch?v={item['yt_id']}"
                            if item["yt_id"] else item["embed_url"]
                        ),
                        embed_code=item["yt_id"] or "",
                        thumbnail_url=item["img"],
                        category_id=cat.id if cat else None,
                        is_published=True,
                        is_featured=False,
                    )
                    db.session.add(vid)

        # Also extract from index.html for recommended/trending tracks
        index_extracted = extract_videos_from_html(base_dir / "index.html")
        for item in index_extracted:
            clean_title = re.sub(r"\s+", " ", item["title"]).strip()
            if not clean_title or len(clean_title) < 2:
                continue
            existing = Video.query.filter_by(title=clean_title).first()
            if existing:
                if item["yt_id"] and not existing.source_url:
                    existing.source_type = "youtube"
                    existing.source_url = f"https://www.youtube.com/watch?v={item['yt_id']}"
                    existing.embed_code = item["yt_id"]
                if item["img"]:
                    existing.thumbnail_url = item["img"]
                if "song" in clean_title.lower() and not existing.category_id:
                    existing.category_id = cat_map["music"].id
            else:
                base_slug = re.sub(r"[^\w\s-]", "", clean_title.lower()).strip()
                base_slug = re.sub(r"[\s_-]+", "-", base_slug)[:80]
                slug = base_slug
                cnt = 1
                while Video.query.filter_by(slug=slug).first():
                    slug = f"{base_slug}-{cnt}"
                    cnt += 1

                # Guess category or assign to music / trending
                vid = Video(
                    title=clean_title,
                    slug=slug,
                    description=item["desc"],
                    source_type="youtube" if item["yt_id"] else "external",
                    source_url=(
                        f"https://www.youtube.com/watch?v={item['yt_id']}"
                        if item["yt_id"] else item["embed_url"]
                    ),
                    embed_code=item["yt_id"] or "",
                    thumbnail_url=item["img"],
                    category_id=cat_map["music"].id if "song" in clean_title.lower() else None,
                    is_published=True,
                    is_featured=True,
                )
                db.session.add(vid)

        # 6. Default sample dynamic page (to test Page Builder immediately)
        anime_page = Page.query.filter_by(slug="anime").first()
        if not anime_page:
            print("Creating sample 'Anime' page for Page Builder testing...")
            anime_page = Page(
                title="Anime Spotlight",
                slug="anime",
                meta_description="Discover top trending Japanese anime series and movies.",
                template="default",
                is_published=True,
            )
            db.session.add(anime_page)
            db.session.flush()

            # Add Hero Section
            hero_sec = PageSection(
                page_id=anime_page.id,
                section_type="hero",
                title="Anime Universe",
                subtitle="Stream the highest-rated anime series, OVA episodes, and movies.",
                config={"bg_color": "dark", "align": "center", "badge": "New Feature"},
                display_order=0,
                is_visible=True,
            )
            db.session.add(hero_sec)

            # Add Video Grid Section
            grid_sec = PageSection(
                page_id=anime_page.id,
                section_type="video_grid",
                title="Top Anime Picks",
                subtitle="Hand-picked action, shonen, and fantasy titles",
                config={"columns": 4, "limit": 8, "show_views": True},
                display_order=1,
                is_visible=True,
            )
            db.session.add(grid_sec)

        db.session.commit()
        print(f"Seed complete! Total Videos in DB: {Video.query.count()}")
        print(f"Total Categories: {Category.query.count()}")
        print(f"Total Navigation Items: {NavigationItem.query.count()}")


if __name__ == "__main__":
    run_seed()
