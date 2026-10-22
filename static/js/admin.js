/**
 * VIDSPLAY Admin Dashboard SPA Controller
 * Handles all management modules: Videos, Uploads, URLs, Categories, Navbar, Page Builder, Media, Settings.
 */

let currentAdminTab = 'overview';
let cachedCategories = [];
let cachedPages = [];
let videoCurrentPage = 1;
let deleteTarget = { type: null, id: null, title: '' };

// Toast notification helper
function showToast(msg, type = 'info') {
    const toastEl = document.getElementById('adminToast');
    const msgEl = document.getElementById('toastMessage');
    if (!toastEl || !msgEl) return;

    const icon = type === 'success' ? 'bi-check-circle text-success' : 
                 (type === 'danger' ? 'bi-exclamation-triangle text-danger' : 'bi-info-circle text-info');
    msgEl.innerHTML = `<i class="bi ${icon}"></i> <span>${msg}</span>`;

    if (window.bootstrap && window.bootstrap.Toast) {
        const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
        toast.show();
    }
}

// Tab Switcher
function switchAdminTab(tabName) {
    currentAdminTab = tabName;
    window.location.hash = tabName;

    // Update nav links
    document.querySelectorAll('.vp-admin-nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.tab === tabName);
    });

    // Update tab panes
    document.querySelectorAll('.tab-pane-content').forEach(pane => {
        pane.classList.add('d-none');
    });

    const activePane = document.getElementById(`tab-${tabName}`);
    if (activePane) activePane.classList.remove('d-none');

    // Update title
    const titles = {
        'overview': 'Dashboard Overview',
        'videos': 'Video Catalogue Management',
        'add-video': 'Add New Video',
        'categories': 'Categories Management',
        'navbar': 'Dynamic Navbar Builder',
        'pages': 'Pages & Layout Builder',
        'media': 'Media Assets Library',
        'settings': 'Platform Settings',
        'activity': 'System Activity Logs',
    };
    const titleEl = document.getElementById('currentTabTitle');
    if (titleEl) titleEl.textContent = titles[tabName] || 'Admin Dashboard';

    // Trigger module loaders
    if (tabName === 'overview') loadOverviewStats();
    if (tabName === 'videos') loadVideosTable();
    if (tabName === 'categories') loadCategoriesTable();
    if (tabName === 'navbar') loadNavbarTable();
    if (tabName === 'pages') loadPagesTable();
    if (tabName === 'media') loadMediaGrid();
    if (tabName === 'settings') loadSiteSettings();
    if (tabName === 'activity') loadActivityLogs();
}

document.addEventListener('DOMContentLoaded', () => {
    // Check initial hash
    const initialHash = window.location.hash.replace('#', '');
    if (initialHash) {
        switchAdminTab(initialHash);
    } else {
        switchAdminTab('overview');
    }

    // Nav link click events
    document.querySelectorAll('.vp-admin-nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            switchAdminTab(link.dataset.tab);
        });
    });

    // Mobile sidebar toggler
    const toggleBtn = document.getElementById('sidebarToggleBtn');
    const sidebar = document.getElementById('vpAdminSidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('show');
        });
    }

    // Logout
    const logoutBtn = document.getElementById('adminLogoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await fetch('/api/auth/logout', { method: 'POST' });
            window.location.href = '/admin/login';
        });
    }

    // Initialize module handlers
    initVideoModule();
    initUploadModule();
    initUrlModule();
    initCategoryModule();
    initNavbarModule();
    initPageBuilderModule();
    initMediaModule();
    initSettingsModule();
    initDeleteConfirmModal();
});

/* ==========================================================================
   MODULE 1: OVERVIEW
   ========================================================================== */
async function loadOverviewStats() {
    try {
        const res = await fetch('/api/dashboard/stats');
        const data = await res.json();
        if (!data.success) return;

        const s = data.stats;
        document.getElementById('statTotalVideos').textContent = s.total_videos.toLocaleString();
        document.getElementById('statPublished').textContent = s.published_videos.toLocaleString();
        document.getElementById('statDraft').textContent = s.draft_videos.toLocaleString();
        document.getElementById('statCategories').textContent = s.total_categories.toLocaleString();
        document.getElementById('statNavTabs').textContent = s.active_nav_tabs.toLocaleString();

        // Recent videos
        const vTable = document.getElementById('overviewRecentVideosTable');
        if (data.recent_videos.length === 0) {
            vTable.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">No videos added yet.</td></tr>';
        } else {
            vTable.innerHTML = data.recent_videos.map(v => `
                <tr>
                    <td>
                        <div class="d-flex align-items-center gap-2">
                            <img src="${v.thumbnail_url || '/static/img/logo.png'}" class="rounded" style="width: 44px; height: 26px; object-fit: cover;">
                            <div class="text-truncate fw-semibold text-white small" style="max-width: 200px;">${escapeHtml(v.title)}</div>
                        </div>
                    </td>
                    <td><span class="badge bg-dark border border-secondary text-info">${escapeHtml(v.category_name)}</span></td>
                    <td><span class="badge ${v.source_type === 'youtube' ? 'vp-source-youtube' : 'vp-source-local'}">${v.source_type}</span></td>
                    <td>${v.is_published ? '<span class="text-success small"><i class="bi bi-check-circle"></i> Published</span>' : '<span class="text-warning small"><i class="bi bi-pause-circle"></i> Draft</span>'}</td>
                </tr>
            `).join('');
        }

        // Recent activity
        const aList = document.getElementById('overviewRecentActivityList');
        if (data.recent_activity.length === 0) {
            aList.innerHTML = '<div class="text-center text-muted py-3">No recent logs recorded.</div>';
        } else {
            aList.innerHTML = data.recent_activity.map(a => `
                <div class="d-flex justify-content-between align-items-start border-bottom border-secondary py-2">
                    <div>
                        <div class="text-white small fw-semibold">${escapeHtml(a.action.replace('_', ' ').toUpperCase())}</div>
                        <div class="text-secondary" style="font-size: 0.78rem;">${escapeHtml(a.details)}</div>
                    </div>
                    <div class="text-muted" style="font-size: 0.72rem;">${formatTime(a.timestamp)}</div>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error('Stats error:', err);
    }
}

/* ==========================================================================
   MODULE 2: VIDEOS MANAGEMENT
   ========================================================================== */
function initVideoModule() {
    const searchInput = document.getElementById('videoSearchInput');
    const catFilter = document.getElementById('videoCategoryFilter');
    const statusFilter = document.getElementById('videoStatusFilter');
    const prevBtn = document.getElementById('videoPrevPageBtn');
    const nextBtn = document.getElementById('videoNextPageBtn');

    let debounceTimer;
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                videoCurrentPage = 1;
                loadVideosTable();
            }, 300);
        });
    }

    if (catFilter) {
        catFilter.addEventListener('change', () => {
            videoCurrentPage = 1;
            loadVideosTable();
        });
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            videoCurrentPage = 1;
            loadVideosTable();
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (videoCurrentPage > 1) {
                videoCurrentPage--;
                loadVideosTable();
            }
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            videoCurrentPage++;
            loadVideosTable();
        });
    }

    // Edit Video form submit
    const editForm = document.getElementById('editVideoForm');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('editVideoId').value;
            const title = document.getElementById('editVideoTitle').value;
            const category_id = document.getElementById('editVideoCategory').value;
            const thumbnail_url = document.getElementById('editVideoThumbnail').value;
            const description = document.getElementById('editVideoDesc').value;
            const source_url = document.getElementById('editVideoSourceUrl').value.trim();
            const is_published = document.getElementById('editVideoPublished').checked;
            const is_featured = document.getElementById('editVideoFeatured').checked;
            const payload = { title, category_id, thumbnail_url, description, is_published, is_featured };
            if (source_url) payload.source_url = source_url;

            try {
                const res = await fetch(`/api/videos/${id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    showToast('Video updated successfully!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('editVideoModal')).hide();
                    loadVideosTable();
                } else {
                    showToast(data.error || 'Update failed', 'danger');
                }
            } catch (err) {
                showToast('Error updating video', 'danger');
            }
        });
    }
}

async function loadVideosTable() {
    const tableBody = document.getElementById('videosTableBody');
    const searchVal = document.getElementById('videoSearchInput')?.value.trim() || '';
    const catVal = document.getElementById('videoCategoryFilter')?.value || '';
    const statusVal = document.getElementById('videoStatusFilter')?.value || 'all';

    // Populate category filter options once
    await populateCategoryDropdowns();

    let url = `/api/videos?include_drafts=1&page=${videoCurrentPage}&per_page=10`;
    if (searchVal) url += `&q=${encodeURIComponent(searchVal)}`;
    if (catVal) url += `&category=${encodeURIComponent(catVal)}`;

    try {
        const res = await fetch(url);
        const data = await res.json();

        let videos = data.videos || [];
        if (statusVal === 'published') videos = videos.filter(v => v.is_published);
        if (statusVal === 'draft') videos = videos.filter(v => !v.is_published);

        if (videos.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No matching videos found.</td></tr>';
            document.getElementById('videoPaginationInfo').textContent = 'Showing 0 of 0';
            document.getElementById('videoPrevPageBtn').disabled = true;
            document.getElementById('videoNextPageBtn').disabled = true;
            return;
        }

        tableBody.innerHTML = videos.map(v => `
            <tr>
                <td>
                    <img src="${v.thumbnail_url || '/static/img/logo.png'}" class="rounded" style="width: 58px; height: 34px; object-fit: cover;">
                </td>
                <td>
                    <div class="fw-semibold text-white small">${escapeHtml(v.title)}</div>
                    <div class="text-muted text-truncate" style="font-size: 0.75rem; max-width: 250px;">${escapeHtml(v.description || '')}</div>
                </td>
                <td><span class="badge bg-dark border border-secondary text-info">${escapeHtml(v.category_name)}</span></td>
                <td><span class="badge ${v.source_type === 'youtube' ? 'vp-source-youtube' : 'vp-source-local'}">${v.source_type}</span></td>
                <td><span class="text-secondary small"><i class="bi bi-eye"></i> ${v.views_count.toLocaleString()}</span></td>
                <td>
                    <div class="form-check form-switch mb-0">
                        <input class="form-check-input" type="checkbox" ${v.is_published ? 'checked' : ''} onchange="toggleVideoPublish(${v.id}, this.checked)">
                    </div>
                </td>
                <td>
                    <div class="d-flex align-items-center gap-1">
                        <button class="btn btn-sm btn-outline-info border-0" title="Edit" onclick="openEditVideoModal(${v.id})"><i class="bi bi-pencil-square"></i></button>
                        <button class="btn btn-sm btn-outline-danger border-0" title="Delete" onclick="confirmDelete('video', ${v.id}, '${escapeHtml(v.title)}')"><i class="bi bi-trash"></i></button>
                    </div>
                </td>
            </tr>
        `).join('');

        document.getElementById('videoPaginationInfo').textContent = `Page ${data.page} of ${data.pages} (${data.total} total videos)`;
        document.getElementById('videoPrevPageBtn').disabled = (data.page <= 1);
        document.getElementById('videoNextPageBtn').disabled = (data.page >= data.pages);
    } catch (err) {
        console.error('Error loading videos table:', err);
    }
}

async function toggleVideoPublish(videoId, isPublished) {
    try {
        const res = await fetch(`/api/videos/${videoId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_published: isPublished })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Video ${isPublished ? 'published' : 'saved as draft'}!`, 'success');
        }
    } catch (err) {
        showToast('Failed to toggle status', 'danger');
    }
}

async function openEditVideoModal(videoId) {
    try {
        const res = await fetch(`/api/videos/${videoId}`);
        const data = await res.json();
        if (!data.success) return;
        const v = data.video;

        document.getElementById('editVideoId').value = v.id;
        document.getElementById('editVideoTitle').value = v.title;
        document.getElementById('editVideoThumbnail').value = v.thumbnail_url;
        document.getElementById('editVideoDesc').value = v.description;
        document.getElementById('editVideoSourceUrl').value = '';

        const currentSource = v.source_url || (
            v.source_type === 'local' ? `${window.location.origin}/stream/${v.id}` : ''
        );
        const currentSourceInput = document.getElementById('editVideoCurrentSource');
        const openSourceLink = document.getElementById('editVideoOpenSource');
        currentSourceInput.value = currentSource || 'No source URL is saved';
        openSourceLink.classList.add('d-none');
        openSourceLink.removeAttribute('href');
        if (/^https?:\/\//i.test(currentSource)) {
            openSourceLink.href = currentSource;
            openSourceLink.classList.remove('d-none');
        }

        document.getElementById('editVideoPublished').checked = v.is_published;
        document.getElementById('editVideoFeatured').checked = v.is_featured;

        // Populate categories
        const catSelect = document.getElementById('editVideoCategory');
        catSelect.innerHTML = cachedCategories.map(c => `
            <option value="${c.id}" ${c.id === v.category_id ? 'selected' : ''}>${escapeHtml(c.name)}</option>
        `).join('');

        new bootstrap.Modal(document.getElementById('editVideoModal')).show();
    } catch (err) {
        showToast('Error fetching video details', 'danger');
    }
}

/* ==========================================================================
   MODULE 3: ADD VIDEO (OPTION 1 LOCAL UPLOAD & OPTION 2 URL)
   ========================================================================== */
function initUploadModule() {
    const dropzone = document.getElementById('videoDropzone');
    const fileInput = document.getElementById('localVideoFileInput');
    const fileNameDisplay = document.getElementById('selectedVideoFileName');
    const uploadForm = document.getElementById('uploadVideoForm');
    const progressWrapper = document.getElementById('uploadProgressWrapper');
    const progressFill = document.getElementById('uploadProgressFill');
    const progressPercent = document.getElementById('uploadProgressPercent');
    const submitBtn = document.getElementById('uploadSubmitBtn');

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(event => {
        dropzone.addEventListener(event, (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(event => {
        dropzone.addEventListener(event, (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelected(fileInput.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFileSelected(fileInput.files[0]);
        }
    });

    function handleFileSelected(file) {
        fileNameDisplay.textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
        // Auto-fill title if empty
        const titleInput = document.getElementById('uploadVideoTitle');
        if (titleInput && !titleInput.value) {
            const raw = file.name.replace(/\.[^/.]+$/, "");
            titleInput.value = raw.replace(/[_-]+/g, " ");
        }
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (!fileInput.files || fileInput.files.length === 0) {
                showToast('Please select a video file to upload', 'danger');
                return;
            }

            const formData = new FormData(uploadForm);
            progressWrapper.classList.remove('d-none');
            submitBtn.disabled = true;

            const xhr = new XMLHttpRequest();
            xhr.open('POST', '/api/videos', true);

            xhr.upload.onprogress = (event) => {
                if (event.lengthComputable) {
                    const percent = Math.round((event.loaded / event.total) * 100);
                    progressFill.style.width = percent + '%';
                    progressPercent.textContent = percent + '%';
                }
            };

            xhr.onload = () => {
                submitBtn.disabled = false;
                progressWrapper.classList.add('d-none');
                try {
                    const data = JSON.parse(xhr.responseText);
                    if (xhr.status >= 200 && xhr.status < 300 && data.success) {
                        showToast('Video uploaded and saved to catalogue successfully!', 'success');
                        uploadForm.reset();
                        fileNameDisplay.textContent = '';
                        switchAdminTab('videos');
                    } else {
                        showToast(data.error || 'Upload error', 'danger');
                    }
                } catch (err) {
                    showToast('Server response parsing error', 'danger');
                }
            };

            xhr.onerror = () => {
                submitBtn.disabled = false;
                progressWrapper.classList.add('d-none');
                showToast('Network upload error', 'danger');
            };

            xhr.send(formData);
        });
    }
}

function initUrlModule() {
    const validateBtn = document.getElementById('validateUrlBtn');
    const urlInput = document.getElementById('urlInput');
    const previewBox = document.getElementById('urlPreviewBox');
    const previewThumb = document.getElementById('urlPreviewThumb');
    const previewBadge = document.getElementById('urlPreviewSourceBadge');
    const previewNormalized = document.getElementById('urlPreviewNormalized');
    const urlForm = document.getElementById('urlVideoForm');

    if (validateBtn && urlInput) {
        validateBtn.addEventListener('click', async () => {
            const url = urlInput.value.trim();
            if (!url) {
                showToast('Please enter a video URL first', 'warning');
                return;
            }

            try {
                const res = await fetch('/api/videos/validate-url', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                const data = await res.json();

                if (data.valid) {
                    previewBox.classList.remove('d-none');
                    previewThumb.src = data.thumbnail_url || '/static/img/logo.png';
                    previewBadge.textContent = data.source_type.toUpperCase();
                    previewBadge.className = `badge ${data.source_type === 'youtube' ? 'vp-source-youtube' : 'vp-source-local'} mb-1`;
                    previewNormalized.textContent = data.normalized_url;
                    showToast('URL validated successfully!', 'success');
                } else {
                    previewBox.classList.add('d-none');
                    showToast(data.error || 'Invalid video URL', 'danger');
                }
            } catch (err) {
                showToast('Error validating URL', 'danger');
            }
        });
    }

    if (urlForm) {
        urlForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const source_url = urlInput.value.trim();
            const title = document.getElementById('urlVideoTitle').value.trim();
            const category_id = document.getElementById('urlCategorySelect').value;
            const description = document.getElementById('urlVideoDesc').value;
            const thumbnail_url = document.getElementById('urlCustomThumb').value.trim();
            const is_published = document.getElementById('urlPublishedSwitch').checked;
            const is_featured = document.getElementById('urlFeaturedSwitch').checked;

            try {
                const res = await fetch('/api/videos', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source_type: 'youtube',
                        source_url,
                        title,
                        category_id,
                        description,
                        thumbnail_url,
                        is_published,
                        is_featured,
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Video added to catalogue successfully!', 'success');
                    urlForm.reset();
                    previewBox.classList.add('d-none');
                    switchAdminTab('videos');
                } else {
                    showToast(data.error || 'Failed to add video', 'danger');
                }
            } catch (err) {
                showToast('Error saving video', 'danger');
            }
        });
    }
}

/* ==========================================================================
   MODULE 4: CATEGORY MANAGEMENT
   ========================================================================== */
function initCategoryModule() {
    const form = document.getElementById('categoryForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('categoryId').value;
            const name = document.getElementById('categoryName').value.trim();
            const slug = document.getElementById('categorySlug').value.trim();
            const icon = document.getElementById('categoryIcon').value.trim();
            const description = document.getElementById('categoryDesc').value.trim();
            const is_active = document.getElementById('categoryActiveSwitch').checked;

            const url = id ? `/api/categories/${id}` : '/api/categories';
            const method = id ? 'PUT' : 'POST';

            try {
                const res = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, slug, icon, description, is_active })
                });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message || 'Category saved!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('addCategoryModal')).hide();
                    form.reset();
                    document.getElementById('categoryId').value = '';
                    loadCategoriesTable();
                } else {
                    showToast(data.error || 'Save failed', 'danger');
                }
            } catch (err) {
                showToast('Category save error', 'danger');
            }
        });
    }
}

async function loadCategoriesTable() {
    const tableBody = document.getElementById('categoriesTableBody');
    try {
        const res = await fetch('/api/categories?all=1');
        const data = await res.json();
        cachedCategories = data.categories || [];

        if (cachedCategories.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No categories created yet.</td></tr>';
            return;
        }

        tableBody.innerHTML = cachedCategories.map((c, idx) => `
            <tr>
                <td>
                    <div class="d-flex flex-column gap-1">
                        <button class="btn btn-sm btn-dark p-0 border-0" ${idx === 0 ? 'disabled' : ''} onclick="moveCategoryOrder(${idx}, -1)"><i class="bi bi-chevron-up"></i></button>
                        <button class="btn btn-sm btn-dark p-0 border-0" ${idx === cachedCategories.length - 1 ? 'disabled' : ''} onclick="moveCategoryOrder(${idx}, 1)"><i class="bi bi-chevron-down"></i></button>
                    </div>
                </td>
                <td class="fw-semibold text-white">${escapeHtml(c.name)}</td>
                <td><code class="text-info">${c.slug}</code></td>
                <td><i class="bi ${c.icon || 'bi-folder'} text-info fs-5"></i></td>
                <td><span class="badge bg-dark border border-secondary text-white">${c.video_count || 0} videos</span></td>
                <td>
                    <span class="badge ${c.is_active ? 'bg-success' : 'bg-secondary'}">${c.is_active ? 'Active' : 'Hidden'}</span>
                </td>
                <td>
                    <div class="d-flex align-items-center gap-1">
                        <button class="btn btn-sm btn-outline-info border-0" onclick="openEditCategoryModal(${c.id})"><i class="bi bi-pencil-square"></i></button>
                        <button class="btn btn-sm btn-outline-danger border-0" onclick="confirmDelete('category', ${c.id}, '${escapeHtml(c.name)}')"><i class="bi bi-trash"></i></button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Categories error:', err);
    }
}

async function moveCategoryOrder(index, direction) {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= cachedCategories.length) return;

    const temp = cachedCategories[index];
    cachedCategories[index] = cachedCategories[newIndex];
    cachedCategories[newIndex] = temp;

    const orderIds = cachedCategories.map(c => c.id);
    await fetch('/api/categories/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: orderIds })
    });
    loadCategoriesTable();
}

function openEditCategoryModal(catId) {
    const cat = cachedCategories.find(c => c.id === catId);
    if (!cat) return;

    document.getElementById('categoryId').value = cat.id;
    document.getElementById('categoryName').value = cat.name;
    document.getElementById('categorySlug').value = cat.slug;
    document.getElementById('categoryIcon').value = cat.icon || 'bi-folder';
    document.getElementById('categoryDesc').value = cat.description || '';
    document.getElementById('categoryActiveSwitch').checked = cat.is_active;
    document.getElementById('categoryModalTitle').textContent = 'Edit Category';

    new bootstrap.Modal(document.getElementById('addCategoryModal')).show();
}

/* ==========================================================================
   MODULE 5: NAVBAR MANAGEMENT
   ========================================================================== */
function initNavbarModule() {
    const targetTypeSelect = document.getElementById('navItemTargetType');
    if (targetTypeSelect) {
        targetTypeSelect.addEventListener('change', (e) => {
            const val = e.target.value;
            document.getElementById('navCategorySelectGroup').classList.toggle('d-none', val !== 'category');
            document.getElementById('navPageSelectGroup').classList.toggle('d-none', val !== 'page');
            document.getElementById('navCustomUrlGroup').classList.toggle('d-none', val !== 'custom');
        });
    }

    const form = document.getElementById('navItemForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('navItemId').value;
            const label = document.getElementById('navItemLabel').value.trim();
            const target_type = document.getElementById('navItemTargetType').value;
            const category_id = document.getElementById('navCategorySelect').value;
            const page_id = document.getElementById('navPageSelect').value;
            const target_url = document.getElementById('navCustomUrl').value.trim();
            const visibility = document.getElementById('navVisibility').value;
            const icon = document.getElementById('navIcon').value.trim();
            const is_active = document.getElementById('navActiveSwitch').checked;

            const payload = { label, target_type, category_id, page_id, target_url, visibility, icon, is_active };
            const url = id ? `/api/navigation/${id}` : '/api/navigation';
            const method = id ? 'PUT' : 'POST';

            try {
                const res = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message || 'Navbar item saved!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('addNavModal')).hide();
                    form.reset();
                    document.getElementById('navItemId').value = '';
                    loadNavbarTable();
                } else {
                    showToast(data.error || 'Save failed', 'danger');
                }
            } catch (err) {
                showToast('Navbar save error', 'danger');
            }
        });
    }
}

let cachedNavItems = [];
async function loadNavbarTable() {
    const tableBody = document.getElementById('navbarTableBody');
    await populateCategoryDropdowns();
    await populatePagesDropdowns();

    try {
        const res = await fetch('/api/navigation/all');
        const data = await res.json();
        cachedNavItems = data.items || [];

        if (cachedNavItems.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">No navbar tabs configured.</td></tr>';
            return;
        }

        tableBody.innerHTML = cachedNavItems.map((item, idx) => `
            <tr>
                <td>
                    <div class="d-flex flex-column gap-1">
                        <button class="btn btn-sm btn-dark p-0 border-0" ${idx === 0 ? 'disabled' : ''} onclick="moveNavOrder(${idx}, -1)"><i class="bi bi-chevron-up"></i></button>
                        <button class="btn btn-sm btn-dark p-0 border-0" ${idx === cachedNavItems.length - 1 ? 'disabled' : ''} onclick="moveNavOrder(${idx}, 1)"><i class="bi bi-chevron-down"></i></button>
                    </div>
                </td>
                <td class="fw-semibold text-white">
                    ${item.icon ? `<i class="${item.icon} me-1 text-info"></i>` : ''}
                    ${escapeHtml(item.label)}
                </td>
                <td><span class="badge bg-dark border border-secondary text-info text-capitalize">${item.target_type}</span></td>
                <td><code class="text-white small">${escapeHtml(item.resolved_url)}</code></td>
                <td><span class="badge bg-dark border border-secondary text-capitalize">${item.visibility}</span></td>
                <td><span class="badge ${item.is_active ? 'bg-success' : 'bg-secondary'}">${item.is_active ? 'Active' : 'Disabled'}</span></td>
                <td>
                    <div class="d-flex align-items-center gap-1">
                        <button class="btn btn-sm btn-outline-info border-0" onclick="openEditNavModal(${item.id})"><i class="bi bi-pencil-square"></i></button>
                        <button class="btn btn-sm btn-outline-danger border-0" onclick="confirmDelete('nav', ${item.id}, '${escapeHtml(item.label)}')"><i class="bi bi-trash"></i></button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Navbar error:', err);
    }
}

async function moveNavOrder(index, direction) {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= cachedNavItems.length) return;

    const temp = cachedNavItems[index];
    cachedNavItems[index] = cachedNavItems[newIndex];
    cachedNavItems[newIndex] = temp;

    const orderIds = cachedNavItems.map(i => i.id);
    await fetch('/api/navigation/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: orderIds })
    });
    loadNavbarTable();
}

function openEditNavModal(itemId) {
    const item = cachedNavItems.find(i => i.id === itemId);
    if (!item) return;

    document.getElementById('navItemId').value = item.id;
    document.getElementById('navItemLabel').value = item.label;
    document.getElementById('navItemTargetType').value = item.target_type;
    document.getElementById('navCategorySelect').value = item.category_id || '';
    document.getElementById('navPageSelect').value = item.page_id || '';
    document.getElementById('navCustomUrl').value = item.target_url || '';
    document.getElementById('navVisibility').value = item.visibility || 'all';
    document.getElementById('navIcon').value = item.icon || '';
    document.getElementById('navActiveSwitch').checked = item.is_active;

    document.getElementById('navCategorySelectGroup').classList.toggle('d-none', item.target_type !== 'category');
    document.getElementById('navPageSelectGroup').classList.toggle('d-none', item.target_type !== 'page');
    document.getElementById('navCustomUrlGroup').classList.toggle('d-none', item.target_type !== 'custom');

    document.getElementById('navModalTitle').textContent = 'Edit Navbar Tab';
    new bootstrap.Modal(document.getElementById('addNavModal')).show();
}

/* ==========================================================================
   MODULE 6: PAGES & VISUAL SECTION BUILDER
   ========================================================================== */
function initPageBuilderModule() {
    const createForm = document.getElementById('createPageForm');
    if (createForm) {
        createForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const title = document.getElementById('newPageTitle').value.trim();
            const slug = document.getElementById('newPageSlug').value.trim();
            const meta_description = document.getElementById('newPageMeta').value.trim();
            const add_to_navbar = document.getElementById('newPageNavbarCheck').checked;
            const is_published = document.getElementById('newPagePublishCheck').checked;

            try {
                const res = await fetch('/api/pages', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, slug, meta_description, add_to_navbar, is_published })
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Page created successfully!', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('createPageModal')).hide();
                    createForm.reset();
                    loadPagesTable();
                } else {
                    showToast(data.error || 'Failed to create page', 'danger');
                }
            } catch (err) {
                showToast('Page creation error', 'danger');
            }
        });
    }
}

async function loadPagesTable() {
    const tableBody = document.getElementById('pagesTableBody');
    try {
        const res = await fetch('/api/pages?all=1');
        const data = await res.json();
        cachedPages = data.pages || [];

        if (cachedPages.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No custom pages created yet.</td></tr>';
            return;
        }

        tableBody.innerHTML = cachedPages.map(p => `
            <tr>
                <td class="fw-semibold text-white">${escapeHtml(p.title)}</td>
                <td><a href="/pages/${p.slug}" target="_blank" class="text-info text-decoration-none">/pages/${p.slug} <i class="bi bi-box-arrow-up-right small"></i></a></td>
                <td><span class="badge ${p.is_published ? 'bg-success' : 'bg-secondary'}">${p.is_published ? 'Published' : 'Draft'}</span></td>
                <td>
                    <button class="btn btn-sm vp-btn-primary py-1 px-2" onclick="openSectionBuilder(${p.id})">
                        <i class="bi bi-layout-wtf"></i> Edit Sections
                    </button>
                </td>
                <td>
                    <div class="d-flex align-items-center gap-1">
                        <button class="btn btn-sm btn-outline-secondary border-0" title="Duplicate" onclick="duplicatePage(${p.id})"><i class="bi bi-copy"></i></button>
                        <button class="btn btn-sm btn-outline-danger border-0" title="Delete" onclick="confirmDelete('page', ${p.id}, '${escapeHtml(p.title)}')"><i class="bi bi-trash"></i></button>
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Pages error:', err);
    }
}

async function duplicatePage(pageId) {
    try {
        const res = await fetch(`/api/pages/${pageId}/duplicate`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            showToast('Page duplicated successfully!', 'success');
            loadPagesTable();
        }
    } catch (err) {
        showToast('Error duplicating page', 'danger');
    }
}

// Section Builder Logic
let currentBuilderPageId = null;
let currentBuilderSections = [];

async function openSectionBuilder(pageId) {
    currentBuilderPageId = pageId;
    document.getElementById('builderPageId').value = pageId;

    try {
        const res = await fetch(`/api/pages/${pageId}`);
        const data = await res.json();
        if (!data.success) return;

        const p = data.page;
        document.getElementById('builderPageTitle').textContent = `Editing: ${p.title}`;
        document.getElementById('builderPageSlug').textContent = `Route: /pages/${p.slug}`;

        currentBuilderSections = p.sections || [];
        renderBuilderSectionsList();

        new bootstrap.Modal(document.getElementById('sectionBuilderModal')).show();
    } catch (err) {
        showToast('Error opening section builder', 'danger');
    }
}

function renderBuilderSectionsList() {
    const list = document.getElementById('builderSectionsList');
    if (currentBuilderSections.length === 0) {
        list.innerHTML = '<div class="text-center py-4 text-secondary">No sections in this page. Click "+ Add Section" above!</div>';
        return;
    }

    const typeIcons = {
        'hero': 'bi-star text-warning',
        'video_grid': 'bi-grid-3x3 text-info',
        'category_grid': 'bi-tags text-primary',
        'banner': 'bi-megaphone text-danger',
        'text': 'bi-text-paragraph text-light',
    };

    list.innerHTML = currentBuilderSections.map((sec, idx) => `
        <div class="vp-builder-section-card">
            <div class="d-flex align-items-center gap-3">
                <div class="d-flex flex-column gap-1">
                    <button class="btn btn-sm btn-dark p-0 border-0" ${idx === 0 ? 'disabled' : ''} onclick="moveSectionOrder(${idx}, -1)"><i class="bi bi-chevron-up"></i></button>
                    <button class="btn btn-sm btn-dark p-0 border-0" ${idx === currentBuilderSections.length - 1 ? 'disabled' : ''} onclick="moveSectionOrder(${idx}, 1)"><i class="bi bi-chevron-down"></i></button>
                </div>
                <i class="bi ${typeIcons[sec.section_type] || 'bi-square'} fs-4"></i>
                <div>
                    <div class="fw-semibold text-white small">${escapeHtml(sec.title || sec.section_type.toUpperCase())}</div>
                    <div class="text-secondary" style="font-size: 0.75rem;">Type: <span class="text-info">${sec.section_type}</span> ${sec.subtitle ? `• ${escapeHtml(sec.subtitle)}` : ''}</div>
                </div>
            </div>
            <div class="d-flex align-items-center gap-2">
                <button class="btn btn-sm btn-outline-danger border-0" onclick="deleteSectionFromPage(${sec.id})"><i class="bi bi-trash"></i></button>
            </div>
        </div>
    `).join('');
}

async function addSectionToPage(sectionType) {
    if (!currentBuilderPageId) return;

    let defaultTitle = 'New Section';
    let defaultSubtitle = '';
    let config = {};

    if (sectionType === 'hero') {
        defaultTitle = 'Hero Showcase Banner';
        defaultSubtitle = 'Highlight your main announcement here.';
        config = { align: 'center', badge: 'Featured' };
    } else if (sectionType === 'video_grid') {
        defaultTitle = 'Curated Video Collection';
        defaultSubtitle = 'Watch hand-picked videos';
        config = { columns: 4, limit: 8 };
    } else if (sectionType === 'category_grid') {
        defaultTitle = 'All Entertainment Categories';
    } else if (sectionType === 'banner') {
        defaultTitle = 'Special Feature Announcement';
        defaultSubtitle = 'Click below to explore more.';
        config = { btn_text: 'Explore Now', btn_url: '/' };
    } else if (sectionType === 'text') {
        defaultTitle = 'About This Hub';
        defaultSubtitle = 'Add rich description or guidelines.';
    }

    try {
        const res = await fetch(`/api/pages/${currentBuilderPageId}/sections`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section_type: sectionType,
                title: defaultTitle,
                subtitle: defaultSubtitle,
                config,
                is_visible: true,
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast('Section added to page!', 'success');
            currentBuilderSections.push(data.section);
            renderBuilderSectionsList();
        }
    } catch (err) {
        showToast('Error adding section', 'danger');
    }
}

async function moveSectionOrder(index, direction) {
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= currentBuilderSections.length) return;

    const temp = currentBuilderSections[index];
    currentBuilderSections[index] = currentBuilderSections[newIndex];
    currentBuilderSections[newIndex] = temp;

    const orderIds = currentBuilderSections.map(s => s.id);
    await fetch(`/api/pages/${currentBuilderPageId}/sections/reorder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: orderIds })
    });
    renderBuilderSectionsList();
}

async function deleteSectionFromPage(sectionId) {
    try {
        await fetch(`/api/pages/sections/${sectionId}`, { method: 'DELETE' });
        currentBuilderSections = currentBuilderSections.filter(s => s.id !== sectionId);
        renderBuilderSectionsList();
        showToast('Section removed', 'info');
    } catch (err) {
        showToast('Error removing section', 'danger');
    }
}

/* ==========================================================================
   MODULE 7: MEDIA ASSETS LIBRARY
   ========================================================================== */
function initMediaModule() {
    const filter = document.getElementById('mediaTypeFilter');
    if (filter) {
        filter.addEventListener('change', () => loadMediaGrid());
    }

    const uploadInput = document.getElementById('mediaLibraryUploadInput');
    if (uploadInput) {
        uploadInput.addEventListener('change', async () => {
            if (!uploadInput.files || uploadInput.files.length === 0) return;
            const formData = new FormData();
            formData.append('file', uploadInput.files[0]);

            try {
                showToast('Uploading asset...', 'info');
                const res = await fetch('/api/media/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Asset uploaded successfully!', 'success');
                    uploadInput.value = '';
                    loadMediaGrid();
                } else {
                    showToast(data.error || 'Upload error', 'danger');
                }
            } catch (err) {
                showToast('Network upload error', 'danger');
            }
        });
    }
}

async function loadMediaGrid() {
    const container = document.getElementById('mediaGridContainer');
    const type = document.getElementById('mediaTypeFilter')?.value || 'all';

    try {
        const res = await fetch(`/api/media?type=${type}`);
        const data = await res.json();
        const assets = data.assets || [];

        if (assets.length === 0) {
            container.innerHTML = '<div class="text-center text-muted py-5 w-100">No media assets found in library.</div>';
            return;
        }

        container.innerHTML = assets.map(a => `
            <div class="vp-media-item">
                <img src="${a.file_path}" class="vp-media-thumb" alt="${escapeHtml(a.original_name)}" onerror="this.src='/static/img/logo.png'">
                <div class="p-2">
                    <div class="text-truncate fw-semibold text-white small" title="${escapeHtml(a.original_name)}">${escapeHtml(a.original_name)}</div>
                    <div class="text-secondary d-flex justify-content-between align-items-center mt-1" style="font-size: 0.72rem;">
                        <span>${(a.file_size / 1024).toFixed(0)} KB</span>
                        <div class="d-flex gap-1">
                            <button class="btn btn-sm btn-dark p-0 px-1 border-0" title="Copy URL" onclick="copyToClipboard('${a.file_path}')"><i class="bi bi-clipboard"></i></button>
                            <button class="btn btn-sm btn-outline-danger p-0 px-1 border-0" title="Delete" onclick="confirmDelete('media', ${a.id}, '${escapeHtml(a.original_name)}')"><i class="bi bi-trash"></i></button>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Media error:', err);
    }
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('Path copied to clipboard!', 'success');
        });
    }
}

/* ==========================================================================
   MODULE 8: GLOBAL SETTINGS
   ========================================================================== */
function initSettingsModule() {
    const form = document.getElementById('siteSettingsForm');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                site_title: document.getElementById('settingSiteTitle').value.trim(),
                site_tagline: document.getElementById('settingSiteTagline').value.trim(),
                marquee_text: document.getElementById('settingMarqueeText').value.trim(),
                contact_email: document.getElementById('settingContactEmail').value.trim(),
            };

            try {
                const res = await fetch('/api/dashboard/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Platform settings saved successfully!', 'success');
                }
            } catch (err) {
                showToast('Error saving settings', 'danger');
            }
        });
    }
}

async function loadSiteSettings() {
    try {
        const res = await fetch('/api/dashboard/settings');
        const data = await res.json();
        if (data.success && data.settings) {
            const s = data.settings;
            document.getElementById('settingSiteTitle').value = s.site_title || '';
            document.getElementById('settingSiteTagline').value = s.site_tagline || '';
            document.getElementById('settingMarqueeText').value = s.marquee_text || '';
            document.getElementById('settingContactEmail').value = s.contact_email || '';
        }
    } catch (err) {
        console.error('Settings load error:', err);
    }
}

/* ==========================================================================
   MODULE 9: ACTIVITY LOGS
   ========================================================================== */
async function loadActivityLogs() {
    const tableBody = document.getElementById('activityLogsTableBody');
    try {
        const res = await fetch('/api/dashboard/activity');
        const data = await res.json();
        const logs = data.logs || [];

        if (logs.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">No audit logs recorded yet.</td></tr>';
            return;
        }

        tableBody.innerHTML = logs.map(l => `
            <tr>
                <td class="text-secondary small">${formatTime(l.timestamp)}</td>
                <td><span class="badge bg-dark border border-secondary text-info">${escapeHtml(l.username)}</span></td>
                <td class="fw-semibold text-white small">${escapeHtml(l.action)}</td>
                <td class="text-secondary small">${escapeHtml(l.details)}</td>
                <td><code class="text-muted small">${l.ip_address || '127.0.0.1'}</code></td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Activity logs error:', err);
    }
}

/* ==========================================================================
   DELETE CONFIRMATION DIALOG CONTROLLER
   ========================================================================== */
function initDeleteConfirmModal() {
    const actionBtn = document.getElementById('confirmDeleteActionBtn');
    if (actionBtn) {
        actionBtn.addEventListener('click', async () => {
            const { type, id } = deleteTarget;
            if (!type || !id) return;

            actionBtn.disabled = true;

            try {
                let url = '';
                let options = { method: 'DELETE' };

                if (type === 'video') url = `/api/videos/${id}`;
                if (type === 'category') {
                    url = `/api/categories/${id}`;
                    const reassignId = document.getElementById('deleteReassignCategorySelect').value;
                    if (reassignId) {
                        options.headers = { 'Content-Type': 'application/json' };
                        options.body = JSON.stringify({ reassign_to_id: parseInt(reassignId) });
                    }
                }
                if (type === 'nav') url = `/api/navigation/${id}`;
                if (type === 'page') url = `/api/pages/${id}`;
                if (type === 'media') url = `/api/media/${id}?force=1`;

                const res = await fetch(url, options);
                const data = await res.json();

                actionBtn.disabled = false;
                bootstrap.Modal.getInstance(document.getElementById('confirmDeleteModal')).hide();

                if (data.success) {
                    showToast(data.message || 'Record deleted successfully!', 'success');
                    if (type === 'video') loadVideosTable();
                    if (type === 'category') loadCategoriesTable();
                    if (type === 'nav') loadNavbarTable();
                    if (type === 'page') loadPagesTable();
                    if (type === 'media') loadMediaGrid();
                } else {
                    showToast(data.error || 'Failed to delete record', 'danger');
                }
            } catch (err) {
                actionBtn.disabled = false;
                showToast('Deletion request failed', 'danger');
            }
        });
    }
}

function confirmDelete(type, id, title) {
    deleteTarget = { type, id, title };
    const promptEl = document.getElementById('confirmDeletePrompt');
    const reassignBox = document.getElementById('categoryReassignContainer');

    promptEl.innerHTML = `Are you sure you want to delete <strong>"${title}"</strong>?`;

    // If deleting category, offer reassignment dropdown
    if (type === 'category') {
        reassignBox.classList.remove('d-none');
        const select = document.getElementById('deleteReassignCategorySelect');
        select.innerHTML = '<option value="">Do not reassign (Uncategorized)</option>' + 
            cachedCategories.filter(c => c.id !== id).map(c => `
                <option value="${c.id}">${escapeHtml(c.name)}</option>
            `).join('');
    } else {
        reassignBox.classList.add('d-none');
    }

    new bootstrap.Modal(document.getElementById('confirmDeleteModal')).show();
}

/* Helper Utilities */
async function populateCategoryDropdowns() {
    if (cachedCategories.length === 0) {
        const res = await fetch('/api/categories?all=1');
        const data = await res.json();
        cachedCategories = data.categories || [];
    }

    const options = cachedCategories.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');

    const uploadCat = document.getElementById('uploadCategorySelect');
    if (uploadCat) uploadCat.innerHTML = '<option value="">Select Category</option>' + options;

    const urlCat = document.getElementById('urlCategorySelect');
    if (urlCat) urlCat.innerHTML = '<option value="">Select Category</option>' + options;

    const filterCat = document.getElementById('videoCategoryFilter');
    if (filterCat) {
        filterCat.innerHTML = '<option value="">All Categories</option>' + 
            cachedCategories.map(c => `<option value="${c.slug}">${escapeHtml(c.name)}</option>`).join('');
    }

    const navCat = document.getElementById('navCategorySelect');
    if (navCat) navCat.innerHTML = options;
}

async function populatePagesDropdowns() {
    if (cachedPages.length === 0) {
        const res = await fetch('/api/pages?all=1');
        const data = await res.json();
        cachedPages = data.pages || [];
    }

    const navPage = document.getElementById('navPageSelect');
    if (navPage) {
        navPage.innerHTML = cachedPages.map(p => `<option value="${p.id}">${escapeHtml(p.title)} (/pages/${p.slug})</option>`).join('');
    }
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatTime(isoStr) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr);
        return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
        return isoStr;
    }
}
