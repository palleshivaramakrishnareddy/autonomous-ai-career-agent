// CareerPilot AI — Client-Side Application Core

const API_BASE = window.location.origin;

let state = {
  currentTab: 'dashboard',
  profile: null,
  jobs: [],
  applications: [],
  agentConfig: null,
  logs: [],
  analytics: null,
  selectedStudioJobId: null,
  currentStudioSubtab: 'resume',
  searchTimeout: null,
};

// ==================== INITIALIZATION ====================

document.addEventListener('DOMContentLoaded', async () => {
  await initApp();
});

async function initApp() {
  lucide.createIcons();
  await Promise.all([
    fetchProfile(),
    fetchAgentConfig(),
    loadJobs(),
    loadApplications(),
    fetchActivityLogs(),
    fetchAnalytics()
  ]);
  updateDashboardUI();
  setupEventListeners();
  lucide.createIcons();
}

function setupEventListeners() {
  // Re-run icons when tabs change or content re-renders
}

// ==================== API HELPERS ====================

async function fetchAPI(endpoint, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      },
      ...options
    });
    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}));
      throw new Error(errorData.detail || `Request failed with status ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Error [${endpoint}]:`, err);
    showToast(err.message, 'error');
    throw err;
  }
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  const colors = {
    info: 'bg-slate-900 border-slate-700 text-slate-200',
    success: 'bg-emerald-950/90 border-emerald-600/50 text-emerald-200',
    error: 'bg-red-950/90 border-red-600/50 text-red-200',
    action: 'bg-indigo-950/90 border-indigo-600/50 text-indigo-200'
  };

  toast.className = `px-4 py-3 rounded-xl border text-xs shadow-xl flex items-center gap-2 transform transition-all duration-300 ease-out translate-y-2 opacity-0 ${colors[type] || colors.info}`;
  toast.innerHTML = `
    <i data-lucide="${type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'info'}" class="w-4 h-4 shrink-0"></i>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  lucide.createIcons();

  setTimeout(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ==================== TAB NAVIGATION ====================

function switchTab(tabId) {
  state.currentTab = tabId;

  // Toggle active nav item
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const activeNav = document.getElementById(`nav-${tabId}`);
  if (activeNav) activeNav.classList.add('active');

  // Toggle tab views
  document.querySelectorAll('.tab-view').forEach(el => el.classList.add('hidden'));
  const activeView = document.getElementById(`view-${tabId}`);
  if (activeView) activeView.classList.remove('hidden');

  // Refresh tab specific views
  if (tabId === 'dashboard') {
    updateDashboardUI();
    fetchActivityLogs();
  } else if (tabId === 'radar') {
    renderRadarJobs();
  } else if (tabId === 'studio') {
    populateStudioDropdown();
  } else if (tabId === 'kanban') {
    renderKanbanBoard();
  } else if (tabId === 'profile') {
    populateProfileForm();
  } else if (tabId === 'agent') {
    populateAgentConfigForm();
    fetchActivityLogs();
  } else if (tabId === 'analytics') {
    fetchAnalytics();
  }

  lucide.createIcons();
}

// ==================== DATA FETCHING ====================

async function fetchProfile() {
  try {
    const data = await fetchAPI('/api/profile');
    state.profile = data;

    // Update Header Avatar & Name
    document.getElementById('user-display-name').textContent = data.full_name;
    const initials = data.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    document.getElementById('user-avatar-initials').textContent = initials;
    const topRole = data.target_roles[0] || 'Software Engineer';
    document.getElementById('user-display-role').textContent = topRole;
  } catch (e) {}
}

async function fetchAgentConfig() {
  try {
    const data = await fetchAPI('/api/agent/config');
    state.agentConfig = data;

    // Update Header status
    const pill = document.getElementById('agent-header-status');
    const thresholdEl = document.getElementById('agent-header-threshold');
    const ping = document.getElementById('agent-pulse-ping');
    const dot = document.getElementById('agent-pulse-dot');
    const modeTag = document.getElementById('dash-agent-mode-tag');

    if (data.is_autonomous) {
      pill.textContent = 'Autopilot Active';
      ping.className = 'animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75';
      dot.className = 'relative inline-flex rounded-full h-2 w-2 bg-emerald-500';
      if (modeTag) modeTag.textContent = 'Mode: Autonomous (Full Autopilot)';
    } else {
      pill.textContent = 'Copilot Armed';
      ping.className = 'animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75';
      dot.className = 'relative inline-flex rounded-full h-2 w-2 bg-indigo-500';
      if (modeTag) modeTag.textContent = 'Mode: Copilot (Approval Required)';
    }

    thresholdEl.textContent = `Threshold: ${data.min_fit_threshold}%`;

    const llmPill = document.getElementById('llm-status-pill');
    if (llmPill) {
      if (data.has_api_key) {
        llmPill.textContent = `Gemini (${data.model_name})`;
        llmPill.className = 'text-[10px] px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-400 border border-brand-500/30';
      } else {
        llmPill.textContent = 'Local Heuristic';
        llmPill.className = 'text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400';
      }
    }
  } catch (e) {}
}

async function loadJobs() {
  try {
    const search = document.getElementById('radar-search')?.value || '';
    const remoteOnly = document.getElementById('radar-remote-only')?.checked || false;
    const minScore = document.getElementById('radar-min-score')?.value || '';
    const source = document.getElementById('radar-source')?.value || '';

    const params = new URLSearchParams();
    if (search) params.append('q', search);
    if (remoteOnly) params.append('remote_only', 'true');
    if (minScore) params.append('min_score', minScore);
    if (source) params.append('source', source);

    const jobs = await fetchAPI(`/api/jobs?${params.toString()}`);
    state.jobs = jobs;

    const radarBadge = document.getElementById('badge-radar-count');
    if (radarBadge) radarBadge.textContent = jobs.length;

    renderRadarJobs();
    updateDashboardUI();
  } catch (e) {}
}

async function loadApplications() {
  try {
    const apps = await fetchAPI('/api/applications');
    state.applications = apps;

    const badge = document.getElementById('badge-kanban-count');
    if (badge) badge.textContent = apps.length;

    renderKanbanBoard();
    updateDashboardUI();
  } catch (e) {}
}

async function fetchActivityLogs() {
  try {
    const logs = await fetchAPI('/api/agent/logs?limit=40');
    state.logs = logs;
    renderActivityLogs();
  } catch (e) {}
}

async function fetchAnalytics() {
  try {
    const data = await fetchAPI('/api/analytics');
    state.analytics = data;
    renderAnalyticsView();
  } catch (e) {}
}

// ==================== DASHBOARD RENDERING ====================

function updateDashboardUI() {
  const totalJobs = state.jobs.length;
  const highMatches = state.jobs.filter(j => j.match && j.match.fit_score >= 80).length;
  const tailoredApps = state.applications.length;
  const interviews = state.applications.filter(a => a.status === 'interviewing').length;

  const avgAts = state.applications.length
    ? Math.round(state.applications.reduce((acc, a) => acc + (a.ats_score || 0), 0) / state.applications.length)
    : 0;

  document.getElementById('kpi-total-jobs').textContent = totalJobs;
  document.getElementById('kpi-high-matches').textContent = highMatches;
  document.getElementById('kpi-tailored-apps').textContent = tailoredApps;
  document.getElementById('kpi-interviews').textContent = interviews;
  document.getElementById('kpi-avg-ats').textContent = `${avgAts}%`;

  // Render top jobs on dashboard
  const container = document.getElementById('dashboard-top-jobs');
  if (!container) return;

  const topJobs = [...state.jobs]
    .sort((a, b) => ((b.match?.fit_score || 0) - (a.match?.fit_score || 0)))
    .slice(0, 4);

  if (topJobs.length === 0) {
    container.innerHTML = `<div class="p-6 text-center text-slate-500 text-xs">No jobs discovered yet. Click 'Run Agent Scout' to fetch opportunities.</div>`;
    return;
  }

  container.innerHTML = topJobs.map(job => {
    const score = job.match?.fit_score || 0;
    const badgeColor = score >= 80 ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
                       score >= 65 ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30' :
                       'bg-slate-800 text-slate-400 border-slate-700';

    const matched = job.match?.matched_skills?.slice(0, 4) || [];
    const missing = job.match?.missing_skills?.slice(0, 2) || [];

    return `
      <div class="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="space-y-1.5 flex-1">
          <div class="flex items-center gap-2.5 flex-wrap">
            <span class="font-semibold text-xs text-white">${job.title}</span>
            <span class="text-xs text-slate-400">• ${job.company}</span>
            <span class="text-[10px] px-2 py-0.5 rounded-full border ${badgeColor} font-bold">${score}% Match</span>
          </div>
          <div class="flex items-center gap-2 text-[11px] text-slate-400 flex-wrap">
            <span><i data-lucide="map-pin" class="w-3 h-3 inline"></i> ${job.location}</span>
            <span>•</span>
            <span>${job.salary_min ? `$${job.salary_min.toLocaleString()} - $${job.salary_max ? job.salary_max.toLocaleString() : ''}` : 'Competitive'}</span>
            <span>•</span>
            <span class="uppercase text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">${job.source}</span>
          </div>
          <div class="flex flex-wrap gap-1.5 pt-1">
            ${matched.map(s => `<span class="text-[10px] px-2 py-0.5 rounded-md bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">${s}</span>`).join('')}
            ${missing.map(s => `<span class="text-[10px] px-2 py-0.5 rounded-md bg-amber-950/40 text-amber-400 border border-amber-800/30">${s}</span>`).join('')}
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button onclick="openStudioForJob(${job.id})" class="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium flex items-center gap-1.5 transition-all">
            <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
            <span>Tailor Application</span>
          </button>
        </div>
      </div>
    `;
  }).join('');

  lucide.createIcons();
}

function renderActivityLogs() {
  const dashContainer = document.getElementById('dashboard-activity-stream');
  const fullContainer = document.getElementById('agent-full-logs');

  const logs = state.logs;

  if (dashContainer) {
    if (logs.length === 0) {
      dashContainer.innerHTML = `<div class="text-xs text-slate-500 text-center py-4">No agent logs recorded yet.</div>`;
    } else {
      dashContainer.innerHTML = logs.slice(0, 8).map(l => {
        const icon = l.category === 'scout' ? 'binoculars' :
                     l.category === 'match' ? 'target' :
                     l.category === 'tailor' ? 'file-edit' : 'cpu';
        const color = l.level === 'action' ? 'text-cyan-400' :
                      l.level === 'success' ? 'text-emerald-400' :
                      l.level === 'warning' ? 'text-amber-400' : 'text-slate-400';
        const time = l.timestamp ? new Date(l.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

        return `
          <div class="flex items-start gap-2.5 text-xs text-slate-300 pb-2 border-b border-slate-800/40">
            <i data-lucide="${icon}" class="w-3.5 h-3.5 shrink-0 mt-0.5 ${color}"></i>
            <div class="flex-1">
              <p class="leading-tight text-[11px]">${l.message}</p>
              <span class="text-[9px] text-slate-500">${time} • [${l.category}]</span>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  if (fullContainer) {
    if (logs.length === 0) {
      fullContainer.innerHTML = `<div class="text-slate-600 py-6 text-center">No terminal logs recorded yet.</div>`;
    } else {
      fullContainer.innerHTML = logs.map(l => {
        const time = l.timestamp ? new Date(l.timestamp).toISOString().split('T')[1].slice(0, 8) : '';
        const levelColor = l.level === 'success' ? 'text-emerald-400' :
                           l.level === 'action' ? 'text-cyan-400' :
                           l.level === 'warning' ? 'text-amber-400' : 'text-slate-400';

        return `
          <div class="flex items-start gap-2 leading-relaxed">
            <span class="text-slate-600 select-none">[${time}]</span>
            <span class="${levelColor} font-bold">[${l.category.toUpperCase()}]</span>
            <span class="text-slate-200 flex-1">${l.message}</span>
          </div>
        `;
      }).join('');
    }
  }

  lucide.createIcons();
}

// ==================== JOB RADAR VIEW ====================

function debounceSearchJobs() {
  clearTimeout(state.searchTimeout);
  state.searchTimeout = setTimeout(() => {
    loadJobs();
  }, 300);
}

function renderRadarJobs() {
  const container = document.getElementById('radar-jobs-list');
  if (!container) return;

  if (state.jobs.length === 0) {
    container.innerHTML = `
      <div class="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800 space-y-3">
        <i data-lucide="compass" class="w-10 h-10 mx-auto text-slate-600"></i>
        <h3 class="text-sm font-semibold text-slate-300">No matching job postings found</h3>
        <p class="text-xs text-slate-500 max-w-md mx-auto">Try loosening your filter parameters, or trigger an autonomous scout of live external feeds.</p>
        <button onclick="triggerScoutNow()" class="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-xs font-medium text-white inline-flex items-center gap-2">
          <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
          <span>Scout Feeds Now</span>
        </button>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = state.jobs.map(job => {
    const score = job.match?.fit_score || 0;
    const badgeColor = score >= 80 ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
                       score >= 65 ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30' :
                       'bg-slate-800 text-slate-400 border-slate-700';

    const matched = job.match?.matched_skills || [];
    const missing = job.match?.missing_skills || [];

    // Find if already applied
    const existingApp = state.applications.find(a => a.job_id === job.id);

    return `
      <div class="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 transition-all space-y-3">
        <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
          <div class="space-y-1">
            <div class="flex items-center gap-2.5 flex-wrap">
              <h3 class="font-bold text-sm text-white">${job.title}</h3>
              <span class="text-xs text-slate-400">• ${job.company}</span>
              <span class="text-xs px-2.5 py-0.5 rounded-full border ${badgeColor} font-bold">${score}% Match</span>
              ${existingApp ? `<span class="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 font-semibold uppercase">Pipeline: ${existingApp.status}</span>` : ''}
            </div>
            <div class="flex items-center gap-2 text-xs text-slate-400 flex-wrap">
              <span><i data-lucide="map-pin" class="w-3 h-3 inline"></i> ${job.location}</span>
              <span>•</span>
              <span>${job.salary_min ? `$${job.salary_min.toLocaleString()} - $${job.salary_max ? job.salary_max.toLocaleString() : ''}` : 'Compensation Unspecified'}</span>
              <span>•</span>
              <span class="px-2 py-0.5 rounded bg-slate-800 text-[10px] uppercase">${job.source}</span>
              ${job.url ? `<span>•</span><a href="${job.url}" target="_blank" class="text-brand-400 hover:underline flex items-center gap-1 text-xs"><span>View Portal</span><i data-lucide="external-link" class="w-3 h-3"></i></a>` : ''}
            </div>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <button onclick="openStudioForJob(${job.id})" class="px-3.5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium flex items-center gap-1.5 transition-all shadow-md shadow-brand-600/20">
              <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
              <span>${existingApp ? 'Open in Studio' : 'Tailor Application'}</span>
            </button>
            <button onclick="deleteJobPosting(${job.id})" class="p-2 rounded-xl hover:bg-slate-800 text-slate-500 hover:text-red-400 transition-colors" title="Delete job">
              <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
          </div>
        </div>

        <div class="text-xs text-slate-400 line-clamp-2 leading-relaxed">
          ${job.description.slice(0, 240)}...
        </div>

        <div class="pt-2 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-2">
          <div class="flex flex-wrap items-center gap-1.5">
            <span class="text-[10px] text-slate-500 font-semibold mr-1">ATS Breakdown:</span>
            ${matched.slice(0, 5).map(s => `<span class="text-[10px] px-2 py-0.5 rounded-md bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">${s}</span>`).join('')}
            ${missing.slice(0, 3).map(s => `<span class="text-[10px] px-2 py-0.5 rounded-md bg-amber-950/40 text-amber-400 border border-amber-800/30">${s}</span>`).join('')}
          </div>

          <div class="text-[11px] text-slate-500">
            Seniority: <span class="text-slate-300 capitalize">${job.match?.experience_match || 'Aligned'}</span>
          </div>
        </div>
      </div>
    `;
  }).join('');

  lucide.createIcons();
}

async function triggerScoutNow() {
  const btn = document.getElementById('btn-scout-feed');
  if (btn) btn.innerHTML = `<i data-lucide="refresh-cw" class="w-3.5 h-3.5 animate-spin"></i><span>Scouting...</span>`;
  lucide.createIcons();

  try {
    const res = await fetchAPI('/api/jobs/scout', { method: 'POST' });
    showToast(`Scouted ${res.fetched} listings (${res.new_jobs_added} new added)`, 'success');
    await loadJobs();
  } finally {
    if (btn) btn.innerHTML = `<i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i><span>Scout External Feeds</span>`;
    lucide.createIcons();
  }
}

async function deleteJobPosting(jobId) {
  if (!confirm('Are you sure you want to remove this job posting?')) return;
  try {
    await fetchAPI(`/api/jobs/${jobId}`, { method: 'DELETE' });
    showToast('Job posting removed', 'info');
    await loadJobs();
    await loadApplications();
  } catch (e) {}
}

// ==================== APPLICATION STUDIO ====================

function populateStudioDropdown() {
  const select = document.getElementById('studio-job-select');
  if (!select) return;

  if (state.jobs.length === 0) {
    select.innerHTML = `<option value="">No jobs available</option>`;
    return;
  }

  select.innerHTML = state.jobs.map(j => {
    const score = j.match?.fit_score || 0;
    return `<option value="${j.id}" ${state.selectedStudioJobId === j.id ? 'selected' : ''}>${score}% — ${j.title} (${j.company})</option>`;
  }).join('');

  if (!state.selectedStudioJobId && state.jobs.length > 0) {
    state.selectedStudioJobId = state.jobs[0].id;
  }

  onStudioJobChanged();
}

async function openStudioForJob(jobId) {
  state.selectedStudioJobId = jobId;
  switchTab('studio');
}

async function onStudioJobChanged() {
  const select = document.getElementById('studio-job-select');
  const jobId = parseInt(select.value);
  if (!jobId) return;

  state.selectedStudioJobId = jobId;
  const job = state.jobs.find(j => j.id === jobId);
  if (!job) return;

  // Render left job pane
  document.getElementById('studio-job-title').textContent = job.title;
  document.getElementById('studio-job-company').textContent = job.company;

  const score = job.match?.fit_score || 0;
  const badgeEl = document.getElementById('studio-fit-badge');
  badgeEl.textContent = `${score}% Match`;
  badgeEl.className = `px-2.5 py-1 rounded-lg text-xs font-bold ${
    score >= 80 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-300'
  }`;

  document.getElementById('studio-job-meta').innerHTML = `
    <span><i data-lucide="map-pin" class="w-3 h-3 inline"></i> ${job.location}</span>
    <span>•</span>
    <span>${job.salary_min ? `$${job.salary_min.toLocaleString()} - $${job.salary_max ? job.salary_max.toLocaleString() : ''}` : 'Competitive'}</span>
    <span>•</span>
    <span class="uppercase">${job.source}</span>
  `;

  document.getElementById('studio-job-desc').textContent = job.description;

  // Matched & Missing skills
  const matched = job.match?.matched_skills || [];
  const missing = job.match?.missing_skills || [];

  document.getElementById('studio-matched-skills').innerHTML = matched.length
    ? matched.map(s => `<span class="text-[10px] px-2 py-0.5 rounded-md bg-emerald-950 text-emerald-300 border border-emerald-800/50">${s}</span>`).join('')
    : '<span class="text-[10px] text-slate-500">None detected</span>';

  document.getElementById('studio-missing-skills').innerHTML = missing.length
    ? missing.map(s => `<span class="text-[10px] px-2 py-0.5 rounded-md bg-amber-950 text-amber-400 border border-amber-800/40">${s}</span>`).join('')
    : '<span class="text-[10px] text-emerald-400">Zero ATS gaps detected!</span>';

  // Check if tailored application already exists
  const existingApp = state.applications.find(a => a.job_id === jobId);
  if (existingApp && existingApp.tailored_resume) {
    renderStudioApplicationData(existingApp);
  } else {
    // Generate tailored package automatically
    await regenerateTailoredPackage();
  }

  lucide.createIcons();
}

function renderStudioApplicationData(data) {
  document.getElementById('studio-resume-editor').value = data.tailored_resume || '';
  document.getElementById('studio-cover-editor').value = data.cover_letter || '';
  document.getElementById('studio-resume-ats-tag').textContent = `ATS Score: ${data.ats_score || 92}%`;

  // Screening QA
  const qaContainer = document.getElementById('studio-qa-list');
  const qas = data.screening_qa || [];
  if (qas.length === 0) {
    qaContainer.innerHTML = `<div class="text-xs text-slate-500">No screening Q&A generated yet.</div>`;
  } else {
    qaContainer.innerHTML = qas.map((qa, idx) => `
      <div class="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
        <div class="flex items-start justify-between gap-2">
          <p class="text-xs font-semibold text-slate-200">${qa.question}</p>
          <button onclick="copyText('${escapeQuotes(qa.answer)}')" class="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-white shrink-0" title="Copy answer">
            <i data-lucide="copy" class="w-3.5 h-3.5"></i>
          </button>
        </div>
        <p class="text-xs text-slate-400 leading-relaxed bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">${qa.answer}</p>
      </div>
    `).join('');
  }

  lucide.createIcons();
}

async function regenerateTailoredPackage() {
  if (!state.selectedStudioJobId) return;
  const btn = document.getElementById('btn-studio-regenerate');
  if (btn) btn.innerHTML = `<i data-lucide="sparkles" class="w-3.5 h-3.5 animate-spin"></i><span>Synthesizing...</span>`;

  try {
    const res = await fetchAPI(`/api/tailor/${state.selectedStudioJobId}`, { method: 'POST' });
    showToast(`Tailored application package synthesized (ATS: ${res.ats_score}%)`, 'success');
    renderStudioApplicationData(res);
    await loadApplications();
  } finally {
    if (btn) btn.innerHTML = `<i data-lucide="sparkles" class="w-3.5 h-3.5 text-brand-400"></i><span>Re-Tailor with AI</span>`;
    lucide.createIcons();
  }
}

async function advanceJobFromStudio() {
  if (!state.selectedStudioJobId) return;
  const app = state.applications.find(a => a.job_id === state.selectedStudioJobId);
  if (app) {
    await fetchAPI(`/api/applications/${app.id}`, {
      method: 'PUT',
      body: JSON.stringify({ status: 'ready', notes: 'Reviewed and staged in studio.' })
    });
    showToast('Application marked as READY in pipeline!', 'success');
    await loadApplications();
  }
}

function switchStudioSubtab(subtab) {
  state.currentStudioSubtab = subtab;
  document.querySelectorAll('.studio-pill').forEach(el => el.classList.remove('active'));
  document.getElementById(`studio-subtab-${subtab}`)?.classList.add('active');

  document.querySelectorAll('.studio-pane').forEach(el => el.classList.add('hidden'));
  document.getElementById(`studio-content-${subtab}`)?.classList.remove('hidden');

  lucide.createIcons();
}

function copyCurrentStudioContent() {
  let content = '';
  if (state.currentStudioSubtab === 'resume') {
    content = document.getElementById('studio-resume-editor')?.value || '';
  } else if (state.currentStudioSubtab === 'cover') {
    content = document.getElementById('studio-cover-editor')?.value || '';
  } else if (state.currentStudioSubtab === 'interview') {
    content = document.getElementById('studio-interview-guide')?.textContent || '';
  }
  if (content) {
    copyText(content);
    showToast('Copied content to clipboard', 'info');
  }
}

function downloadStudioContent() {
  let content = '';
  let filename = 'document.md';
  const job = state.jobs.find(j => j.id === state.selectedStudioJobId);
  const companySlug = job ? job.company.toLowerCase().replace(/[^a-z0-9]/g, '_') : 'job';

  if (state.currentStudioSubtab === 'resume') {
    content = document.getElementById('studio-resume-editor')?.value || '';
    filename = `resume_${companySlug}.md`;
  } else if (state.currentStudioSubtab === 'cover') {
    content = document.getElementById('studio-cover-editor')?.value || '';
    filename = `cover_letter_${companySlug}.txt`;
  } else if (state.currentStudioSubtab === 'interview') {
    content = document.getElementById('studio-interview-guide')?.textContent || '';
    filename = `interview_prep_${companySlug}.md`;
  }

  if (!content) return;
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  showToast(`Downloaded ${filename}`, 'success');
}

async function fetchInterviewPrepGuide() {
  if (!state.selectedStudioJobId) return;
  const guideEl = document.getElementById('studio-interview-guide');
  guideEl.textContent = 'Synthesizing strategic STAR-method interview guide...';

  try {
    const res = await fetchAPI(`/api/tailor/${state.selectedStudioJobId}/interview-prep`, { method: 'POST' });
    guideEl.textContent = res.guide;
    showToast('Interview prep guide synthesized!', 'success');
  } catch (e) {
    guideEl.textContent = 'Failed to generate guide.';
  }
}

// ==================== KANBAN BOARD ====================

function renderKanbanBoard() {
  const columns = ['discovered', 'tailored', 'ready', 'applied', 'interviewing', 'offer'];

  columns.forEach(col => {
    const colContainer = document.getElementById(`cards-${col}`);
    const countEl = document.getElementById(`count-col-${col}`);
    if (!colContainer) return;

    let items = [];
    if (col === 'discovered') {
      // Jobs that don't have an application record or status is discovered
      const appJobIds = new Set(state.applications.map(a => a.job_id));
      const unappliedJobs = state.jobs.filter(j => !appJobIds.has(j.id));
      items = unappliedJobs.map(j => ({ isJobOnly: true, job: j }));
    } else {
      items = state.applications.filter(a => a.status === col);
    }

    if (countEl) countEl.textContent = items.length;

    if (items.length === 0) {
      colContainer.innerHTML = `<div class="p-4 text-center text-slate-600 text-[11px] border border-dashed border-slate-800/80 rounded-xl">Empty</div>`;
      return;
    }

    colContainer.innerHTML = items.map(item => {
      if (item.isJobOnly) {
        const job = item.job;
        const score = job.match?.fit_score || 0;
        return `
          <div class="kanban-card p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div class="flex items-start justify-between gap-1">
              <span class="font-semibold text-xs text-white leading-tight">${job.title}</span>
              <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">${score}%</span>
            </div>
            <p class="text-[11px] text-slate-400">${job.company}</p>
            <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between">
              <span class="text-[10px] text-slate-500">${job.location}</span>
              <button onclick="openStudioForJob(${job.id})" class="text-[11px] text-brand-400 hover:underline flex items-center gap-1 font-medium">
                <span>Tailor</span>
                <i data-lucide="chevron-right" class="w-3 h-3"></i>
              </button>
            </div>
          </div>
        `;
      }

      const app = item;
      const job = app.job || {};
      const atsScore = app.ats_score || 90;

      return `
        <div class="kanban-card p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2.5">
          <div class="flex items-start justify-between gap-1">
            <span class="font-semibold text-xs text-white leading-tight">${job.title || 'Application'}</span>
            <span class="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">ATS: ${atsScore}%</span>
          </div>
          <p class="text-[11px] text-slate-400">${job.company || 'Company'}</p>

          ${app.interview_date ? `
            <div class="px-2 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-[10px] text-amber-300 flex items-center gap-1">
              <i data-lucide="calendar" class="w-3 h-3"></i>
              <span>${new Date(app.interview_date).toLocaleDateString()}</span>
            </div>
          ` : ''}

          <div class="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-1">
            <button onclick="openStudioForJob(${app.job_id})" class="text-[11px] text-slate-400 hover:text-white flex items-center gap-1">
              <i data-lucide="eye" class="w-3 h-3"></i>
              <span>Studio</span>
            </button>

            <!-- Quick Advance Menu -->
            <select onchange="changeAppStatus(${app.id}, this.value)" class="text-[10px] px-1.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300 focus:outline-none">
              <option value="" disabled selected>Move &rsaquo;</option>
              <option value="tailored">Tailored</option>
              <option value="ready">Ready</option>
              <option value="applied">Applied</option>
              <option value="interviewing">Interview</option>
              <option value="offer">Offer Won</option>
            </select>
          </div>
        </div>
      `;
    }).join('');
  });

  const totalInFlight = state.applications.length;
  document.getElementById('kanban-total-stat').textContent = `${totalInFlight} Applications In Flight`;
  lucide.createIcons();
}

async function changeAppStatus(appId, newStatus) {
  try {
    let payload = { status: newStatus };
    if (newStatus === 'interviewing') {
      const dateStr = prompt('Enter Interview Date & Time (YYYY-MM-DD):', new Date().toISOString().split('T')[0]);
      if (dateStr) {
        payload.interview_date = `${dateStr}T14:00:00Z`;
      }
    }
    await fetchAPI(`/api/applications/${appId}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
    showToast(`Advanced to ${newStatus.toUpperCase()}`, 'success');
    await loadApplications();
  } catch (e) {}
}

// ==================== CAREER DNA / PROFILE ====================

function populateProfileForm() {
  const p = state.profile;
  if (!p) return;

  document.getElementById('prof-name').value = p.full_name || '';
  document.getElementById('prof-email').value = p.email || '';
  document.getElementById('prof-phone').value = p.phone || '';
  document.getElementById('prof-location').value = p.location || '';
  document.getElementById('prof-portfolio').value = p.portfolio_url || '';
  document.getElementById('prof-linkedin').value = p.linkedin_url || '';
  document.getElementById('prof-github').value = p.github_url || '';
  document.getElementById('prof-min-salary').value = p.min_salary || 120000;
  document.getElementById('prof-years-exp').value = p.experience_years || 5;
  document.getElementById('prof-remote-pref').value = p.remote_preference || 'remote';
  document.getElementById('prof-bio').value = p.bio_summary || '';
  document.getElementById('prof-target-roles').value = (p.target_roles || []).join(', ');
  document.getElementById('prof-skills').value = (p.skills || []).join(', ');
  document.getElementById('prof-excluded').value = (p.excluded_keywords || []).join(', ');

  renderWorkExperienceList(p.work_experience || []);
  lucide.createIcons();
}

function renderWorkExperienceList(expList) {
  const container = document.getElementById('prof-experience-list');
  if (!container) return;

  container.innerHTML = expList.map((exp, idx) => `
    <div class="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2 exp-item" data-idx="${idx}">
      <div class="flex items-center justify-between gap-2">
        <div class="grid grid-cols-3 gap-2 flex-1">
          <input type="text" value="${escapeQuotes(exp.role)}" placeholder="Role" class="exp-role px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white">
          <input type="text" value="${escapeQuotes(exp.company)}" placeholder="Company" class="exp-company px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white">
          <input type="text" value="${escapeQuotes(exp.period)}" placeholder="Period" class="exp-period px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-white">
        </div>
        <button onclick="removeWorkExperienceItem(${idx})" class="p-1.5 rounded-lg hover:bg-slate-800 text-slate-500 hover:text-red-400">
          <i data-lucide="trash" class="w-3.5 h-3.5"></i>
        </button>
      </div>
      <div>
        <label class="text-[10px] text-slate-500 block mb-1">Key Impact Highlights (one per line)</label>
        <textarea rows="3" class="exp-highlights w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300 leading-relaxed">${(exp.highlights || []).join('\n')}</textarea>
      </div>
    </div>
  `).join('');

  lucide.createIcons();
}

function addWorkExperienceItem() {
  const currentExp = collectWorkExperienceItems();
  currentExp.unshift({
    company: 'New Organization',
    role: 'Senior Software Engineer',
    period: '2024 - Present',
    highlights: ['Led engineering initiative delivering high impact.']
  });
  renderWorkExperienceList(currentExp);
}

function removeWorkExperienceItem(idx) {
  const currentExp = collectWorkExperienceItems();
  currentExp.splice(idx, 1);
  renderWorkExperienceList(currentExp);
}

function collectWorkExperienceItems() {
  const items = [];
  document.querySelectorAll('.exp-item').forEach(el => {
    const role = el.querySelector('.exp-role')?.value || '';
    const company = el.querySelector('.exp-company')?.value || '';
    const period = el.querySelector('.exp-period')?.value || '';
    const rawHighlights = el.querySelector('.exp-highlights')?.value || '';
    const highlights = rawHighlights.split('\n').map(h => h.trim()).filter(Boolean);

    items.push({ role, company, period, highlights });
  });
  return items;
}

async function saveCandidateProfile() {
  const targetRoles = document.getElementById('prof-target-roles').value.split(',').map(s => s.trim()).filter(Boolean);
  const skills = document.getElementById('prof-skills').value.split(',').map(s => s.trim()).filter(Boolean);
  const excluded = document.getElementById('prof-excluded').value.split(',').map(s => s.trim()).filter(Boolean);

  const payload = {
    full_name: document.getElementById('prof-name').value,
    email: document.getElementById('prof-email').value,
    phone: document.getElementById('prof-phone').value,
    location: document.getElementById('prof-location').value,
    portfolio_url: document.getElementById('prof-portfolio').value,
    linkedin_url: document.getElementById('prof-linkedin').value,
    github_url: document.getElementById('prof-github').value,
    min_salary: parseInt(document.getElementById('prof-min-salary').value) || 120000,
    experience_years: parseFloat(document.getElementById('prof-years-exp').value) || 5,
    remote_preference: document.getElementById('prof-remote-pref').value,
    bio_summary: document.getElementById('prof-bio').value,
    target_roles: targetRoles,
    skills: skills,
    excluded_keywords: excluded,
    work_experience: collectWorkExperienceItems(),
    education: state.profile?.education || []
  };

  try {
    const res = await fetchAPI('/api/profile', {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
    state.profile = res.profile;
    showToast('Career DNA updated successfully! Scoring refreshed.', 'success');
    await fetchProfile();
    await loadJobs();
  } catch (e) {}
}

// ==================== AGENT CONTROLS ====================

function populateAgentConfigForm() {
  const c = state.agentConfig;
  if (!c) return;

  if (c.is_autonomous) {
    document.getElementById('mode-autonomous').checked = true;
  } else {
    document.getElementById('mode-copilot').checked = true;
  }

  document.getElementById('agent-threshold-slider').value = c.min_fit_threshold || 75;
  document.getElementById('slider-threshold-val').textContent = `${c.min_fit_threshold || 75}%`;
  document.getElementById('agent-auto-tailor').checked = Boolean(c.auto_tailor);
  document.getElementById('agent-auto-apply').checked = Boolean(c.auto_apply);
  document.getElementById('agent-api-key').value = c.gemini_api_key || '';
  document.getElementById('agent-model-name').value = c.model_name || 'gemini-2.5-flash';
}

async function saveAgentSettings() {
  const isAutonomous = document.getElementById('mode-autonomous').checked;
  const threshold = parseInt(document.getElementById('agent-threshold-slider').value);
  const autoTailor = document.getElementById('agent-auto-tailor').checked;
  const autoApply = document.getElementById('agent-auto-apply').checked;
  const apiKey = document.getElementById('agent-api-key').value.trim();
  const modelName = document.getElementById('agent-model-name').value;

  const payload = {
    is_autonomous: isAutonomous,
    min_fit_threshold: threshold,
    auto_tailor: autoTailor,
    auto_apply: autoApply,
    gemini_api_key: apiKey,
    model_name: modelName
  };

  try {
    await fetchAPI('/api/agent/config', {
      method: 'PUT',
      body: JSON.stringify(payload)
    });
    showToast('Agent configuration updated!', 'success');
    await fetchAgentConfig();
  } catch (e) {}
}

async function triggerAgentCycle() {
  const btn = document.getElementById('btn-quick-run-agent');
  if (btn) btn.innerHTML = `<i data-lucide="play" class="w-3.5 h-3.5 animate-spin"></i><span>Running...</span>`;
  lucide.createIcons();

  try {
    const res = await fetchAPI('/api/agent/run', { method: 'POST' });
    showToast(res.summary, 'success');
    await Promise.all([
      loadJobs(),
      loadApplications(),
      fetchActivityLogs(),
      fetchAnalytics()
    ]);
  } finally {
    if (btn) btn.innerHTML = `<i data-lucide="play" class="w-3.5 h-3.5 fill-current"></i><span>Run Agent Scout</span>`;
    lucide.createIcons();
  }
}

async function clearLogs() {
  try {
    await fetchAPI('/api/agent/logs', { method: 'DELETE' });
    showToast('Logs cleared', 'info');
    await fetchActivityLogs();
  } catch (e) {}
}

// ==================== MARKET INTEL & ANALYTICS ====================

function renderAnalyticsView() {
  const a = state.analytics;
  if (!a) return;

  const skillsContainer = document.getElementById('analytics-skills-list');
  const gapsContainer = document.getElementById('analytics-gaps-list');

  if (skillsContainer) {
    const topSkills = a.top_market_skills || [];
    const maxCount = topSkills[0]?.count || 1;

    skillsContainer.innerHTML = topSkills.map(s => {
      const pct = Math.round((s.count / maxCount) * 100);
      const isOwned = s.has_skill;

      return `
        <div class="space-y-1">
          <div class="flex items-center justify-between text-xs">
            <span class="font-medium text-slate-200 flex items-center gap-1.5">
              <span>${s.skill}</span>
              ${isOwned ? '<span class="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300">In Your DNA</span>' : ''}
            </span>
            <span class="text-slate-400 font-mono text-[11px]">${s.count} postings</span>
          </div>
          <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
            <div class="h-full rounded-full ${isOwned ? 'bg-emerald-500' : 'bg-brand-500'}" style="width: ${pct}%"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  if (gapsContainer) {
    const gaps = a.top_missing_skills || [];
    if (gaps.length === 0) {
      gapsContainer.innerHTML = `<div class="text-xs text-emerald-400 py-4">Great news: You possess all high-frequency market skills!</div>`;
    } else {
      gapsContainer.innerHTML = gaps.map(g => `
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between">
          <div>
            <p class="text-xs font-semibold text-amber-300">${g.skill}</p>
            <p class="text-[10px] text-slate-500">Requested in ${g.count} target postings</p>
          </div>
          <button onclick="addSkillToProfile('${g.skill}')" class="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-slate-300 flex items-center gap-1">
            <i data-lucide="plus" class="w-3 h-3"></i>
            <span>Add to DNA</span>
          </button>
        </div>
      `).join('');
    }
  }

  lucide.createIcons();
}

async function addSkillToProfile(skill) {
  if (!state.profile) return;
  const skills = [...state.profile.skills];
  if (!skills.includes(skill)) {
    skills.push(skill);
    state.profile.skills = skills;
    await fetchAPI('/api/profile', {
      method: 'PUT',
      body: JSON.stringify(state.profile)
    });
    showToast(`Added ${skill} to your skills! Recalculating matches...`, 'success');
    await loadJobs();
    await fetchAnalytics();
  }
}

// ==================== MODAL IMPORT CUSTOM JOB ====================

function openCustomJobModal() {
  document.getElementById('modal-custom-job').classList.remove('hidden');
  lucide.createIcons();
}

function closeCustomJobModal() {
  document.getElementById('modal-custom-job').classList.add('hidden');
}

async function submitCustomJob() {
  const title = document.getElementById('modal-job-title').value.trim();
  const company = document.getElementById('modal-job-company').value.trim();
  const location = document.getElementById('modal-job-location').value.trim();
  const salMin = parseInt(document.getElementById('modal-job-sal-min').value) || null;
  const salMax = parseInt(document.getElementById('modal-job-sal-max').value) || null;
  const url = document.getElementById('modal-job-url').value.trim();
  const desc = document.getElementById('modal-job-desc').value.trim();

  if (!title || !company || !desc) {
    showToast('Title, company, and description are required', 'error');
    return;
  }

  const payload = {
    title,
    company,
    location: location || 'Remote',
    is_remote: location.toLowerCase().includes('remote'),
    salary_min: salMin,
    salary_max: salMax,
    url,
    description: desc,
    source: 'manual_import'
  };

  try {
    const res = await fetchAPI('/api/jobs', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
    closeCustomJobModal();
    showToast(`Job imported! Fit score: ${res.job.match?.fit_score || '--'}%`, 'success');
    await loadJobs();
    if (res.job) {
      openStudioForJob(res.job.id);
    }
  } catch (e) {}
}

// ==================== UTILITIES ====================

function copyText(text) {
  navigator.clipboard.writeText(text);
}

function escapeQuotes(str) {
  if (!str) return '';
  return str.replace(/"/g, '&quot;');
}
