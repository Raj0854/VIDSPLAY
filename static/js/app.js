/**
 * VIDSPLAY Frontend Application Controller
 * Handles dynamic navbar fetching, live search autocomplete, and page interactions.
 */

class VidsApp {
    constructor() {
        this.navContainer = document.getElementById('vpDynamicNav');
        this.mobileNavContainer = document.getElementById('vpDynamicMobileNav');
        this.searchInput = document.getElementById('vpSearchInput');
        this.searchSubmitBtn = document.getElementById('vpSearchSubmit');
        this.searchResultsDropdown = document.getElementById('vpSearchResultsDropdown');
        this.searchClearBtn = document.getElementById('vpSearchClear');
        this.searchTimeout = null;

        this.init();
    }

    async init() {
        await this.loadNavigation();
        this.setupSearch();
    }

    async loadNavigation() {
        if (!this.navContainer) return;

        try {
            const response = await fetch('/api/navigation');
            const data = await response.json();

            if (!data.success || !data.items) return;

            const currentPath = window.location.pathname;

            let html = '';
            let mobileHtml = '';

            data.items.forEach(item => {
                const isActive = (item.resolved_url === currentPath) || 
                                 (currentPath.startsWith('/category/') && item.resolved_url === currentPath) ||
                                 (currentPath.startsWith('/pages/') && item.resolved_url === currentPath);
                
                const activeClass = isActive ? 'active' : '';
                const iconHtml = item.icon ? `<i class="${item.icon}"></i>` : '';

                // Handle item with dropdown children
                if (item.children && item.children.length > 0) {
                    const dropdownId = `navDrop_${item.id}`;
                    html += `
                        <li class="nav-item dropdown">
                            <a class="vp-nav-link dropdown-toggle ${activeClass}" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                                ${iconHtml} ${this.escapeHtml(item.label)}
                            </a>
                            <ul class="dropdown-menu dropdown-menu-dark">
                                ${item.children.map(c => `
                                    <li><a class="dropdown-item" href="${c.resolved_url}">${c.icon ? `<i class="${c.icon} me-1"></i>` : ''}${this.escapeHtml(c.label)}</a></li>
                                `).join('')}
                            </ul>
                        </li>
                    `;
                } else {
                    // Regular item
                    if (item.visibility !== 'mobile') {
                        html += `
                            <li class="nav-item">
                                <a class="vp-nav-link ${activeClass}" href="${item.resolved_url}">
                                    ${iconHtml} ${this.escapeHtml(item.label)}
                                </a>
                            </li>
                        `;
                    }
                }

                // Mobile list
                if (item.visibility !== 'desktop') {
                    mobileHtml += `
                        <li class="nav-item">
                            <a class="nav-link text-white ${activeClass}" href="${item.resolved_url}">
                                ${iconHtml} ${this.escapeHtml(item.label)}
                            </a>
                        </li>
                    `;
                }
            });

            this.navContainer.innerHTML = html;
            if (this.mobileNavContainer) {
                this.mobileNavContainer.innerHTML = mobileHtml;
            }
        } catch (err) {
            console.error('Failed to load navigation:', err);
        }
    }

    setupSearch() {
        if (!this.searchInput) return;

        this.searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();

            if (this.searchClearBtn) {
                this.searchClearBtn.style.display = query ? 'block' : 'none';
            }

            clearTimeout(this.searchTimeout);

            if (!query) {
                this.hideSearchResults();
                return;
            }

            this.searchTimeout = setTimeout(() => {
                this.performSearch(query);
            }, 250);
        });

        if (this.searchClearBtn) {
            this.searchClearBtn.addEventListener('click', () => {
                this.searchInput.value = '';
                this.searchClearBtn.style.display = 'none';
                this.hideSearchResults();
            });
        }

        if (this.searchSubmitBtn) {
            this.searchSubmitBtn.addEventListener('click', () => {
                this.searchInput.focus();
                if (this.searchInput.value.trim()) {
                    this.performSearch(this.searchInput.value.trim());
                }
            });
        }

        // Close search dropdown on click outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.vp-search-container')) {
                this.hideSearchResults();
            }
        });
    }

    async performSearch(query) {
        if (!this.searchResultsDropdown) return;

        try {
            const response = await fetch(`/api/videos?q=${encodeURIComponent(query)}&per_page=6`);
            const data = await response.json();

            if (!data.videos || data.videos.length === 0) {
                this.searchResultsDropdown.innerHTML = `
                    <div class="p-3 text-center text-muted small">
                        No videos found matching "<strong>${this.escapeHtml(query)}</strong>"
                    </div>
                `;
                this.searchResultsDropdown.style.display = 'block';
                return;
            }

            let html = '';
            data.videos.forEach(v => {
                html += `
                    <div class="vp-search-result-item" data-video-id="${v.id}">
                        <img src="${v.thumbnail_url}" class="vp-search-result-thumb" alt="${this.escapeHtml(v.title)}">
                        <div class="flex-grow-1 overflow-hidden">
                            <div class="text-truncate fw-semibold small text-white">${this.escapeHtml(v.title)}</div>
                            <div class="text-muted text-truncate" style="font-size: 0.75rem;">
                                <span class="text-info">${this.escapeHtml(v.category_name)}</span> • ${v.views_count.toLocaleString()} views
                            </div>
                        </div>
                        <i class="bi bi-play-circle text-info fs-5"></i>
                    </div>
                `;
            });

            this.searchResultsDropdown.innerHTML = html;
            this.searchResultsDropdown.style.display = 'block';
        } catch (err) {
            console.error('Search error:', err);
        }
    }

    hideSearchResults() {
        if (this.searchResultsDropdown) {
            this.searchResultsDropdown.style.display = 'none';
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.vidsApp = new VidsApp();
});
