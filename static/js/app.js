/* ═══════════════════════════════════════════════════════════════════════════
   FindFast - Job Board JavaScript Application Logic
   ═══════════════════════════════════════════════════════════════════════════ */

/**
 * Utility function to escape HTML and prevent XSS attacks
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format relative date strings
 */
function formatRelativeDate(dateStr) {
    if (!dateStr || dateStr === 'Not specified' || dateStr === 'Recently') {
        return 'Recently';
    }

    try {
        let date = new Date(dateStr);
        if (isNaN(date.getTime())) {
            return 'Recently';
        }

        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMinutes = Math.floor(diffMs / (1000 * 60));

        if (diffMinutes < 60) {
            return diffMinutes === 0 ? 'Just now' : `${diffMinutes}m ago`;
        } else if (diffHours < 24) {
            return `${diffHours}h ago`;
        } else if (diffDays === 1) {
            return 'Yesterday';
        } else if (diffDays < 7) {
            return `${diffDays}d ago`;
        } else if (diffDays < 30) {
            const weeks = Math.floor(diffDays / 7);
            return `${weeks}w ago`;
        } else {
            return `${Math.floor(diffDays / 30)}mo ago`;
        }
    } catch (error) {
        return 'Recently';
    }
}

/**
 * Load and display job statistics
 */
async function loadStats() {
    try {
        console.log('Loading stats...');
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        console.log('Stats data:', data);
        console.log('Jobs by source:', data.jobs_by_source);
        console.log('Jobs by location:', data.jobs_by_location);

        document.getElementById('totalJobsCount').textContent = data.total_jobs.toLocaleString();
        document.getElementById('sourcesCount').textContent = Object.keys(data.jobs_by_source || {}).length;

        // Format last updated time
        if (data.combined_at && data.combined_at !== 'Unknown') {
            const lastUpdated = new Date(data.combined_at);
            const now = new Date();
            const diffMinutes = Math.round((now - lastUpdated) / (1000 * 60));

            if (diffMinutes < 60) {
                document.getElementById('lastUpdated').textContent = `${diffMinutes}m ago`;
            } else if (diffMinutes < 1440) {
                const hours = Math.round(diffMinutes / 60);
                document.getElementById('lastUpdated').textContent = `${hours}h ago`;
            } else {
                const days = Math.round(diffMinutes / 1440);
                document.getElementById('lastUpdated').textContent = `${days}d ago`;
            }
        }

        // Populate dropdowns
        populateFilters(data);
    } catch (error) {
        console.error('Error loading stats:', error);
        showToast('Error loading stats', 'error');
    }
}

/**
 * Populate filter dropdowns with available options
 */
function populateFilters(statsData) {
    try {
        console.log('populateFilters called with:', statsData);
        
        // Populate location filter
        const locationSelect = document.getElementById('locationFilter');
        const sourceSelect = document.getElementById('sourceFilter');

        if (!locationSelect || !sourceSelect) {
            console.error('Filter select elements not found!');
            return;
        }

        // Get unique locations and sources from stats
        const locations = Object.keys(statsData.jobs_by_location || {}).sort();
        const sources = Object.keys(statsData.jobs_by_source || {}).sort();

        console.log('Locations to add:', locations);
        console.log('Sources to add:', sources);

        // Clear existing options (except the first "All" option)
        while (locationSelect.options.length > 1) {
            locationSelect.remove(1);
        }
        while (sourceSelect.options.length > 1) {
            sourceSelect.remove(1);
        }

        // Add location options
        locations.forEach(location => {
            const option = document.createElement('option');
            option.value = location;
            option.textContent = location;
            locationSelect.appendChild(option);
        });

        // Add source options
        sources.forEach(source => {
            const option = document.createElement('option');
            option.value = source;
            option.textContent = source;
            sourceSelect.appendChild(option);
        });

        console.log('Filters populated:', locations.length, 'locations,', sources.length, 'sources');
    } catch (error) {
        console.error('Error populating filters:', error);
    }
}

/**
 * Load jobs with applied filters
 */
let currentPage = 1;
const jobsPerPage = 20;
let aiFilterActive = false;
let aiFilterCriteria = '';

async function loadJobs() {
    try {
        if (currentPage === 1) {
            // Reset to page 1 when filters change
        }
        const searchQuery = document.getElementById('searchInput')?.value.trim() || '';
        const location = document.getElementById('locationFilter')?.value || '';
        const source = document.getElementById('sourceFilter')?.value || '';
        const viewedFilter = document.getElementById('viewedFilter')?.value || '';
        const sort = document.getElementById('sortFilter')?.value || '';

        console.log('Filter values - search:', searchQuery, 'location:', location, 'source:', source, 'viewed:', viewedFilter, 'sort:', sort);

        // If AI filter is active, re-run it with current filters
        if (aiFilterActive && aiFilterCriteria) {
            console.log('AI filter active, applying with current filters');
            await filterJobsWithAI(true); // Pass true to indicate this is a refresh
            return;
        }

        const params = new URLSearchParams();
        if (searchQuery) params.append('keyword', searchQuery);
        if (location) params.append('location', location);
        if (source) params.append('source', source);
        // Don't pass 'relevance' to backend - handle it on frontend
        if (sort && sort !== 'relevance') {
            params.append('sort', sort);
        }

        console.log('Loading jobs with params:', params.toString());

        const response = await fetch(`/api/jobs?${params.toString()}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        console.log('Total jobs:', data.total);

        let allJobs = data.jobs;

        // Apply viewed filter on frontend
        if (viewedFilter) {
            if (viewedFilter === 'viewed') {
                allJobs = allJobs.filter(job => {
                    const jobId = job.job_id || job.url;
                    return userViewedJobs.has(jobId);
                });
                console.log(`Filtered to ${allJobs.length} viewed jobs`);
            } else if (viewedFilter === 'not-viewed') {
                allJobs = allJobs.filter(job => {
                    const jobId = job.job_id || job.url;
                    return !userViewedJobs.has(jobId);
                });
                console.log(`Filtered to ${allJobs.length} not-viewed jobs`);
            }
        }

        // Handle relevance sorting on frontend (viewed jobs go to bottom)
        if (sort === 'relevance') {
            const viewedJobs = [];
            const unviewedJobs = [];
            
            allJobs.forEach(job => {
                const jobId = job.job_id || job.url;
                if (userViewedJobs.has(jobId)) {
                    viewedJobs.push(job);
                } else {
                    unviewedJobs.push(job);
                }
            });
            
            // Combine: unviewed jobs first, then viewed jobs at bottom
            allJobs = [...unviewedJobs, ...viewedJobs];
            console.log(`Relevance sort: ${unviewedJobs.length} unviewed, ${viewedJobs.length} viewed`);
        }

        // Paginate the jobs (after relevance sorting)
        const startIdx = (currentPage - 1) * jobsPerPage;
        const endIdx = startIdx + jobsPerPage;
        const paginatedJobs = allJobs.slice(startIdx, endIdx);

        renderJobs(paginatedJobs);
        // Show total after sorting
        renderPagination(allJobs.length);
    } catch (error) {
        console.error('Error loading jobs:', error);
        showToast('Error loading jobs', 'error');
    }
}

/**
 * Render job cards
 */
function renderJobs(jobs) {
    const jobsList = document.getElementById('jobsList');
    jobsList.innerHTML = '';

    if (jobs.length === 0) {
        jobsList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-search"></i>
                <h3>No jobs found</h3>
                <p>Try adjusting your filters or search terms</p>
            </div>
        `;
        return;
    }

    jobs.forEach((job, index) => {
        const card = createJobCard(job);
        card.style.animationDelay = `${index * 30}ms`;
        jobsList.appendChild(card);
    });
}

/**
 * Create individual job card HTML
 */
function createJobCard(job) {
    const card = document.createElement('div');
    card.className = 'job-card';
    card.setAttribute('data-job-id', job.job_id || job.url);
    
    // Check if job was already viewed
    const isViewed = userViewedJobs.has(job.job_id || job.url);
    if (isViewed) {
        card.classList.add('job-viewed');
    }

    card.innerHTML = `
        <div class="job-header">
            <div>
                <h3 class="job-title">${escapeHtml(job.title)}</h3>
                <p class="job-company">${escapeHtml(job.company)}</p>
            </div>
        </div>

        <div class="job-meta">
            <span class="job-location">
                <i class="fas fa-map-marker-alt"></i> ${escapeHtml(job.location || 'Not specified')}
            </span>
            <span class="job-salary">
                <i class="fas fa-money-bill-wave"></i> ${escapeHtml(job.salary || 'Not specified')}
            </span>
            <span class="job-date">
                <i class="fas fa-clock"></i> ${formatRelativeDate(job.posted)}
            </span>
        </div>

        ${job.summary ? `<p class="job-description">${escapeHtml(job.summary.substring(0, 150))}...</p>` : ''}

        <div style="display: flex; gap: 0.5rem; margin-top: 1rem; flex-wrap: wrap;">
            <span class="job-source">${escapeHtml(job.source)}</span>
            ${job.job_type ? `<span style="font-size: 0.85rem; color: #6B7280;"><i class="fas fa-briefcase"></i> ${escapeHtml(job.job_type)}</span>` : ''}
        </div>

        <a href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary btn-sm job-link" style="margin-top: 1rem; display: inline-block;">
            View Job <i class="fas fa-arrow-right"></i>
        </a>
    `;
    
    // Track job view when link is clicked
    const jobLink = card.querySelector('.job-link');
    jobLink.addEventListener('click', () => {
        trackJobView(job.job_id || job.url, job.url);
    });

    return card;
}

/**
 * Render pagination buttons
 */
function renderPagination(total) {
    const totalPages = Math.ceil(total / jobsPerPage);
    const paginationNumbers = document.getElementById('paginationNumbers');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');

    paginationNumbers.innerHTML = '';

    // Previous button
    prevBtn.disabled = currentPage === 1;

    // Page numbers
    const maxPages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxPages / 2));
    let endPage = Math.min(totalPages, startPage + maxPages - 1);

    if (endPage - startPage + 1 < maxPages) {
        startPage = Math.max(1, endPage - maxPages + 1);
    }

    for (let i = startPage; i <= endPage; i++) {
        const btn = document.createElement('button');
        btn.className = `pagination-num ${i === currentPage ? 'active' : ''}`;
        btn.textContent = i;
        btn.addEventListener('click', () => goToPage(i));
        paginationNumbers.appendChild(btn);
    }

    // Ellipsis
    if (endPage < totalPages) {
        const ellipsis = document.createElement('span');
        ellipsis.className = 'pagination-ellipsis';
        ellipsis.textContent = '...';
        paginationNumbers.appendChild(ellipsis);
    }

    // Next button
    nextBtn.disabled = currentPage === totalPages;
}

/**
 * Go to specific page
 */
async function goToPage(page) {
    currentPage = page;
    window.scrollTo({ top: 0, behavior: 'smooth' });
    await loadJobs();
}

/**
 * Toggle dark mode
 */
function toggleDarkMode() {
    const htmlElement = document.documentElement;
    htmlElement.classList.toggle('dark-mode');
    const isDarkMode = htmlElement.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDarkMode);
    
    // Update icon
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.innerHTML = isDarkMode ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    const locationFilter = document.getElementById('locationFilter');
    const sourceFilter = document.getElementById('sourceFilter');
    const viewedFilter = document.getElementById('viewedFilter');
    const sortFilter = document.getElementById('sortFilter');
    const resetBtn = document.getElementById('resetFiltersBtn');
    const clearSearchBtn = document.getElementById('clearSearchBtn');
    const refreshBtn = document.getElementById('refreshJobsBtn');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');

    // Debounced search
    let searchTimeout;
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            currentPage = 1;
            searchTimeout = setTimeout(loadJobs, 300);
        });
    }

    if (locationFilter) locationFilter.addEventListener('change', () => {
        console.log('Location filter changed to:', locationFilter.value);
        currentPage = 1;
        loadJobs();
    });
    if (sourceFilter) sourceFilter.addEventListener('change', () => {
        console.log('Source filter changed to:', sourceFilter.value);
        currentPage = 1;
        loadJobs();
    });
    if (viewedFilter) viewedFilter.addEventListener('change', () => {
        console.log('Viewed filter changed to:', viewedFilter.value);
        currentPage = 1;
        loadJobs();
    });
    if (sortFilter) sortFilter.addEventListener('change', () => {
        console.log('Sort filter changed to:', sortFilter.value);
        currentPage = 1;
        loadJobs();
    });

    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', function() {
            searchInput.value = '';
            loadJobs();
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            console.log('Reset filters clicked');
            searchInput.value = '';
            locationFilter.value = '';
            sourceFilter.value = '';
            viewedFilter.value = '';
            sortFilter.value = '';
            currentPage = 1;
            loadJobs();
        });
    }

    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshJobs);
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) goToPage(currentPage - 1);
        });
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => goToPage(currentPage + 1));
    }

    // Close scraper status panel
    const closeStatusBtn = document.getElementById('closeStatusBtn');
    if (closeStatusBtn) {
        closeStatusBtn.addEventListener('click', () => {
            document.getElementById('scraperStatusPanel').style.display = 'none';
        });
    }

    // Dark mode toggle
    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleDarkMode);
    }

    // AI Filter button
    const aiFilterBtn = document.getElementById('aiFilterBtn');
    if (aiFilterBtn) {
        aiFilterBtn.addEventListener('click', filterJobsWithAI);
    }

    // Clear AI filter button
    const clearAiFilterBtn = document.getElementById('clearAiFilter');
    if (clearAiFilterBtn) {
        clearAiFilterBtn.addEventListener('click', clearAIFilter);
    }

    // Allow Enter key to trigger AI filter
    const aiFilterInput = document.getElementById('aiFilterInput');
    if (aiFilterInput) {
        aiFilterInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                filterJobsWithAI();
            }
        });
    }
}

/**
 * Refresh jobs (trigger scraping)
 */
async function refreshJobs() {
    if (!confirm('Update job listings? This may take a few minutes.')) {
        return;
    }

    const btn = document.getElementById('refreshJobsBtn');
    const statusPanel = document.getElementById('scraperStatusPanel');
    const scraperLog = document.getElementById('scraperLog');
    
    btn.disabled = true;
    statusPanel.style.display = 'block';
    scraperLog.innerHTML = '';
    addLogEntry('Initializing update...', 'running');

    try {
        const response = await fetch('/api/scrape', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'success') {
            addLogEntry('Update started!', 'running');

            // Poll for updates every 2 seconds
            let pollCount = 0;
            const pollInterval = setInterval(async () => {
                pollCount++;

                try {
                    const statusResponse = await fetch('/api/scrape-status');
                    const statusData = await statusResponse.json();

                    addLogEntry(statusData.message || 'Update in progress...', statusData.running ? 'running' : 'complete');

                    if (statusData.status === 'complete' || pollCount > 150) {
                        clearInterval(pollInterval);
                        addLogEntry('Update complete! Refreshing jobs...', 'complete');
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        location.reload();
                    }
                } catch (e) {
                    console.error('Error checking scrape status:', e);
                    addLogEntry('Error checking update: ' + e.message, 'error');
                }
            }, 2000);

            // Timeout after 5 minutes
            setTimeout(() => {
                clearInterval(pollInterval);
                location.reload();
            }, 300000);
        } else {
            addLogEntry('Error starting update', 'error');
            showToast('Error starting update', 'error');
        }
    } catch (error) {
        console.error('Error triggering update:', error);
        addLogEntry('Error: ' + error.message, 'error');
        showToast('Error starting update', 'error');
    } finally {
        btn.disabled = false;
    }
}

/**
 * Add entry to scraper log
 */
function addLogEntry(message, status = 'info') {
    const scraperLog = document.getElementById('scraperLog');
    const entry = document.createElement('div');
    entry.className = 'scraper-log-entry';
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString();
    
    const statusClass = `log-status-${status}`;
    entry.innerHTML = `
        <span class="log-time">${timeStr}</span>
        <span class="log-message ${statusClass}">${message}</span>
    `;
    
    scraperLog.appendChild(entry);
    scraperLog.scrollTop = scraperLog.scrollHeight;
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
        'success': 'fa-check-circle',
        'error': 'fa-exclamation-circle',
        'info': 'fa-info-circle'
    };

    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
        <button class="toast-close" title="Close"><i class="fas fa-times"></i></button>
    `;

    container.appendChild(toast);

    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
        toast.remove();
    });

    setTimeout(() => {
        toast.classList.add('show');
    }, 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

/**
 * Show/hide loading overlay
 */
function showLoadingOverlay(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

/**
 * AI Filter Jobs - Process in chunks
 */
async function filterJobsWithAI(isRefresh = false) {
    const criteria = document.getElementById('aiFilterInput').value.trim();
    
    if (!criteria) {
        showToast('Please enter your search criteria', 'info');
        return;
    }
    
    // Store AI filter state
    aiFilterActive = true;
    aiFilterCriteria = criteria;
    
    const filterBtn = document.getElementById('aiFilterBtn');
    const originalText = filterBtn.innerHTML;
    const jobsList = document.getElementById('jobsList');
    const resultDiv = document.getElementById('aiFilterResult');
    
    filterBtn.disabled = true;
    filterBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
    
    // Show loading state
    jobsList.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: #6B7280;"><i class="fas fa-spinner fa-spin" style="font-size: 2rem; color: #c09023; margin-bottom: 1rem;"></i><br>Processing jobs with AI...<br><small>This may take a moment</small></div>';
    if (!isRefresh) {
        resultDiv.style.display = 'none';
    }
    document.querySelector('.pagination').style.display = 'none';
    
    try {
        // Get current filter values (respects existing filters)
        const searchQuery = document.getElementById('searchInput')?.value.trim() || '';
        const location = document.getElementById('locationFilter')?.value || '';
        const source = document.getElementById('sourceFilter')?.value || '';
        const viewedFilter = document.getElementById('viewedFilter')?.value || '';
        
        console.log('AI filter with - criteria:', criteria, 'location:', location, 'source:', source, 'keyword:', searchQuery, 'viewed:', viewedFilter);
        
        const response = await fetch('/api/ai-filter-chunked', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                criteria: criteria,
                location,
                source,
                keyword: searchQuery
            })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            showToast(data.message || 'Error filtering jobs', 'error');
            jobsList.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #EF4444;">${data.message}</div>`;
            return;
        }
        
        let filteredJobs = data.filtered_jobs;
        
        // Apply viewed filter to AI results
        if (viewedFilter) {
            if (viewedFilter === 'viewed') {
                filteredJobs = filteredJobs.filter(job => {
                    const jobId = job.job_id || job.url;
                    return userViewedJobs.has(jobId);
                });
            } else if (viewedFilter === 'not-viewed') {
                filteredJobs = filteredJobs.filter(job => {
                    const jobId = job.job_id || job.url;
                    return !userViewedJobs.has(jobId);
                });
            }
        }
        
        // Display result explanation
        const explanationDiv = resultDiv.querySelector('.ai-filter-explanation');
        const filterInfo = [];
        if (location) filterInfo.push(`Location: ${location}`);
        if (source) filterInfo.push(`Source: ${source}`);
        if (searchQuery) filterInfo.push(`Search: "${searchQuery}"`);
        if (viewedFilter) filterInfo.push(`Status: ${viewedFilter === 'viewed' ? 'Viewed' : 'Not Viewed'}`);
        
        let explanationText = `Found ${filteredJobs.length} matching jobs: ${data.explanation}`;
        if (filterInfo.length > 0) {
            explanationText += ` (with filters: ${filterInfo.join(', ')})`;
        }
        
        explanationDiv.textContent = explanationText;
        resultDiv.style.display = 'block';
        
        // Display filtered jobs
        renderAIFilteredJobs(filteredJobs);
        
        if (!isRefresh) {
            showToast(`Found ${data.total_filtered} matching jobs!`, 'success');
        }
        
    } catch (error) {
        console.error('AI filter error:', error);
        showToast('Error processing your request: ' + error.message, 'error');
        jobsList.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #EF4444;">Error: ${error.message}</div>`;
    } finally {
        filterBtn.disabled = false;
        filterBtn.innerHTML = originalText;
    }
}

/**
 * Render AI filtered jobs
 */
function renderAIFilteredJobs(jobs) {
    const jobsList = document.getElementById('jobsList');
    
    if (!jobs || jobs.length === 0) {
        jobsList.innerHTML = '<div style="text-align: center; padding: 2rem; grid-column: 1/-1; color: #6B7280;"><i class="fas fa-search" style="font-size: 2rem; color: #c09023; margin-bottom: 0.5rem;"></i><br>No jobs match your criteria.<br><small>Try different search terms.</small></div>';
        return;
    }
    
    jobsList.innerHTML = '';
    
    // Add jobs with animation
    jobs.forEach((job, index) => {
        const card = createJobCard(job);
        jobsList.appendChild(card);
    });
    
    // Hide pagination when showing AI filtered results
    document.querySelector('.pagination').style.display = 'none';
    
    // Scroll to results
    setTimeout(() => {
        jobsList.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}

/**
 * Clear AI filter and show all jobs again
 */
function clearAIFilter() {
    aiFilterActive = false;
    aiFilterCriteria = '';
    document.getElementById('aiFilterInput').value = '';
    document.getElementById('aiFilterResult').style.display = 'none';
    document.querySelector('.pagination').style.display = 'flex';
    currentPage = 1;
    loadJobs();
}

/* ═══════════════════════════════════════════════════════════════════════════
   User Authentication (Firebase)
   ═══════════════════════════════════════════════════════════════════════════ */

let currentUser = null;
let userViewedJobs = new Set();

function initializeAuth() {
    const logoutBtn = document.getElementById('logoutBtn');
    const userInfo = document.getElementById('userInfo');
    
    // Check if user is authenticated via backend session
    fetch('/api/auth/user')
        .then(r => r.json())
        .then(data => {
            if (data.success && data.user) {
                currentUser = data.user;
                userInfo.textContent = data.user.name || data.user.email;
                loadUserHistory();
                loadJobs();
            } else {
                // Not authenticated - redirect to login
                window.location.href = '/login';
            }
        })
        .catch(err => {
            console.error('Auth check failed:', err);
            window.location.href = '/login';
        });
    
    // Logout button
    logoutBtn.addEventListener('click', () => {
        fetch('/api/auth/logout', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    currentUser = null;
                    userViewedJobs.clear();
                    showToast('Signed out successfully', 'success');
                    window.location.href = '/login';
                }
            })
            .catch(err => {
                console.error('Logout failed:', err);
                window.location.href = '/login';
            });
    });
}

function loadUserHistory() {
    if (!currentUser) return;
    
    const userId = currentUser.uid || currentUser.email;
    fetch(`/api/user-history/${encodeURIComponent(userId)}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                userViewedJobs = new Set(data.viewed_jobs.map(j => j.job_id));
                console.log(`Loaded ${data.total_viewed} viewed jobs for ${userId}`);
            }
        })
        .catch(err => console.error('Error loading user history:', err));
}

function trackJobView(jobId, jobUrl) {
    if (!currentUser) return;
    
    if (userViewedJobs.has(jobId)) return; // Already tracked
    
    const userId = currentUser.uid || currentUser.email;
    fetch('/api/track-job', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: userId,
            job_id: jobId,
            job_url: jobUrl
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            userViewedJobs.add(jobId);
            // Update UI to show job as viewed
            const jobCard = document.querySelector(`[data-job-id="${jobId}"]`);
            if (jobCard) {
                jobCard.classList.add('job-viewed');
            }
        }
    })
    .catch(err => console.error('Error tracking job:', err));
}

/* ═══════════════════════════════════════════════════════════════════════════
   Initialization
   ═══════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded. Initializing...');
    initializeAuth(); // This will load jobs after auth check
    loadStats();
    setupEventListeners();
});
