// ===============================
// TAB SYSTEM
// ===============================
const tabs = document.querySelectorAll(".tab");
const tabButtons = document.querySelectorAll(".tablink");
const logoutBtn = document.getElementById("logoutBtn");

function showTab(id) {
    tabs.forEach((t) => t.classList.toggle("active", t.id === id));

    if (id === "achievements") renderAchievements();
    if (id === "forum") renderForum();
    if (id === "support") renderSupport();
}

tabButtons.forEach((btn) =>
    btn.addEventListener("click", () => showTab(btn.dataset.tab))
);

// ===============================
// FORMS
// ===============================
const registerForm = document.getElementById("registerForm");
const loginForm = document.getElementById("loginForm");

// Password Policy Regex
function pwdValid(p) {
    return /^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{10,}$/.test(p);
}

// ===============================
// REGISTER
// ===============================
registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(registerForm).entries());

    if (!pwdValid(data.password)) {
        alert(
            "Password must be ≥10 chars and include a letter, a number, and a special character."
        );
        return;
    }

    const r = await fetch("/api/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });

    const j = await r.json();
    if (j.ok) {
        alert("Account created! Please log in.");
    } else {
        alert(j.msg || "Error");
    }
});

// ===============================
// LOGIN
// ===============================
loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(loginForm).entries());

    const r = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });

    const j = await r.json();

    if (j.ok) {
        if (j.redirect) {
            window.location.href = j.redirect;
        } else {
            await afterLogin();
        }
    } else {
        alert(j.msg || "Error");
    }
});

// LOGOUT
logoutBtn.addEventListener("click", async () => {
    await fetch("/api/logout", { method: "POST" });
    location.reload();
});

// ===============================
// SESSION AFTER LOGIN
// ===============================
let sessionUser = null;
let CONTENT = null;
let currentLesson = null;
let autoMarked = false;
let ytPlayer = null;

// Dashboard refs
const userName = document.getElementById("userName");
const progressText = document.getElementById("progressText");
const pointsDiv = document.getElementById("points");
const levelDiv = document.getElementById("level");
const badgesCountDiv = document.getElementById("badgesCount");

async function afterLogin() {
    const s = await (await fetch("/api/session")).json();
    if (!s.ok) {
        showTab("auth");
        return;
    }

    sessionUser = s.user;

    // Enable tabs
    document
        .querySelectorAll(
            '[data-tab="dashboard"],[data-tab="content"],[data-tab="quiz"],[data-tab="achievements"],[data-tab="forum"],[data-tab="faq"],[data-tab="support"]'
        )
        .forEach((b) => b.removeAttribute("disabled"));

    document.querySelector('[data-tab="auth"]').setAttribute("disabled", "true");

    logoutBtn.style.display = "inline-block";

    showTab("dashboard");
    await refreshDashboard();
    await loadContent();
    await renderForum();
    await renderAchievements();
    await renderSupport();
}

// ===============================
// DASHBOARD
// ===============================
async function refreshDashboard() {
    const s = await (await fetch("/api/session")).json();
    sessionUser = s.ok ? s.user : null;

    userName.textContent = sessionUser?.name || sessionUser?.email || "-";

    pointsDiv.textContent = sessionUser?.points ?? 0;
    levelDiv.textContent = sessionUser?.level ?? 1;

    const list = await (await fetch("/api/user/achievements")).json();
    badgesCountDiv.textContent = list.badges?.length || 0;
}

// ===============================
// LOAD CONTENT (LESSONS)
// ===============================
const modulesDiv = document.getElementById("modules");
const lessonCard = document.getElementById("lessonCard");
const lessonTitle = document.getElementById("lessonTitle");
const lessonBody = document.getElementById("lessonBody");
const videoWrap = document.getElementById("videoWrap");
const markCompleteBtn = document.getElementById("markCompleteBtn");
const openQuizBtn = document.getElementById("openQuizBtn");

async function loadContent() {
    const res = await fetch("/api/content");
    const data = await res.json();
    CONTENT = data;

    modulesDiv.innerHTML = "";

    data.modules.forEach((m) => {
        const mEl = document.createElement("div");
        mEl.className = "module card";

        const header = document.createElement("h3");
        header.textContent = m.title;
        mEl.appendChild(header);

        m.lessons.forEach((lsn) => {
            const row = document.createElement("div");
            row.className = "lesson";

            const left = document.createElement("div");
            left.innerHTML = `<strong>${lsn.title}</strong>`;

            const btn = document.createElement("button");
            btn.textContent = "Open";
            btn.addEventListener("click", () => openLesson(lsn));

            row.appendChild(left);
            row.appendChild(btn);
            mEl.appendChild(row);
        });

        modulesDiv.appendChild(mEl);
    });
}

// Handle YouTube
function resetVideoWrap() {
    videoWrap.innerHTML = "";
    videoWrap.style.display = "none";
    autoMarked = false;

    if (ytPlayer && ytPlayer.destroy) {
        try {
            ytPlayer.destroy();
        } catch (e) { }
    }
    ytPlayer = null;
}

function isYouTube(url) {
    return /youtube\.com|youtu\.be/.test(url || "");
}

function youtubeIdFromUrl(url) {
    const m = url.match(/(?:v=|\/embed\/|youtu\.be\/)([a-zA-Z0-9_-]{6,})/);
    return m ? m[1] : null;
}

// OPEN LESSON
function openLesson(lsn) {
    currentLesson = lsn;

    lessonCard.style.display = "block";
    lessonTitle.textContent = lsn.title;
    lessonBody.textContent = lsn.body;

    resetVideoWrap();

    if (lsn.video) {
        videoWrap.style.display = "block";

        if (isYouTube(lsn.video)) {
            const vid = youtubeIdFromUrl(lsn.video);

            const holder = document.createElement("div");
            holder.id = "ytplayer";
            videoWrap.appendChild(holder);

            function build() {
                ytPlayer = new YT.Player("ytplayer", {
                    width: "100%",
                    height: "360",
                    videoId: vid,
                    playerVars: { rel: 0, modestbranding: 1 },

                    events: {
                        onStateChange: (e) => {
                            if (e.data === 0 && !autoMarked) {
                                autoMarked = true;
                                markComplete(true);
                                playCompletionSound();
                                showNotification("🎉 Excellent! You completed this lesson!");
                            }
                        },
                    },
                });
            }

            if (window.YT && window.YT.Player) {
                build();
            } else {
                window.onYouTubeIframeAPIReady = build;
            }
        } else {
            const v = document.createElement("video");
            v.controls = true;
            v.src = lsn.video;

            v.addEventListener("ended", () => {
                if (!autoMarked) {
                    autoMarked = true;
                    markComplete(true);
                    playCompletionSound();
                    showNotification("🎉 Excellent! You completed this lesson!");
                }
            });

            videoWrap.appendChild(v);
        }
    }

    showTab("content");
}

// ===============================
// MARK LESSON COMPLETE
// ===============================
async function markComplete(auto = false) {
    if (!currentLesson) return;

    const r = await fetch("/api/lesson/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lesson_id: currentLesson.id }),
    });

    const j = await r.json();

    if (j.ok) {
        // تحديث النقاط والمستوى والتقدم
        pointsDiv.textContent = j.points;
        levelDiv.textContent = j.level;
        progressText.textContent = j.progress_pct + "%";

        // لو فيه إنجازات جديدة، نطلع البوب أب فقط
        if (j.new_achievements?.length) {
            showAchievementPopup(j.new_achievements);
        }

        // مهم: نحدث شاشة الإنجازات والدashboard دايمًا
        await renderAchievements();
        await refreshDashboard();

        if (!auto) alert("Lesson completed! +50 points");
    } else {
        alert(j.msg || "Error");
    }
}

markCompleteBtn.addEventListener("click", () => markComplete(false));

// ===============================
// QUIZ
// ===============================
const quizTitle = document.getElementById("quizTitle");
const quizForm = document.getElementById("quizForm");
const quizResult = document.getElementById("quizResult");

openQuizBtn.addEventListener("click", () => {
    if (!currentLesson) {
        alert("Open a lesson first.");
        return;
    }

    buildQuiz(currentLesson);
    showTab("quiz");
});

async function buildQuiz(lsn) {
    quizTitle.textContent = "Quiz – " + lsn.title;
    quizForm.innerHTML = "";
    quizResult.textContent = "";

    const res = await fetch(`/api/quizzes/${lsn.id}`);
    const quizzes = await res.json();

    if (!quizzes.length) {
        quizForm.innerHTML = "<p>No quiz for this lesson.</p>";
        return;
    }

    quizzes.forEach((q, idx) => {
        const qDiv = document.createElement("div");
        qDiv.classList.add("question-block");
        qDiv.innerHTML = `<h4>${idx + 1}. ${q.question}</h4>`;

        const opts = JSON.parse(q.options_json);
        opts.forEach((opt, i) => {
            const id = `q${idx}_opt${i}`;
            qDiv.innerHTML += `
        <label for="${id}">
          <input type="radio" name="q${idx}" id="${id}" value="${i}"> ${opt}
        </label><br>
      `;
        });

        quizForm.appendChild(qDiv);
    });

    const submit = document.createElement("button");
    submit.textContent = "Submit Quiz";
    submit.type = "submit";
    quizForm.appendChild(submit);

    quizForm.onsubmit = async (e) => {
        e.preventDefault();

        const answers = [];
        quizzes.forEach((q, idx) => {
            const chosen = quizForm.querySelector(
                `input[name=q${idx}]:checked`
            );
            answers.push(chosen ? parseInt(chosen.value) : -1);
        });

        const r = await fetch(`/api/submit_quiz/${lsn.id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ answers }),
        });

        const data = await r.json();

        quizResult.textContent = `You scored ${data.score}/${data.total} – ${data.result}`;

        if (data.result === "Passed") {
            playCompletionSound();
            showNotification("🎉 You passed the quiz!");

            // تحديث النقاط والمستوى
            pointsDiv.textContent = data.points;
            levelDiv.textContent = data.level;

            // تحديث التقدم لو رجع من الـ API
            if (typeof data.progress_pct !== "undefined") {
                progressText.textContent = data.progress_pct + "%";
            }

            // لو فيه إنجازات جديدة من الكويز
            if (data.new_achievements?.length) {
                showAchievementPopup(data.new_achievements);
            }

            // تحديث الإنجازات والdashboard بعد كل كويز ناجح
            await renderAchievements();
            await refreshDashboard();
        }

    };
}

// ===============================
// ACHIEVEMENTS
// ===============================
const achContent = document.getElementById("achievementsContent");

async function renderAchievements() {
    const j = await (await fetch("/api/user/achievements")).json();

    if (!j.badges?.length) {
        achContent.innerHTML =
            "<p>No achievements yet. Complete lessons and quizzes!</p>";
        return;
    }

    achContent.innerHTML =
        "<ul>" +
        j.badges
            .map(
                (b) =>
                    `<li>🏅 <b>${b.name}</b> — <small>${b.description}</small></li>`
            )
            .join("") +
        "</ul>";
}

// ===============================
// FORUM
// ===============================
const postForm = document.getElementById("postForm");
const postsDiv = document.getElementById("posts");

if (postForm) {
    postForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const txt = new FormData(postForm).get("content");

        const r = await fetch("/api/forum", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ content: txt }),
        });

        const j = await r.json();

        if (j.ok) {
            postForm.reset();
            renderForum();
        } else {
            alert(j.msg || "Error");
        }
    });
}

async function renderForum() {
    const posts = await (await fetch("/api/forum")).json();

    postsDiv.innerHTML = posts
        .map(
            (p) => `
      <div class="card">
        <div class="row" style="justify-content:space-between">
          <strong>${p.by}</strong>
          <small>${p.ts}</small>
        </div>
        <p>${p.text}</p>
      </div>
    `
        )
        .join("");
}

// ===============================
// ACHIEVEMENT POPUP
// ===============================
const popup = document.getElementById("achievementPopup");
const popupBody = document.getElementById("popupBody");

function showAchievementPopup(names) {
    popupBody.textContent = Array.isArray(names)
        ? names.join(", ")
        : String(names);

    popup.style.display = "flex";

    const a = document.getElementById("achSound");
    if (a) {
        try {
            a.currentTime = 0;
            a.play();
        } catch { }
    }

    setTimeout(() => (popup.style.display = "none"), 4000);
}

// ===============================
// SUPPORT CHAT
// ===============================
const supportMessagesDiv = document.getElementById("supportMessages");
const supportInput = document.getElementById("supportInput");
const supportSendBtn = document.getElementById("supportSendBtn");

async function renderSupport() {
    if (!supportMessagesDiv) return;

    const res = await fetch("/api/support");
    const j = await res.json();

    if (!j.ok) {
        supportMessagesDiv.innerHTML =
            "<p>Please log in to contact support.</p>";
        return;
    }

    if (!j.messages.length) {
        supportMessagesDiv.innerHTML =
            "<p>No messages yet. You can start by sending a message below.</p>";
        return;
    }

    supportMessagesDiv.innerHTML = "";

    j.messages.forEach((m) => {
        const div = document.createElement("div");
        div.className = "support-msg " + (m.from_admin ? "admin" : "user");
        div.innerHTML = `
      <div>${m.text}</div>
      <div class="support-meta">${m.from_admin ? "Support" : "You"
            } • ${m.ts}</div>
    `;
        supportMessagesDiv.appendChild(div);
    });

    supportMessagesDiv.scrollTop = supportMessagesDiv.scrollHeight;
}

supportSendBtn?.addEventListener("click", async () => {
    const txt = supportInput.value.trim();
    if (!txt) return;

    const r = await fetch("/api/support", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: txt }),
    });

    const j = await r.json();
    if (j.ok) {
        supportInput.value = "";
        renderSupport();
    } else {
        alert(j.msg || "Error");
    }
});

// ===============================
// FONT SIZE CONTROLS
// ===============================
const fontMinus = document.getElementById("fontMinus");
const fontPlus = document.getElementById("fontPlus");

function applyFontScale(scale) {
    document.documentElement.style.fontSize = scale + "%";
}

let fontScale = parseInt(localStorage.getItem("fontScale") || "100", 10);
applyFontScale(fontScale);

fontMinus?.addEventListener("click", () => {
    fontScale = Math.max(80, fontScale - 10);
    applyFontScale(fontScale);
    localStorage.setItem("fontScale", fontScale);
});

fontPlus?.addEventListener("click", () => {
    fontScale = Math.min(140, fontScale + 10);
    applyFontScale(fontScale);
    localStorage.setItem("fontScale", fontScale);
});

// ===============================
// SOUND + NOTIFICATIONS
// ===============================
function playCompletionSound() {
    const sound = document.getElementById("completeSound");
    if (sound) {
        sound.volume = 0.6;
        try {
            sound.play();
        } catch { }
    }
}

function showNotification(msg) {
    const note = document.createElement("div");

    note.textContent = msg;
    note.style.position = "fixed";
    note.style.bottom = "20px";
    note.style.right = "20px";
    note.style.background = "#ffbcd9";
    note.style.color = "#333";
    note.style.padding = "15px 20px";
    note.style.borderRadius = "10px";
    note.style.fontWeight = "bold";
    note.style.zIndex = "9999";
    note.style.boxShadow = "0 3px 6px rgba(0,0,0,0.2)";

    document.body.appendChild(note);

    setTimeout(() => note.remove(), 3500);
}

// ===============================
// AUTO LOGIN CHECK
// ===============================
(async function boot() {
    const s = await (await fetch("/api/session")).json();
    if (s.ok) afterLogin();
    else showTab("auth");
})();
