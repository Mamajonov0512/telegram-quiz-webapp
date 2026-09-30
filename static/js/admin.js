/**
 * Admin Dashboard JavaScript
 * Handles overview stats, user whitelist, file upload, and settings
 */

let adminKey = localStorage.getItem('admin_secret_key') || 'admin12345';
let cachedUsers = [];

document.addEventListener('DOMContentLoaded', () => {
  const keyInput = document.getElementById('adminKeyInput');
  if (keyInput) keyInput.value = adminKey;

  // Setup drag & drop
  setupDropZone();

  // Load initial tab
  loadOverviewData();
});

function saveAdminKey() {
  const input = document.getElementById('adminKeyInput');
  if (input) {
    adminKey = input.value.trim();
    localStorage.setItem('admin_secret_key', adminKey);
    alert("Admin kaliti saqlandi!");
    loadOverviewData();
  }
}

function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-Admin-Key': adminKey
  };
}

// --- TAB SWITCHING ---
function switchTab(tabId) {
  const tabs = ['overview', 'analytics', 'users', 'questions', 'results'];
  tabs.forEach(t => {
    const el = document.getElementById(`${t}Tab`);
    if (el) el.style.display = (t === tabId) ? 'block' : 'none';
  });

  const buttons = document.querySelectorAll('.nav-btn');
  buttons.forEach(btn => {
    if (btn.getAttribute('onclick')?.includes(`'${tabId}'`)) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  if (tabId === 'overview') loadOverviewData();
  else if (tabId === 'analytics') loadAnalyticsData();
  else if (tabId === 'users') loadUsersData();
  else if (tabId === 'questions') {
    loadQuestionsData();
    loadCategoriesManagement();
  }
  else if (tabId === 'results') loadResultsData();
}

// --- TAB 1: OVERVIEW & SETTINGS ---
async function loadOverviewData() {
  try {
    const res = await fetch('/api/admin/stats', { headers: { 'X-Admin-Key': adminKey } });
    if (!res.ok) {
      if (res.status === 401) alert("Admin kaliti noto'g'ri! Iltimos, chap pastdagi maydonga to'g'ri kalitni kiriting.");
      return;
    }

    const data = await res.json();
    const stats = data.stats;
    const settings = data.settings;

    document.getElementById('metricTotalQuestions').innerText = stats.total_questions;
    document.getElementById('metricTotalUsers').innerText = stats.total_users;
    document.getElementById('metricTotalTests').innerText = stats.total_tests_taken;
    document.getElementById('metricAvgScore').innerText = `${stats.avg_score}%`;

    // Populate settings
    if (settings) {
      document.getElementById('settingQuestionCount').value = settings.questions_per_test || 50;
      if (document.getElementById('settingMaxQuestionsLimit')) {
        document.getElementById('settingMaxQuestionsLimit').value = settings.max_questions_limit || 500;
      }
      document.getElementById('settingDuration').value = settings.duration_minutes || 50;
      document.getElementById('settingPassPercent').value = settings.pass_percentage || 60;
      document.getElementById('settingWhitelistToggle').checked = (settings.whitelist_enabled === 'true');
      
      const catToggle = document.getElementById('settingCategoryFilterToggle');
      if (catToggle) catToggle.checked = (settings.category_filter_enabled !== 'false');

      const shufQToggle = document.getElementById('settingShuffleQuestionsToggle');
      if (shufQToggle) shufQToggle.checked = (settings.shuffle_questions !== 'false');

      const shufOToggle = document.getElementById('settingShuffleOptionsToggle');
      if (shufOToggle) shufOToggle.checked = (settings.shuffle_options !== 'false');

      const cheatToggle = document.getElementById('settingAntiCheatToggle');
      if (cheatToggle) cheatToggle.checked = (settings.anti_cheat_enabled !== 'false');
    }
  } catch (err) {
    console.error("Overview load error:", err);
  }
}

async function saveSettings() {
  const questions_per_test = parseInt(document.getElementById('settingQuestionCount').value, 10);
  const max_questions_limit = parseInt(document.getElementById('settingMaxQuestionsLimit')?.value || '500', 10);
  const duration_minutes = parseInt(document.getElementById('settingDuration').value, 10);
  const pass_percentage = parseInt(document.getElementById('settingPassPercent').value, 10);
  const whitelist_enabled = document.getElementById('settingWhitelistToggle').checked;
  const category_filter_enabled = document.getElementById('settingCategoryFilterToggle')?.checked ?? true;
  const shuffle_questions = document.getElementById('settingShuffleQuestionsToggle')?.checked ?? true;
  const shuffle_options = document.getElementById('settingShuffleOptionsToggle')?.checked ?? true;
  const anti_cheat_enabled = document.getElementById('settingAntiCheatToggle')?.checked ?? true;

  try {
    const res = await fetch('/api/admin/settings', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        questions_per_test,
        max_questions_limit,
        duration_minutes,
        pass_percentage,
        whitelist_enabled,
        category_filter_enabled,
        shuffle_questions,
        shuffle_options,
        anti_cheat_enabled
      })
    });

    if (res.ok) {
      alert("✅ Barcha sozlamalar muvaffaqiyatli saqlandi!");
    } else {
      alert("❌ Xatolik yuz berdi!");
    }
  } catch (err) {
    alert("Server bilan ulanishda xatolik: " + err.message);
  }
}

// --- TAB: DETAILED ANALYTICS ---
async function loadAnalyticsData() {
  try {
    const res = await fetch('/api/admin/analytics', { headers: { 'X-Admin-Key': adminKey } });
    if (!res.ok) return;

    const data = await res.json();
    const a = data.analytics;

    // 1. KPI Cards
    document.getElementById('anAvgScore').innerText = `${a.avg_score}%`;
    document.getElementById('anPassRate').innerText = `${a.pass_rate}%`;
    document.getElementById('anPassCountDetail').innerText = `${a.pass_count} ta o'tdi / ${a.fail_count} ta o'tmadi`;
    document.getElementById('anAvgTime').innerText = `${a.avg_time_min} daq`;
    document.getElementById('anUniqueUsers').innerText = `${a.unique_users} nafar`;
    document.getElementById('anTotalTestsDetail').innerText = `Jami ${a.total_tests} ta urinish`;

    // 2. Score Distribution
    const distContainer = document.getElementById('distributionBars');
    const totalT = Math.max(1, a.total_tests);
    const d = a.score_distribution;

    const brackets = [
      { label: "80 - 100% (A'lo daraja)", count: d['80-100'] || 0, color: "var(--success)" },
      { label: "60 - 79% (Yaxshi / O'tdi)", count: d['60-79'] || 0, color: "var(--primary)" },
      { label: "40 - 59% (Past / O'tmadi)", count: d['40-59'] || 0, color: "var(--warning)" },
      { label: "0 - 39% (Qoniqarsiz)", count: d['0-39'] || 0, color: "var(--danger)" }
    ];

    distContainer.innerHTML = '';
    brackets.forEach(b => {
      const pct = Math.round((b.count / totalT) * 100);
      const row = document.createElement('div');
      row.style.marginBottom = '14px';
      row.innerHTML = `
        <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px;">
          <span>${b.label}</span>
          <strong>${b.count} ta (${pct}%)</strong>
        </div>
        <div style="height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
          <div style="height: 100%; width: ${pct}%; background: ${b.color}; border-radius: 4px; transition: width 0.4s ease;"></div>
        </div>
      `;
      distContainer.appendChild(row);
    });

    // 3. Category Performance Table
    const catTbody = document.getElementById('categoryTableBody');
    catTbody.innerHTML = '';
    if (!a.category_performance || a.category_performance.length === 0) {
      catTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">Ma'lumotlar yo'q</td></tr>`;
    } else {
      a.category_performance.forEach(c => {
        const color = c.accuracy_percentage >= 80 ? 'var(--success)' : (c.accuracy_percentage >= 60 ? 'var(--primary)' : 'var(--danger)');
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${escapeHtml(c.category)}</strong></td>
          <td>${c.total_questions} ta</td>
          <td>${c.correct_answers} ta</td>
          <td>
            <span style="font-weight: 700; color: ${color};">
              ${c.accuracy_percentage}%
            </span>
          </td>
        `;
        catTbody.appendChild(tr);
      });
    }

    // 4. Hardest Questions
    const hardTbody = document.getElementById('hardestQuestionsBody');
    hardTbody.innerHTML = '';
    if (!a.hardest_questions || a.hardest_questions.length === 0) {
      hardTbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Hozircha xato qilingan savollar yo'q</td></tr>`;
    } else {
      a.hardest_questions.forEach((q, idx) => {
        const tr = document.createElement('tr');
        const badgeColor = q.error_rate >= 70 ? 'var(--danger)' : (q.error_rate >= 50 ? 'var(--warning)' : 'var(--text-muted)');
        tr.innerHTML = `
          <td>${idx + 1}</td>
          <td><strong>${escapeHtml(q.question)}</strong></td>
          <td><span style="font-size: 11px; background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px;">${escapeHtml(q.category)}</span></td>
          <td>${q.total_answered} marta</td>
          <td><strong style="color: var(--danger);">${q.wrong_count} marta</strong></td>
          <td>
            <span style="display: inline-block; padding: 4px 8px; border-radius: 6px; font-weight: 700; font-size: 12px; background: rgba(239, 68, 68, 0.15); color: ${badgeColor};">
              ${q.error_rate}% xato
            </span>
          </td>
        `;
        hardTbody.appendChild(tr);
      });
    }

    // 5. Leaderboard
    const lbBody = document.getElementById('leaderboardBody');
    lbBody.innerHTML = '';
    if (!a.leaderboard || a.leaderboard.length === 0) {
      lbBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">Yetakchilar mavjud emas</td></tr>`;
    } else {
      const medals = ["🥇 1", "🥈 2", "🥉 3"];
      a.leaderboard.forEach((u, idx) => {
        const tr = document.createElement('tr');
        const rankText = idx < 3 ? medals[idx] : `${idx + 1}`;
        tr.innerHTML = `
          <td><strong>${rankText}</strong></td>
          <td><strong>${escapeHtml(u.full_name || '—')}</strong></td>
          <td><code>${u.telegram_id}</code></td>
          <td>${u.username ? '@' + escapeHtml(u.username) : '—'}</td>
          <td>${u.attempts_count} ta</td>
          <td><strong style="color: var(--success);">${u.best_score}%</strong></td>
          <td><strong style="color: var(--primary);">${u.avg_score}%</strong></td>
        `;
        lbBody.appendChild(tr);
      });
    }

  } catch (err) {
    console.error("Analytics load error:", err);
  }
}

function downloadExcelReport() {
  window.location.href = `/api/admin/export/excel?key=${encodeURIComponent(adminKey)}`;
}

// --- TAB 2: USERS (WHITELIST) ---
async function loadUsersData() {
  try {
    const res = await fetch('/api/admin/users', { headers: { 'X-Admin-Key': adminKey } });
    if (!res.ok) return;

    const data = await res.json();
    cachedUsers = data.users || [];
    renderUsersTable(cachedUsers);
  } catch (err) {
    console.error("Users load error:", err);
  }
}

function renderUsersTable(users) {
  const tbody = document.getElementById('usersTableBody');
  document.getElementById('usersTableCount').innerText = users.length;
  tbody.innerHTML = '';

  if (users.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">Hozircha ruxsat berilgan foydalanuvchilar yo'q.</td></tr>`;
    return;
  }

  users.forEach(u => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${u.telegram_id}</strong></td>
      <td>${escapeHtml(u.full_name || '—')}</td>
      <td>${u.username ? '@' + escapeHtml(u.username) : '—'}</td>
      <td style="color: var(--text-muted); font-size: 12px;">${u.added_at ? u.added_at.slice(0, 16) : '—'}</td>
      <td>
        <label class="switch">
          <input type="checkbox" ${u.is_active ? 'checked' : ''} onchange="toggleUser(${u.telegram_id}, this.checked)">
          <span class="slider"></span>
        </label>
      </td>
      <td>
        <button class="btn btn-outline btn-danger" style="padding: 4px 8px; font-size: 12px;" onclick="deleteUser(${u.telegram_id})">
          🗑️ O'chirish
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function filterUsers() {
  const q = document.getElementById('userSearchInput').value.toLowerCase().trim();
  if (!q) {
    renderUsersTable(cachedUsers);
    return;
  }
  const filtered = cachedUsers.filter(u => 
    u.telegram_id.toString().includes(q) || 
    (u.full_name && u.full_name.toLowerCase().includes(q)) ||
    (u.username && u.username.toLowerCase().includes(q))
  );
  renderUsersTable(filtered);
}

async function addUser() {
  const idInput = document.getElementById('newUserId');
  const nameInput = document.getElementById('newUserName');
  const notesInput = document.getElementById('newUserNotes');

  const idVal = parseInt(idInput.value.trim(), 10);
  if (!idVal || isNaN(idVal)) {
    alert("Iltimos, to'g'ri Telegram ID raqamini kiriting!");
    return;
  }

  try {
    const res = await fetch('/api/admin/users/add', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        telegram_id: idVal,
        full_name: nameInput.value.trim(),
        notes: notesInput.value.trim()
      })
    });

    if (res.ok) {
      alert("✅ Foydalanuvchi qo'shildi!");
      idInput.value = '';
      nameInput.value = '';
      notesInput.value = '';
      loadUsersData();
    } else {
      alert("Xatolik yuz berdi!");
    }
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
}

async function toggleUser(id, isActive) {
  try {
    await fetch('/api/admin/users/toggle', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ telegram_id: id, is_active: isActive })
    });
  } catch (err) {
    console.error("Toggle error:", err);
  }
}

async function deleteUser(id) {
  if (!confirm(`Haqiqatan ham ID ${id} ni ruxsat ro'yxatidan o'chirmoqchimisiz?`)) return;

  try {
    const res = await fetch('/api/admin/users/remove', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ telegram_id: id })
    });
    if (res.ok) {
      loadUsersData();
    }
  } catch (err) {
    alert("O'chirishda xatolik: " + err.message);
  }
}

// --- TAB 3: QUESTIONS & FILE UPLOAD ---
function setupDropZone() {
  const dropZone = document.getElementById('dropZone');
  if (!dropZone) return;

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  dropZone.addEventListener('dragover', () => dropZone.style.borderColor = 'var(--primary)');
  dropZone.addEventListener('dragleave', () => dropZone.style.borderColor = 'rgba(59, 130, 246, 0.4)');
  dropZone.addEventListener('drop', (e) => {
    dropZone.style.borderColor = 'rgba(59, 130, 246, 0.4)';
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadFile(files[0]);
  });
}

function handleFileSelect(e) {
  const files = e.target.files;
  if (files.length > 0) uploadFile(files[0]);
}

async function uploadFile(file) {
  const statusBox = document.getElementById('uploadStatusBox');
  statusBox.style.display = 'block';
  statusBox.style.background = 'rgba(59, 130, 246, 0.15)';
  statusBox.style.color = 'var(--primary)';
  statusBox.innerText = `⏳ "${file.name}" fayli yuklanmoqda va tahlil qilinmoqda...`;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/admin/upload', {
      method: 'POST',
      headers: {
        'X-Admin-Key': adminKey
      },
      body: formData
    });

    const data = await res.json();
    if (res.ok && data.success) {
      statusBox.style.background = 'rgba(16, 185, 129, 0.15)';
      statusBox.style.color = 'var(--success)';
      statusBox.innerHTML = `
        ✅ <strong>Muvaffaqiyatli!</strong> Fayldan <strong>${data.parsed_count} ta</strong> savol aniqlandi va <strong>${data.saved_count} ta</strong> savol bazaga saqlandi. Jami savollar: ${data.total_questions} ta.
      `;
      loadQuestionsData();
    } else {
      statusBox.style.background = 'rgba(239, 68, 68, 0.15)';
      statusBox.style.color = 'var(--danger)';
      const errList = data.errors ? data.errors.join('<br>') : (data.detail || "Faylni tahlil qilishda xatolik yuz berdi");
      statusBox.innerHTML = `❌ <strong>Xatolik:</strong><br>${errList}`;
    }
  } catch (err) {
    statusBox.style.background = 'rgba(239, 68, 68, 0.15)';
    statusBox.style.color = 'var(--danger)';
    statusBox.innerText = "Yuklashda tarmoq xatoligi: " + err.message;
  }
}

async function loadQuestionsData() {
  try {
    const res = await fetch('/api/admin/questions?limit=100', { headers: { 'X-Admin-Key': adminKey } });
    if (!res.ok) return;

    const data = await res.json();
    const tbody = document.getElementById('questionsTableBody');
    document.getElementById('questionsTableCount').innerText = data.total;
    tbody.innerHTML = '';

    if (!data.questions || data.questions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">Bazada hozircha savollar yo'q.</td></tr>`;
      return;
    }

    data.questions.forEach((q, idx) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td><strong>${escapeHtml(q.question_text)}</strong></td>
        <td style="font-size: 12px; color: var(--text-muted);">
          A: ${escapeHtml(q.option_a)}<br>
          B: ${escapeHtml(q.option_b)}<br>
          C: ${escapeHtml(q.option_c)}<br>
          D: ${escapeHtml(q.option_d)}
        </td>
        <td><strong style="color: var(--success);">${q.correct_option}</strong></td>
        <td>
          <span style="font-size: 12px; background: rgba(59,130,246,0.15); color: var(--primary); padding: 4px 8px; border-radius: 6px; cursor: pointer; border: 1px solid rgba(59,130,246,0.3); display: inline-block;" title="Fanni o'zgartirish uchun bosing" onclick="editSingleCategory(${q.id}, '${escapeHtml(q.category || 'Umumiy')}')">
            ✏️ ${escapeHtml(q.category || 'Umumiy')}
          </span>
        </td>
        <td>
          <button class="btn btn-outline btn-danger" style="padding: 4px 8px; font-size: 12px;" onclick="deleteQuestion(${q.id})">
            🗑️
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
    loadCategoriesManagement();
  } catch (err) {
    console.error("Questions load error:", err);
  }
}

async function editSingleCategory(qid, currentCat) {
  const newCat = prompt("Yangi fan / kategoriya nomini kiriting:", currentCat);
  if (!newCat || newCat.trim() === '' || newCat.trim() === currentCat) return;

  try {
    const res = await fetch(`/api/admin/questions/${qid}/category`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ category: newCat.trim() })
    });
    if (res.ok) {
      loadQuestionsData();
      loadCategoriesManagement();
    }
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
}

async function renameAllCategories() {
  const input = document.getElementById('bulkCategoryInput');
  const newCat = input.value.trim();
  if (!newCat) {
    alert("Iltimos, yangi fan nomini kiriting!");
    return;
  }
  if (!confirm(`Barcha savollarning fanini "${newCat}" deb o'zgartirmoqchimisiz?`)) return;

  try {
    const res = await fetch('/api/admin/questions/rename-category', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ new_category: newCat })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alert(`✅ ${data.updated_count} ta savol fani "${newCat}" ga o'zgartirildi!`);
      input.value = '';
      loadQuestionsData();
      loadCategoriesManagement();
    }
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
}

async function loadCategoriesManagement() {
  try {
    const res = await fetch('/api/quiz/categories');
    if (!res.ok) return;
    const data = await res.json();
    const container = document.getElementById('categoriesManagementList');
    if (!container) return;

    container.innerHTML = '';
    const cats = data.categories || [];
    if (cats.length === 0) {
      container.innerHTML = '<span style="color: var(--text-muted); font-size: 13px;">Hozircha birorta ham fan qo\'shilmagan.</span>';
      return;
    }

    cats.forEach(c => {
      const badge = document.createElement('div');
      badge.style.display = 'inline-flex';
      badge.style.alignItems = 'center';
      badge.style.gap = '8px';
      badge.style.padding = '8px 12px';
      badge.style.background = 'rgba(255, 255, 255, 0.05)';
      badge.style.border = '1px solid var(--border-color)';
      badge.style.borderRadius = '8px';

      badge.innerHTML = `
        <span style="font-weight: 600; font-size: 14px;">${escapeHtml(c.category)}</span>
        <span style="font-size: 12px; color: var(--text-muted); background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px;">${c.count} ta savol</span>
        <button class="btn btn-outline" style="padding: 4px 8px; font-size: 12px; margin-left: 4px;" onclick="renameSpecificCategory('${escapeHtml(c.category)}')">
          ✏️ Nomini o'zgartirish
        </button>
      `;
      container.appendChild(badge);
    });
  } catch (err) {
    console.error("Categories management load error:", err);
  }
}

async function renameSpecificCategory(oldCat) {
  const newCat = prompt(`"${oldCat}" fani uchun yangi nom kiriting:`, oldCat);
  if (!newCat || newCat.trim() === '' || newCat.trim() === oldCat) return;

  try {
    const res = await fetch('/api/admin/questions/rename-category', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ old_category: oldCat, new_category: newCat.trim() })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      alert(`✅ "${oldCat}" fani muvaffaqiyatli "${newCat.trim()}" ga o'zgartirildi! (${data.updated_count} ta savol)`);
      loadCategoriesManagement();
      loadQuestionsData();
    } else {
      alert("❌ O'zgartirishda xatolik yuz berdi!");
    }
  } catch (err) {
    alert("Server bilan ulanishda xatolik: " + err.message);
  }
}

async function deleteQuestion(qid) {
  if (!confirm("Ushbu savolni o'chirmoqchimisiz?")) return;
  try {
    const res = await fetch(`/api/admin/questions/${qid}`, {
      method: 'DELETE',
      headers: { 'X-Admin-Key': adminKey }
    });
    if (res.ok) loadQuestionsData();
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
}

async function clearAllQuestions() {
  if (!confirm("⚠️ DIQQAT! Barcha test savollarini o'chirib tashlamoqchimisiz?")) return;
  try {
    const res = await fetch('/api/admin/questions/clear', {
      method: 'POST',
      headers: { 'X-Admin-Key': adminKey }
    });
    if (res.ok) {
      alert("Barcha savollar tozalandi!");
      loadQuestionsData();
    }
  } catch (err) {
    alert("Xatolik: " + err.message);
  }
}

// --- TAB 4: RESULTS ---
async function loadResultsData() {
  try {
    const res = await fetch('/api/admin/results', { headers: { 'X-Admin-Key': adminKey } });
    if (!res.ok) return;

    const data = await res.json();
    const tbody = document.getElementById('resultsTableBody');
    tbody.innerHTML = '';

    if (!data.results || data.results.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color: var(--text-muted);">Hozircha topshirilgan testlar yo'q.</td></tr>`;
      return;
    }

    data.results.forEach(r => {
      const mins = Math.floor(r.time_spent_seconds / 60);
      const secs = r.time_spent_seconds % 60;
      const passed = r.score_percentage >= 60;

      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${escapeHtml(r.full_name || 'Foydalanuvchi')}</strong></td>
        <td><code>${r.telegram_id}</code></td>
        <td>${r.correct_answers} / ${r.total_questions}</td>
        <td>
          <span style="font-weight: 700; color: ${passed ? 'var(--success)' : 'var(--danger)'};">
            ${r.score_percentage}%
          </span>
        </td>
        <td>${mins} daq ${secs} son</td>
        <td style="color: var(--text-muted); font-size: 12px;">${r.completed_at}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Results load error:", err);
  }
}

// HTML escape helper
function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
