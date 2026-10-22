/**
 * VIDSPLAY Universal Video Player Modal Controller
 * Dynamically switches between YouTube iframe and HTML5 <video> with streaming.
 */

class VidsPlayer {
    constructor() {
        this.modalElement = document.getElementById('vpUniversalPlayerModal');
        this.playerContainer = document.getElementById('vpPlayerContainer');
        this.titleElement = document.getElementById('vpPlayerTitle');
        this.descElement = document.getElementById('vpPlayerDesc');
        this.categoryElement = document.getElementById('vpPlayerCategory');
        this.viewsElement = document.getElementById('vpPlayerViews');
        this.dateElement = document.getElementById('vpPlayerDate');
        this.sourceBadgeElement = document.getElementById('vpPlayerSourceBadge');
        this.externalLink = document.getElementById('vpPlayerExternalLink');
        this.shareBtn = document.getElementById('vpPlayerShareBtn');
        this.currentVideo = null;
        this.bsModal = null;

        this.init();
    }

    init() {
        if (!this.modalElement) return;

        // Initialize Bootstrap modal instance
        if (window.bootstrap && window.bootstrap.Modal) {
            this.bsModal = new bootstrap.Modal(this.modalElement);
        }

        // Clean up player on modal close (stops audio/video)
        this.modalElement.addEventListener('hidden.bs.modal', () => {
            this.clearPlayer();
        });

        // Global click delegator for any card with data-video-id
        document.addEventListener('click', (e) => {
            const card = e.target.closest('[data-video-id]');
            if (card) {
                e.preventDefault();
                const videoId = card.getAttribute('data-video-id');
                this.loadAndPlay(videoId);
            }
        });

        // Share button handler
        if (this.shareBtn) {
            this.shareBtn.addEventListener('click', () => {
                if (this.currentVideo) {
                    const shareUrl = `${window.location.origin}/#video-${this.currentVideo.id}`;
                    if (navigator.clipboard) {
                        navigator.clipboard.writeText(shareUrl).then(() => {
                            const originalText = this.shareBtn.innerHTML;
                            this.shareBtn.innerHTML = '<i class="bi bi-check2"></i> Copied!';
                            setTimeout(() => {
                                this.shareBtn.innerHTML = originalText;
                            }, 2000);
                        });
                    }
                }
            });
        }
    }

    async loadAndPlay(videoId) {
        try {
            // Show modal with loading state
            this.renderLoadingState();
            if (this.bsModal) this.bsModal.show();

            const response = await fetch(`/api/videos/${videoId}?increment_view=1`);
            const data = await response.json();

            if (!data.success || !data.video) {
                this.renderErrorState(data.error || 'Video could not be loaded');
                return;
            }

            this.currentVideo = data.video;
            this.renderVideo(data.video);
        } catch (err) {
            console.error('Failed to load video:', err);
            this.renderErrorState('Network error while loading video');
        }
    }

    renderLoadingState() {
        if (this.titleElement) this.titleElement.textContent = 'Loading video...';
        if (this.descElement) this.descElement.textContent = '';
        if (this.playerContainer) {
            this.playerContainer.innerHTML = `
                <div class="d-flex align-items-center justify-content-center h-100 py-5">
                    <div class="spinner-border text-info" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
        }
    }

    renderErrorState(msg) {
        if (this.titleElement) this.titleElement.textContent = 'Error';
        if (this.playerContainer) {
            const message = document.createElement('div');
            message.className = 'p-5 text-center text-danger';
            message.innerHTML = '<i class="bi bi-exclamation-triangle fs-1 mb-2"></i><h5>Playback Error</h5>';
            const detail = document.createElement('p');
            detail.className = 'text-secondary';
            detail.textContent = msg;
            message.appendChild(detail);
            this.playerContainer.replaceChildren(message);
        }
    }

    renderVideo(video) {
        if (this.externalLink) {
            this.externalLink.removeAttribute('href');
            this.externalLink.classList.add('d-none');
        }

        if (this.titleElement) this.titleElement.textContent = video.title;
        if (this.descElement) this.descElement.textContent = video.description || 'No description provided.';
        if (this.categoryElement) this.categoryElement.textContent = video.category_name;
        if (this.viewsElement) this.viewsElement.textContent = `${video.views_count.toLocaleString()} views`;
        if (this.dateElement && video.created_at) {
            const date = new Date(video.created_at);
            this.dateElement.textContent = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }

        if (this.sourceBadgeElement) {
            if (video.source_type === 'youtube') {
                this.sourceBadgeElement.className = 'badge vp-source-youtube me-2';
                this.sourceBadgeElement.textContent = 'YouTube';
            } else if (video.source_type === 'local') {
                this.sourceBadgeElement.className = 'badge vp-source-local me-2';
                this.sourceBadgeElement.textContent = 'HD Local';
            } else {
                this.sourceBadgeElement.className = 'badge bg-secondary me-2';
                this.sourceBadgeElement.textContent = 'External';
            }
        }

        if (video.source_type === 'youtube') {
            const videoId = this.getYouTubeId(video.embed_code) || this.getYouTubeId(video.source_url);
            if (!videoId) {
                this.renderErrorState('This video is missing a valid YouTube playback URL. Update its source in the admin panel.');
                return;
            }

            if (this.externalLink) {
                this.externalLink.href = `https://www.youtube.com/watch?v=${videoId}`;
                this.externalLink.classList.remove('d-none');
            }

            const frame = document.createElement('iframe');
            frame.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
            frame.title = video.title;
            frame.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
            frame.referrerPolicy = 'strict-origin-when-cross-origin';
            frame.allowFullscreen = true;
            this.playerContainer.replaceChildren(frame);
            return;
        }

        const playbackUrl = video.source_type === 'local'
            ? `/stream/${video.id}`
            : video.source_url;
        if (!playbackUrl || !/^https?:\/\//i.test(playbackUrl) && video.source_type !== 'local') {
            this.renderErrorState('This video has no valid playback source. Update its source in the admin panel.');
            return;
        }

        const videoElement = document.createElement('video');
        videoElement.controls = true;
        videoElement.autoplay = true;
        videoElement.playsInline = true;
        videoElement.preload = 'metadata';
        if (video.thumbnail_url) videoElement.poster = video.thumbnail_url;

        const source = document.createElement('source');
        source.src = playbackUrl;
        const path = video.source_type === 'local'
            ? (video.storage_key || '')
            : new URL(playbackUrl).pathname;
        const extension = path.split('.').pop().toLowerCase();
        const mimeTypes = {
            mp4: 'video/mp4',
            m4v: 'video/mp4',
            webm: 'video/webm',
            ogg: 'video/ogg',
            ogv: 'video/ogg'
        };
        if (mimeTypes[extension]) source.type = mimeTypes[extension];
        videoElement.appendChild(source);
        videoElement.addEventListener('error', () => {
            this.renderErrorState('The video source could not be loaded. It may have been removed or may not be playable in this browser.');
        }, { once: true });
        this.playerContainer.replaceChildren(videoElement);
    }

    getYouTubeId(value) {
        if (!value) return null;
        const rawValue = value.trim();
        if (/^[A-Za-z0-9_-]{11}$/.test(rawValue)) return rawValue;

        try {
            const url = new URL(rawValue);
            const host = url.hostname.replace(/^www\./, '');
            let videoId = '';
            if (host === 'youtu.be') {
                videoId = url.pathname.split('/').filter(Boolean)[0] || '';
            } else if (host === 'youtube.com' || host === 'youtube-nocookie.com') {
                if (url.pathname === '/watch') {
                    videoId = url.searchParams.get('v') || '';
                } else {
                    videoId = url.pathname.match(/^\/(?:embed|shorts)\/([^/]+)/)?.[1] || '';
                }
            }
            return /^[A-Za-z0-9_-]{11}$/.test(videoId) ? videoId : null;
        } catch {
            return null;
        }
    }

    clearPlayer() {
        if (this.playerContainer) {
            // Clearing innerHTML immediately stops YouTube iframe audio and HTML5 video
            this.playerContainer.innerHTML = '';
        }
        if (this.externalLink) {
            this.externalLink.removeAttribute('href');
            this.externalLink.classList.add('d-none');
        }
        this.currentVideo = null;
    }
}

// Instantiate on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.vidsPlayer = new VidsPlayer();
});
