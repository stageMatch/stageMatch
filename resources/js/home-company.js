document.addEventListener('DOMContentLoaded', () => {
    // --- State ---
    const state = {
        activeSection: 'Dashboard',
        students: [
            { id: 1, name: 'Marco Rossi', class: '5A INF', school: 'ITIS Paleocapa', skills: ['Python', 'Flask', 'SQL'], match: 95 },
            { id: 2, name: 'Sofia Bianchi', class: '5B INF', school: 'ITIS Paleocapa', skills: ['JavaScript', 'React', 'CSS'], match: 88 },
            { id: 3, name: 'Luca Verdi', class: '4A INF', school: 'ITIS Paleocapa', skills: ['C++', 'Linux', 'Java'], match: 82 },
            { id: 4, name: 'Giulia Neri', class: '5A INF', school: 'ITIS Paleocapa', skills: ['Python', 'Data Science'], match: 79 }
        ]
    };

    // --- Selectors ---
    const navItems = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.content');
    const hamburger = document.querySelector('.hamburger');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    const logoutBtn = document.getElementById('navLogout');
    const logoutOverlay = document.getElementById('logoutOverlay');
    const logoutCancel = document.getElementById('logoutCancel');
    const logoutConfirm = document.getElementById('logoutConfirm');

    // --- Navigation Logic ---
    function switchSection(sectionId) {
        const targetId = 'section' + sectionId;

        sections.forEach(s => s.classList.add('hidden'));
        const target = document.getElementById(targetId);
        if (target) {
            target.classList.remove('hidden');
            target.classList.add('animate-in');
        }

        navItems.forEach(item => {
            item.classList.toggle('active', item.id === 'nav' + sectionId);
        });

        state.activeSection = sectionId;

        // On mobile, close sidebar after navigation
        if (window.innerWidth <= 1100) {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        }

        if (sectionId === 'Studenti') {
            renderStudents();
        }
    }

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            if (item.id === 'navLogout') return;
            e.preventDefault();
            const sectionName = item.id.replace('nav', '');
            switchSection(sectionName);
        });
    });

    // --- Sidebar & Mobile ---
    hamburger?.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('active');
    });

    overlay?.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
    });

    // --- Logout ---
    logoutBtn?.addEventListener('click', (e) => {
        e.preventDefault();
        logoutOverlay.classList.add('active');
    });

    logoutCancel?.addEventListener('click', () => {
        logoutOverlay.classList.remove('active');
    });

    logoutConfirm?.addEventListener('click', () => {
        window.location.href = '/auth/logout';
    });

    // --- Rendering Studenti ---
    function renderStudents() {
        const list = document.getElementById('studentiList');
        const loading = document.getElementById('studentiLoading');
        const empty = document.getElementById('studentiEmpty');

        if (!list) return;

        // Simula caricamento
        loading.style.display = 'flex';
        list.style.display = 'none';
        empty.style.display = 'none';

        setTimeout(() => {
            loading.style.display = 'none';

            if (state.students.length === 0) {
                empty.style.display = 'flex';
            } else {
                list.style.display = 'grid';
                list.innerHTML = state.students.map(st => `
                    <div class="st-card">
                        <div class="st-header">
                            <div class="st-avatar">${st.name.split(' ').map(n => n[0]).join('')}</div>
                            <div class="st-info">
                                <div class="st-name">${st.name}</div>
                                <div class="st-school">${st.school} · ${st.class}</div>
                            </div>
                            <div class="co-match">
                                <div class="co-pct">${st.match}%</div>
                                <div class="co-pct-label">Match</div>
                            </div>
                        </div>
                        <div class="st-skills">
                            ${st.skills.map(s => `<span class="st-skill">${s}</span>`).join('')}
                        </div>
                        <div class="st-footer">
                            <button class="st-contact-btn" onclick="alert('Funzionalità di contatto in arrivo!')">Contatta</button>
                        </div>
                    </div>
                `).join('');
            }

            // Aggiorna badge e stats
            const badge = document.getElementById('badgeStudenti');
            if (badge) badge.textContent = state.students.length;

            const statMatches = document.getElementById('statMatches');
            if (statMatches) statMatches.textContent = state.students.length;

            const statInteressi = document.getElementById('statInteressi');
            if (statInteressi) statInteressi.textContent = Math.floor(state.students.length * 0.7);
        }, 800);
    }

    // --- Dashboard Initial Stats ---
    document.getElementById('statViews').textContent = '124';

    // Hero button
    document.getElementById('btnGoToStudents')?.addEventListener('click', () => {
        switchSection('Studenti');
    });
});
