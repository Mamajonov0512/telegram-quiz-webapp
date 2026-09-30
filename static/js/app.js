/**
 * Telegram Web App Quiz Application
 * Handles authentication, whitelist check, timer, quiz navigation, and submission
 */

// Initialize Telegram WebApp SDK
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

// App State
const state = {
  user: {
    id: null,
    name: 'Foydalanuvchi',
    username: ''
  },
  isAllowed: false,
  isAdmin: false,
  settings: {
    questions_per_test: 50,
    duration_minutes: 50,
    pass_percentage: 60
  },
  selectedCategory: 'Barchasi',
  selectedCount: 50,
  sessionId: null,
  categories: [],
  questions: [],
  currentIndex: 0,
  answers: {},     // { questionId: 'A' | 'B' | 'C' | 'D' }
  flagged: new Set(), // Set of questionIds
  timerInterval: null,
  timeRemainingSeconds: 0,
  timeSpentSeconds: 0,
  isFinished: false,
  reviewData: null
};

// --- HAPTIC FEEDBACK HELPER ---
function triggerHaptic(type = 'light') {
  if (!tg?.HapticFeedback) return;
  try {
    if (type === 'success') tg.HapticFeedback.notificationOccurred('success');
    else if (type === 'error') tg.HapticFeedback.notificationOccurred('error');
    else if (type === 'warning') tg.HapticFeedback.notificationOccurred('warning');
    else tg.HapticFeedback.impactOccurred(type);
  } catch (e) {
    // Ignore if not supported
  }
}

// --- TOAST NOTIFICATIONS ---
function showToast(message, duration = 3000) {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.innerText = message;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, duration);
}

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
  initSecurityShieldAndProtections();
  extractUserData();
  checkUserAuth();
});

function extractUserData() {
  // 1. Try Telegram WebApp initDataUnsafe
  if (tg?.initDataUnsafe?.user) {
    const u = tg.initDataUnsafe.user;
    state.user.id = u.id;
    state.user.name = [u.first_name, u.last_name].filter(Boolean).join(' ') || 'Foydalanuvchi';
    state.user.username = u.username || '';
    return;
  }

  // 2. Try URL query parameters (e.g. ?user_id=12345678)
  const params = new URLSearchParams(window.location.search);
  const uidParam = params.get('user_id') || params.get('id');
  if (uidParam && !isNaN(uidParam)) {
    state.user.id = parseInt(uidParam, 10);
    state.user.name = params.get('name') || 'Foydalanuvchi';
    state.user.username = params.get('username') || '';
    return;
  }

  // 3. Fallback for local browser testing: stored in localStorage or default admin ID
  const savedId = localStorage.getItem('demo_telegram_id');
  if (savedId) {
    state.user.id = parseInt(savedId, 10);
    state.user.name = localStorage.getItem('demo_user_name') || 'Test Foydalanuvchi';
  } else {
    // Default test ID
    const demoId = 12345678;
    state.user.id = demoId;
    state.user.name = 'Demo Foydalanuvchi';
    localStorage.setItem('demo_telegram_id', demoId);
    localStorage.setItem('demo_user_name', state.user.name);
  }
}

// --- AUTH & WHITELIST CHECK ---
async function checkUserAuth() {
  switchView('loadingView');
  document.getElementById('loadingStatusText').innerText = "Ruxsat holati tekshirilmoqda...";

  try {
    const res = await fetch('/api/auth/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        telegram_id: state.user.id,
        first_name: state.user.name,
        username: state.user.username,
        init_data: tg?.initData || ''
      })
    });

    const data = await res.json();
    state.isAllowed = !!data.authorized;
    state.isAdmin = !!data.is_admin;

    if (data.settings) {
      state.settings = { ...state.settings, ...data.settings };
    }

    // Update Header
    updateHeaderUI();

    if (state.isAllowed) {
      setupWatermark();
      await loadCategories();
      renderWelcomeScreen();
      switchView('welcomeView');
    } else {
      renderDeniedScreen();
      switchView('deniedView');
    }
  } catch (err) {
    console.error("Auth check error:", err);
    showToast("Server bilan ulanishda xatolik yuz berdi!");
    // Show denied screen as safe fallback
    renderDeniedScreen();
    switchView('deniedView');
  }
}

function recheckAccess() {
  triggerHaptic('light');
  checkUserAuth();
}

function updateHeaderUI() {
  const header = document.getElementById('appHeader');
  const avatar = document.getElementById('headerAvatar');
  const name = document.getElementById('headerName');
  const idEl = document.getElementById('headerId');

  header.style.display = 'flex';
  name.innerText = state.user.name;
  idEl.innerText = `ID: ${state.user.id}`;
  avatar.innerText = (state.user.name[0] || 'U').toUpperCase();
}

function renderDeniedScreen() {
  document.getElementById('deniedUserId').innerText = state.user.id;
}

function copyTelegramId() {
  triggerHaptic('medium');
  navigator.clipboard.writeText(state.user.id.toString()).then(() => {
    showToast("ID nusxalandi: " + state.user.id);
  }).catch(() => {
    showToast("ID: " + state.user.id);
  });
}

// --- CATEGORY & QUESTION COUNT MANAGEMENT ---
async function loadCategories() {
  try {
    const res = await fetch(`/api/quiz/categories?telegram_id=${state.user.id}`);
    if (!res.ok) return;
    const data = await res.json();
    state.categories = data.categories || [];
    const totalQ = data.total_questions || 0;

    const select = document.getElementById('quizCategorySelect');
    if (!select) return;

    select.innerHTML = '';
    const allOpt = document.createElement('option');
    allOpt.value = 'Barchasi';
    allOpt.innerText = `Barchasi (Aralash) - ${totalQ} ta savol`;
    select.appendChild(allOpt);

    state.categories.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.name;
      opt.innerText = `${c.name} - ${c.count} ta savol`;
      select.appendChild(opt);
    });

    state.selectedCategory = 'Barchasi';
    adjustCountPillsForCategory();
  } catch (e) {
    console.error("Failed to load categories:", e);
  }
}

function onCategoryChange() {
  const select = document.getElementById('quizCategorySelect');
  if (!select) return;
  state.selectedCategory = select.value;
  adjustCountPillsForCategory();
}

function getMaxAvailableForCategory() {
  let maxAvail = 0;
  if (state.selectedCategory === 'Barchasi') {
    maxAvail = state.categories.reduce((acc, c) => acc + c.count, 0);
  } else {
    const cat = state.categories.find(c => c.name === state.selectedCategory);
    maxAvail = cat ? cat.count : 0;
  }
  return Math.min(maxAvail || 500, 500);
}

function adjustCountPillsForCategory() {
  const maxAvail = getMaxAvailableForCategory();

  const hintEl = document.getElementById('maxAvailableCountHint');
  if (hintEl) {
    hintEl.innerText = `Mavjud: ${maxAvail} ta (max 500)`;
  }

  const customInput = document.getElementById('customCountInput');
  if (customInput) {
    customInput.max = maxAvail;
  }

  const pills = document.querySelectorAll('.count-pill');
  let activePillFound = false;
  let highestPill = 10;

  pills.forEach(pill => {
    const count = parseInt(pill.getAttribute('data-count'), 10);
    if (count <= maxAvail || maxAvail === 0) {
      pill.style.display = 'inline-block';
      highestPill = Math.max(highestPill, count);
      if (count === state.selectedCount) {
        pill.classList.add('active');
        activePillFound = true;
      } else {
        pill.classList.remove('active');
      }
    } else {
      pill.style.display = 'none';
      pill.classList.remove('active');
    }
  });

  if (!activePillFound) {
    const target = Math.min(state.selectedCount, maxAvail);
    selectQuestionCount(target > 0 ? target : highestPill, true);
  } else {
    updateWelcomeStats();
  }
}

function selectQuestionCount(num, syncCustomInput = true) {
  triggerHaptic('light');
  let count = parseInt(num, 10);
  if (isNaN(count) || count < 1) count = 10;
  
  // Cap at 500 and available questions
  const maxAvail = getMaxAvailableForCategory();
  if (maxAvail > 0) {
    count = Math.min(count, maxAvail);
  }
  count = Math.min(Math.max(1, count), 500);

  state.selectedCount = count;

  const pills = document.querySelectorAll('.count-pill');
  let matchedPill = false;
  pills.forEach(p => {
    const c = parseInt(p.getAttribute('data-count'), 10);
    if (c === count) {
      p.classList.add('active');
      matchedPill = true;
    } else {
      p.classList.remove('active');
    }
  });

  const customInput = document.getElementById('customCountInput');
  if (customInput && syncCustomInput) {
    customInput.value = matchedPill ? '' : count;
  }

  updateWelcomeStats();
}

function onCustomCountInput(val) {
  let count = parseInt(val, 10);
  if (isNaN(count) || count < 1) return;
  if (count > 500) {
    count = 500;
    const input = document.getElementById('customCountInput');
    if (input) input.value = 500;
  }
  const maxAvail = getMaxAvailableForCategory();
  if (maxAvail > 0 && count > maxAvail) {
    count = maxAvail;
    const input = document.getElementById('customCountInput');
    if (input) input.value = maxAvail;
    showToast(`Ushbu fanda jami ${maxAvail} ta savol bor`);
  }
  selectQuestionCount(count, false);
}

function updateWelcomeStats() {
  const countEl = document.getElementById('welcomeQuestionCount');
  const durationEl = document.getElementById('welcomeDuration');
  const passEl = document.getElementById('welcomePassScore');

  if (countEl) countEl.innerText = `${state.selectedCount} ta`;
  if (durationEl) durationEl.innerText = `${state.selectedCount} daqiqa`;
  if (passEl) passEl.innerText = `${state.settings.pass_percentage}%`;
}

function renderWelcomeScreen() {
  document.getElementById('welcomeTitle').innerText = `Assalomu alaykum, ${state.user.name}!`;
  updateWelcomeStats();
}

// --- SWITCH SCREENS HELPER ---
function switchView(viewId) {
  const views = ['loadingView', 'deniedView', 'welcomeView', 'quizView', 'resultsView'];
  views.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      if (id === viewId) {
        el.style.display = (id === 'quizView') ? 'flex' : 'block';
      } else {
        el.style.display = 'none';
      }
    }
  });

  const timerBadge = document.getElementById('timerBadge');
  if (timerBadge) {
    timerBadge.style.display = (viewId === 'quizView') ? 'flex' : 'none';
  }
}

// --- START QUIZ ---
async function startQuiz() {
  triggerHaptic('medium');
  switchView('loadingView');
  document.getElementById('loadingStatusText').innerText = "Savollar tayyorlanmoqda...";

  try {
    const res = await fetch('/api/quiz/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        telegram_id: state.user.id,
        category: state.selectedCategory,
        count: state.selectedCount
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Savollarni yuklab bo'lmadi");
    }

    const data = await res.json();
    if (!data.questions || data.questions.length === 0) {
      alert("Tanlangan fan yoki guruh bo'yicha savollar mavjud emas.");
      switchView('welcomeView');
      return;
    }

    state.sessionId = data.session_id || null;
    state.questions = data.questions;
    state.currentIndex = 0;
    state.answers = {};
    state.flagged.clear();
    state.isFinished = false;
    state.timeSpentSeconds = 0;
    
    // Set timer from server response or selected count
    const durationMinutes = data.duration_minutes || state.selectedCount || 50;
    state.timeRemainingSeconds = durationMinutes * 60;

    startTimer();
    renderQuestion(state.currentIndex);
    buildPaletteGrid();
    switchView('quizView');

  } catch (err) {
    console.error("Quiz start error:", err);
    showToast(err.message || "Xatolik yuz berdi!");
    switchView('welcomeView');
  }
}

// --- TIMER MANAGEMENT ---
function startTimer() {
  if (state.timerInterval) clearInterval(state.timerInterval);

  updateTimerDisplay();

  state.timerInterval = setInterval(() => {
    state.timeRemainingSeconds--;
    state.timeSpentSeconds++;

    updateTimerDisplay();

    if (state.timeRemainingSeconds <= 0) {
      clearInterval(state.timerInterval);
      triggerHaptic('error');
      showToast("⚠️ Vaqt tugadi! Test avtomatik yakunlanmoqda...", 3000);
      setTimeout(() => {
        submitQuizFinal();
      }, 1000);
    }
  }, 1000);
}

function updateTimerDisplay() {
  const badge = document.getElementById('timerBadge');
  const timerText = document.getElementById('timerText');
  if (!timerText) return;

  const mins = Math.floor(Math.max(0, state.timeRemainingSeconds) / 60);
  const secs = Math.max(0, state.timeRemainingSeconds) % 60;
  const formatted = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  timerText.innerText = formatted;

  // Visual cues
  if (state.timeRemainingSeconds <= 120) {
    badge.className = 'timer-badge danger';
  } else if (state.timeRemainingSeconds <= 300) {
    badge.className = 'timer-badge warning';
  } else {
    badge.className = 'timer-badge';
  }
}

// --- RENDER CURRENT QUESTION ---
function renderQuestion(index) {
  const q = state.questions[index];
  if (!q) return;

  // Header info
  document.getElementById('qCategory').innerText = q.category || 'Umumiy';
  document.getElementById('progressCurrent').innerText = (index + 1).toString();
  document.getElementById('progressTotal').innerText = state.questions.length.toString();
  document.getElementById('paletteBtnText').innerText = `${index + 1} / ${state.questions.length}`;

  // Progress Bar
  const answeredCount = Object.keys(state.answers).length;
  document.getElementById('progressAnsweredCount').innerText = answeredCount.toString();
  const percent = Math.round((answeredCount / state.questions.length) * 100);
  document.getElementById('progressBar').style.width = `${percent}%`;

  // Flag button status
  const isFlagged = state.flagged.has(q.id);
  const flagBtn = document.getElementById('flagBtn');
  flagBtn.className = isFlagged ? 'flag-btn flagged' : 'flag-btn';
  document.getElementById('flagIcon').innerText = isFlagged ? '★' : '☆';
  document.getElementById('flagText').innerText = isFlagged ? 'Belgilangan' : 'Belgilash';

  // Question Text
  document.getElementById('questionText').innerText = `${index + 1}. ${q.question}`;

  // Options
  const container = document.getElementById('optionsContainer');
  container.innerHTML = '';

  const selectedOption = state.answers[q.id];

  ['A', 'B', 'C', 'D'].forEach(letter => {
    const optText = q.options[letter];
    if (!optText) return;

    const optDiv = document.createElement('div');
    optDiv.className = `option-item ${selectedOption === letter ? 'selected' : ''}`;
    optDiv.onclick = () => selectOption(q.id, letter);

    optDiv.innerHTML = `
      <div class="option-letter">${letter}</div>
      <div class="option-text">${escapeHtml(optText)}</div>
    `;
    container.appendChild(optDiv);
  });

  // Prev / Next button state
  document.getElementById('prevBtn').disabled = (index === 0);
  document.getElementById('prevBtn').style.opacity = (index === 0) ? '0.5' : '1';

  const nextBtn = document.getElementById('nextBtn');
  if (index === state.questions.length - 1) {
    nextBtn.innerText = 'Tugash ▶️';
  } else {
    nextBtn.innerText = 'Keyingi ▶️';
  }

  // Update palette grid active highlight
  updatePaletteItemState(index);
}

function selectOption(qid, letter) {
  triggerHaptic('light');
  state.answers[qid] = letter;
  renderQuestion(state.currentIndex);
  buildPaletteGrid();
}

function toggleFlagCurrentQuestion() {
  triggerHaptic('medium');
  const q = state.questions[state.currentIndex];
  if (!q) return;

  if (state.flagged.has(q.id)) {
    state.flagged.delete(q.id);
    showToast("Belgilash olib tashlandi");
  } else {
    state.flagged.add(q.id);
    showToast("Savol qayta ko'rish uchun belgilandi ★");
  }
  renderQuestion(state.currentIndex);
  buildPaletteGrid();
}

function goToPrevQuestion() {
  if (state.currentIndex > 0) {
    triggerHaptic('light');
    state.currentIndex--;
    renderQuestion(state.currentIndex);
  }
}

function goToNextQuestion() {
  if (state.currentIndex < state.questions.length - 1) {
    triggerHaptic('light');
    state.currentIndex++;
    renderQuestion(state.currentIndex);
  } else {
    promptFinishQuiz();
  }
}

// --- PALETTE DRAWER (GRID OF 1..50) ---
function buildPaletteGrid() {
  const grid = document.getElementById('paletteGrid');
  if (!grid) return;
  grid.innerHTML = '';

  state.questions.forEach((q, idx) => {
    const item = document.createElement('div');
    const isCurrent = (idx === state.currentIndex);
    const isAnswered = (state.answers[q.id] !== undefined);
    const isFlagged = state.flagged.has(q.id);

    let classes = ['palette-item'];
    if (isCurrent) classes.push('current');
    if (isAnswered) classes.push('answered');
    if (isFlagged) classes.push('flagged');

    item.className = classes.join(' ');
    item.innerText = (idx + 1).toString();
    item.onclick = () => {
      triggerHaptic('light');
      state.currentIndex = idx;
      renderQuestion(idx);
      closePaletteModal();
    };

    grid.appendChild(item);
  });
}

function updatePaletteItemState(currentIndex) {
  const items = document.querySelectorAll('.palette-item');
  items.forEach((item, idx) => {
    if (idx === currentIndex) {
      item.classList.add('current');
    } else {
      item.classList.remove('current');
    }
  });
}

function openPaletteModal() {
  triggerHaptic('medium');
  buildPaletteGrid();
  document.getElementById('paletteModal').classList.add('active');
}

function closePaletteModal(e) {
  if (e && e.target !== e.currentTarget && !e.target.classList.contains('btn-icon-only')) return;
  document.getElementById('paletteModal').classList.remove('active');
}

// --- FINISH QUIZ FLOW ---
function promptFinishQuiz() {
  triggerHaptic('medium');
  const answered = Object.keys(state.answers).length;
  const total = state.questions.length;
  const remaining = total - answered;

  let msg = `Siz <b>${total} ta</b> savoldan <b>${answered} tasiga</b> javob berdingiz.`;
  if (remaining > 0) {
    msg += `<br><span style="color: var(--accent-warning);">⚠️ <b>${remaining} ta</b> savol javobsiz qoldi!</span>`;
  }

  document.getElementById('confirmSummaryText').innerHTML = msg;
  document.getElementById('confirmModal').classList.add('active');
}

function closeConfirmModal() {
  document.getElementById('confirmModal').classList.remove('active');
}

async function submitQuizFinal() {
  closeConfirmModal();
  if (state.timerInterval) clearInterval(state.timerInterval);

  switchView('loadingView');
  document.getElementById('loadingStatusText').innerText = "Natijalaringiz hisoblanmoqda...";

  try {
    const res = await fetch('/api/quiz/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        telegram_id: state.user.id,
        full_name: state.user.name,
        username: state.user.username,
        time_spent_seconds: state.timeSpentSeconds,
        answers: state.answers,
        session_id: state.sessionId
      })
    });

    if (!res.ok) {
      throw new Error("Natijalarni saqlashda xatolik yuz berdi");
    }

    const result = await res.json();
    state.reviewData = result;
    renderResultsScreen(result);
    switchView('resultsView');

    if (result.passed) {
      triggerHaptic('success');
    } else {
      triggerHaptic('warning');
    }

  } catch (err) {
    console.error("Submit error:", err);
    showToast("Xatolik: " + err.message);
    switchView('quizView');
  }
}

// --- RENDER RESULTS & REVIEW ---
function renderResultsScreen(data) {
  const circle = document.getElementById('resultScoreCircle');
  const percentageEl = document.getElementById('resultPercentage');
  const ratioEl = document.getElementById('resultRatio');
  const titleEl = document.getElementById('resultStatusTitle');
  const subtitleEl = document.getElementById('resultStatusSubtitle');

  percentageEl.innerText = `${data.percentage}%`;
  ratioEl.innerText = `${data.score} / ${data.total}`;

  if (data.passed) {
    circle.className = 'score-circle passed';
    titleEl.innerText = "Tabriklaymiz, siz testdan o'tdingiz! 🎉";
    titleEl.style.color = "var(--accent-success)";
    subtitleEl.innerText = `O'tish bali: ${data.pass_percentage}%. Siz ajoyib natija ko'rsatdingiz.`;
  } else {
    circle.className = 'score-circle failed';
    titleEl.innerText = "Afsuski, o'tish baliga yetmadi 😔";
    titleEl.style.color = "var(--accent-danger)";
    subtitleEl.innerText = `O'tish bali: ${data.pass_percentage}%. Yana bir bor urinib ko'ring!`;
  }

  document.getElementById('statCorrect').innerText = data.score;
  document.getElementById('statWrong').innerText = data.wrong;
  
  const mins = Math.floor(data.time_spent_seconds / 60);
  const secs = data.time_spent_seconds % 60;
  document.getElementById('statTime').innerText = `${mins} daq ${secs} son`;
  document.getElementById('statPassed').innerText = data.passed ? "Muvaffaqiyatli ✅" : "O'tmadi ❌";

  // Counts for filter tabs
  document.getElementById('countAll').innerText = data.total;
  document.getElementById('countWrong').innerText = data.wrong;
  document.getElementById('countCorrect').innerText = data.score;

  // Render questions review list
  renderReviewList('all');
}

function filterReview(type) {
  triggerHaptic('light');
  document.querySelectorAll('.filter-tab').forEach(tab => {
    if (tab.dataset.filter === type) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  renderReviewList(type);
}

function renderReviewList(filterType) {
  const container = document.getElementById('reviewContainer');
  if (!container || !state.reviewData?.review) return;

  container.innerHTML = '';

  const items = state.reviewData.review.filter(item => {
    if (filterType === 'correct') return item.is_correct;
    if (filterType === 'wrong') return !item.is_correct;
    return true;
  });

  if (items.length === 0) {
    container.innerHTML = `<p style="text-align: center; color: var(--hint-color); padding: 20px;">Ushbu bo'limda savollar yo'q.</p>`;
    return;
  }

  items.forEach((item, idx) => {
    const card = document.createElement('div');
    card.className = `glass-card review-item ${item.is_correct ? 'correct' : 'wrong'}`;

    const userAnsText = item.user_answer ? `${item.user_answer}) ${item.options[item.user_answer] || ''}` : "Javob berilmagan";
    const correctAnsText = `${item.correct_answer}) ${item.options[item.correct_answer] || ''}`;

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
        <span style="font-weight: 700; font-size: 14px;">Savol #${idx + 1}</span>
        <span style="font-size: 12px; font-weight: 600; color: ${item.is_correct ? 'var(--accent-success)' : 'var(--accent-danger)'};">
          ${item.is_correct ? 'To\'g\'ri ✅' : 'Noto\'g\'ri ❌'}
        </span>
      </div>

      <div style="font-weight: 600; margin-bottom: 12px; font-size: 15px;">
        ${escapeHtml(item.question)}
      </div>

      <div style="font-size: 13px; margin-bottom: 6px;">
        <span style="color: var(--hint-color);">Sizning javobingiz:</span>
        <strong style="color: ${item.is_correct ? 'var(--accent-success)' : 'var(--accent-danger)'};">
          ${escapeHtml(userAnsText)}
        </strong>
      </div>

      ${!item.is_correct ? `
        <div style="font-size: 13px; margin-bottom: 6px;">
          <span style="color: var(--hint-color);">To'g'ri javob:</span>
          <strong style="color: var(--accent-success);">${escapeHtml(correctAnsText)}</strong>
        </div>
      ` : ''}

      ${item.explanation ? `
        <div class="review-explanation">
          💡 <strong>Izoh:</strong> ${escapeHtml(item.explanation)}
        </div>
      ` : ''}
    `;

    container.appendChild(card);
  });
}

function restartTest() {
  triggerHaptic('medium');
  checkUserAuth();
}

function closeWebApp() {
  if (tg) {
    tg.close();
  } else {
    window.location.reload();
  }
}

// --- PAST RESULTS & PERSONAL ANALYTICS MODAL ---
function switchUserModalTab(tab) {
  triggerHaptic('light');
  const tabAn = document.getElementById('tabUserAnalytics');
  const tabHist = document.getElementById('tabUserHistory');
  const viewAn = document.getElementById('userAnalyticsView');
  const viewHist = document.getElementById('historyList');

  if (tab === 'analytics') {
    tabAn.classList.add('active');
    tabHist.classList.remove('active');
    viewAn.style.display = 'block';
    viewHist.style.display = 'none';
  } else {
    tabHist.classList.add('active');
    tabAn.classList.remove('active');
    viewHist.style.display = 'block';
    viewAn.style.display = 'none';
  }
}

async function openHistoryModal() {
  triggerHaptic('light');
  const modal = document.getElementById('historyModal');
  modal.classList.add('active');
  switchUserModalTab('analytics');

  const catContainer = document.getElementById('userCategoryBreakdown');
  catContainer.innerHTML = `<p style="color: var(--hint-color); font-size: 13px;">Tahlil yuklanmoqda...</p>`;

  const list = document.getElementById('historyList');
  list.innerHTML = `<p style="color: var(--hint-color); text-align: center; padding: 20px;">Yuklanmoqda...</p>`;

  try {
    // 1. Fetch user analytics
    const anRes = await fetch(`/api/user/analytics?telegram_id=${state.user.id}`);
    const anData = await anRes.json();
    const a = anData.analytics;

    document.getElementById('userBestScore').innerText = `${a.best_score || 0}%`;
    document.getElementById('userAvgScore').innerText = `${a.avg_score || 0}%`;

    catContainer.innerHTML = '';
    if (!a.category_performance || a.category_performance.length === 0) {
      catContainer.innerHTML = `<p style="color: var(--hint-color); font-size: 13px;">Test topshirganingizdan so'ng bu yerda fanlar bo'yicha tahlil paydo bo'ladi.</p>`;
    } else {
      a.category_performance.forEach(c => {
        const row = document.createElement('div');
        const color = c.accuracy >= 80 ? 'var(--accent-success)' : (c.accuracy >= 60 ? 'var(--accent-primary)' : 'var(--accent-danger)');
        row.innerHTML = `
          <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 4px;">
            <span><strong>${escapeHtml(c.category)}</strong> (${c.correct}/${c.total} ta to'g'ri)</span>
            <span style="font-weight: 700; color: ${color};">${c.accuracy}% • ${c.status}</span>
          </div>
          <div style="height: 6px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden;">
            <div style="height: 100%; width: ${c.accuracy}%; background: ${color}; border-radius: 4px;"></div>
          </div>
        `;
        catContainer.appendChild(row);
      });
    }

    // 2. Fetch history
    const histRes = await fetch(`/api/user/history?telegram_id=${state.user.id}`);
    const histData = await histRes.json();

    if (!histData.results || histData.results.length === 0) {
      list.innerHTML = `<p style="color: var(--hint-color); text-align: center; padding: 20px;">Siz hali test topshirmagansiz.</p>`;
      return;
    }

    list.innerHTML = '';
    histData.results.forEach((r, idx) => {
      const mins = Math.floor(r.time_spent_seconds / 60);
      const secs = r.time_spent_seconds % 60;
      const passed = r.score_percentage >= state.settings.pass_percentage;

      const item = document.createElement('div');
      item.style.padding = '12px';
      item.style.background = 'rgba(255, 255, 255, 0.04)';
      item.style.border = '1px solid var(--card-border)';
      item.style.borderRadius = 'var(--radius-md)';
      item.style.marginBottom = '10px';

      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
          <span style="font-weight: 700;">#${idx + 1} • ${r.completed_at}</span>
          <span style="font-weight: 700; color: ${passed ? 'var(--accent-success)' : 'var(--accent-danger)'};">
            ${r.score_percentage}%
          </span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 13px; color: var(--hint-color);">
          <span>Natija: <strong>${r.correct_answers} / ${r.total_questions}</strong></span>
          <span>Vaqt: <strong>${mins} daq ${secs} son</strong></span>
        </div>
      `;
      list.appendChild(item);
    });

  } catch (err) {
    console.error("User modal load error:", err);
    list.innerHTML = `<p style="color: var(--accent-danger); text-align: center;">Ma'lumotlarni yuklashda xatolik yuz berdi.</p>`;
  }
}

function closeHistoryModal(e) {
  if (e && e.target !== e.currentTarget && !e.target.classList.contains('btn-icon-only')) return;
  document.getElementById('historyModal').classList.remove('active');
}

// Utility: escape HTML
function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// --- ANTI-COPY & ANTI-SCREENSHOT SECURITY ---
function setupWatermark() {
  const overlay = document.getElementById('watermarkOverlay');
  if (!overlay) return;
  overlay.innerHTML = '';
  const dateStr = new Date().toLocaleDateString('uz-UZ');
  const text = `${state.user.name} • ID: ${state.user.id} • ${dateStr}`;
  for (let i = 0; i < 32; i++) {
    const cell = document.createElement('div');
    cell.className = 'watermark-cell';
    cell.innerText = text;
    overlay.appendChild(cell);
  }
}

function triggerSecurityShield(msg) {
  const shield = document.getElementById('securityShield');
  if (shield) {
    if (msg) {
      const p = shield.querySelector('p');
      if (p) p.innerText = msg;
    }
    shield.classList.add('active');
    triggerHaptic('error');
  }
}

function dismissSecurityShield() {
  const shield = document.getElementById('securityShield');
  if (shield) {
    shield.classList.remove('active');
  }
}

function isQuizInProgress() {
  const quizView = document.getElementById('quizView');
  return quizView && quizView.style.display === 'flex' && !state.isFinished;
}

function initSecurityShieldAndProtections() {
  // 1. Disable Right Click (Context Menu)
  document.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    showToast("⚠️ O'ng tugma bosish taqiqlangan!");
    return false;
  }, { capture: true });

  // 2. Disable Copy, Cut, Paste, Drag, Select
  ['copy', 'cut', 'paste', 'selectstart', 'dragstart'].forEach(evt => {
    document.addEventListener(evt, (e) => {
      // Allow copy only in denied screen copy button
      if (e.target && e.target.closest('#deniedView')) return;
      e.preventDefault();
      if (evt === 'copy' || evt === 'cut') {
        showToast("⚠️ Testdan nusxa olish taqiqlangan!");
        triggerHaptic('warning');
      }
      return false;
    }, { capture: true });
  });

  // 3. Prevent Devtools, Print and Save hotkeys
  document.addEventListener('keydown', (e) => {
    const isDevTools = e.key === 'F12' || (e.ctrlKey && e.shiftKey && ['I', 'J', 'C', 'i', 'j', 'c'].includes(e.key));
    const isSaveOrPrint = e.ctrlKey && ['s', 'S', 'p', 'P', 'u', 'U'].includes(e.key);
    const isCopyOrCut = e.ctrlKey && ['c', 'C', 'x', 'X', 'a', 'A'].includes(e.key);

    if (isDevTools || isSaveOrPrint) {
      e.preventDefault();
      e.stopPropagation();
      showToast("⚠️ Ushbu amal taqiqlangan!");
      return false;
    }

    // Block Ctrl+C / Ctrl+A during quiz
    if (isCopyOrCut && isQuizInProgress()) {
      e.preventDefault();
      e.stopPropagation();
      showToast("⚠️ Test davomida nusxa olish taqiqlangan!");
      return false;
    }

    // PrintScreen detection
    if (e.key === 'PrintScreen' || e.keyCode === 44) {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText('');
      }
      triggerSecurityShield("Ekranni rasmga olish (PrintScreen) taqiqlangan!");
    }
  }, { capture: true });

  // 4. Blur and visibilitychange detection (Anti-tab-switch / anti-screenshot tool switch)
  window.addEventListener('blur', () => {
    if (isQuizInProgress()) {
      triggerSecurityShield("Diqqat! Test davomida boshqa oynaga o'tish yoki rasmga olish taqiqlangan!");
    }
  });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden && isQuizInProgress()) {
      triggerSecurityShield("Diqqat! Test oynasidan chiqish taqiqlangan!");
    }
  });

  // 5. Telegram WebApp safety hooks
  if (tg) {
    try {
      if (typeof tg.enableClosingConfirmation === 'function') {
        tg.enableClosingConfirmation();
      }
      if (typeof tg.disableVerticalSwipes === 'function') {
        tg.disableVerticalSwipes();
      }
    } catch (e) {
      console.warn("Telegram WebApp security flags not supported in this client");
    }
  }
}

// Global window assignments for onclick handlers
window.dismissSecurityShield = dismissSecurityShield;
window.onCategoryChange = onCategoryChange;
window.selectQuestionCount = selectQuestionCount;
window.startQuiz = startQuiz;
window.recheckAccess = recheckAccess;
window.copyTelegramId = copyTelegramId;
window.toggleFlagCurrentQuestion = toggleFlagCurrentQuestion;
window.goToPrevQuestion = goToPrevQuestion;
window.goToNextQuestion = goToNextQuestion;
window.openPaletteModal = openPaletteModal;
window.closePaletteModal = closePaletteModal;
window.promptFinishQuiz = promptFinishQuiz;
window.closeConfirmModal = closeConfirmModal;
window.submitQuizFinal = submitQuizFinal;
window.startReviewMode = startReviewMode;
window.restartApp = restartApp;
window.openHistoryModal = openHistoryModal;
window.closeHistoryModal = closeHistoryModal;
window.switchUserModalTab = switchUserModalTab;
window.onCustomCountInput = onCustomCountInput;

