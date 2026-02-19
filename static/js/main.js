document.addEventListener('DOMContentLoaded', () => {

    const ease = 'cubic-bezier(0.4, 0, 0.2, 1)';
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isMobile = window.innerWidth < 768;

    /* ── Mobile hamburger menu ── */
    const navToggle = document.getElementById('navToggle');
    const navList = document.getElementById('navList');
    if (navToggle && navList) {
        navToggle.addEventListener('click', () => {
            const isOpen = navList.classList.toggle('open');
            navToggle.innerHTML = isOpen
                ? '<i class="fa-solid fa-xmark"></i>'
                : '<i class="fa-solid fa-bars"></i>';
        });
        navList.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', () => {
                navList.classList.remove('open');
                navToggle.innerHTML = '<i class="fa-solid fa-bars"></i>';
            });
        });
    }


    if (!isMobile && !prefersReduced) {
        const glow = document.createElement('div');
        glow.className = 'cursor-glow';
        document.body.appendChild(glow);
        document.addEventListener('mousemove', (e) => {
            glow.style.left = e.clientX + 'px';
            glow.style.top = e.clientY + 'px';
        });
    }


    /* Gold floating particles */
    if (!isMobile && !prefersReduced) {
        const particleCSS = document.createElement('style');
        particleCSS.textContent = `
            @keyframes floatUp {
                0%   { opacity: 0; transform: translateY(0) scale(0); }
                15%  { opacity: 1; transform: translateY(-20px) scale(1); }
                100% { opacity: 0; transform: translateY(-100px) scale(0.2); }
            }
        `;
        document.head.appendChild(particleCSS);

        function spawnParticle() {
            const p = document.createElement('div');
            const size = 2 + Math.random() * 4;
            const colors = ['rgba(198,167,94,0.3)', 'rgba(180,150,70,0.25)', 'rgba(212,186,122,0.25)', 'rgba(192,57,43,0.2)', 'rgba(231,76,60,0.18)'];
            const x = Math.random() * window.innerWidth;
            const dur = 3 + Math.random() * 5;
            p.style.cssText =
                'position:fixed;border-radius:50%;pointer-events:none;z-index:0;' +
                'width:' + size + 'px;height:' + size + 'px;' +
                'background:' + colors[Math.floor(Math.random() * colors.length)] + ';' +
                'left:' + x + 'px;bottom:-10px;opacity:0;' +
                'box-shadow:0 0 ' + (size * 4) + 'px rgba(198,167,94,0.15);' +
                'animation:floatUp ' + dur + 's ease forwards;';
            document.body.appendChild(p);
            setTimeout(() => p.remove(), dur * 1000);
        }
        setInterval(spawnParticle, 1200);
    }


    const backToTop = document.getElementById('back-to-top');
    if (backToTop) {
        window.addEventListener('scroll', () => {
            backToTop.style.display = window.pageYOffset > 300 ? 'block' : 'none';
        });
        backToTop.addEventListener('click', (e) => {
            e.preventDefault();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }


    if (!prefersReduced) {
        const targets = document.querySelectorAll(
            '.card, .menu-card, section, .hero-banner, table, .form-grid, .admin-nav, h2, h3, .review-card, .review-form-card'
        );
        targets.forEach(el => { if (!el.classList.contains('animate-in')) el.classList.add('animate-in'); });

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

        document.querySelectorAll('.animate-in').forEach(el => observer.observe(el));
    }


    if (!isMobile && !prefersReduced) {
        document.querySelectorAll('.card, .menu-card, .review-card').forEach(card => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width - 0.5;
                const y = (e.clientY - rect.top) / rect.height - 0.5;
                card.style.transform = `translateY(-6px) perspective(800px) rotateX(${y * -4}deg) rotateY(${x * 4}deg)`;
            });
            card.addEventListener('mouseleave', () => {
                card.style.transition = `all 0.5s ${ease}`;
                card.style.transform = '';
                setTimeout(() => { card.style.transition = ''; }, 500);
            });
            card.addEventListener('mouseenter', () => {
                card.style.transition = 'transform 0.08s ease';
            });
        });
    }


    const menuSearch = document.getElementById('menu-search');
    const filterBtns = document.querySelectorAll('.filter-btn');
    const menuCards = document.querySelectorAll('.menu-card');

    if (menuSearch) {
        menuSearch.addEventListener('keyup', () => {
            const active = document.querySelector('.filter-btn.active');
            filterMenu(menuSearch.value.toLowerCase(), active ? active.dataset.filter : 'all');
        });
    }

    filterBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const category = btn.dataset.filter;
            
            // Перевірка віку для категорії "Алкоголь"
            if (category === 'Алкоголь' && !localStorage.getItem('age_confirmed')) {
                e.preventDefault();
                showAgeVerification(() => {
                    // Якщо підтвердив вік
                    const current = document.querySelector('.filter-btn.active');
                    if (current) current.classList.remove('active');
                    btn.classList.add('active');
                    const search = document.getElementById('menu-search');
                    filterMenu(search ? search.value.toLowerCase() : '', btn.dataset.filter);
                });
                return;
            }
            
            const current = document.querySelector('.filter-btn.active');
            if (current) current.classList.remove('active');
            btn.classList.add('active');
            const search = document.getElementById('menu-search');
            filterMenu(search ? search.value.toLowerCase() : '', btn.dataset.filter);
        });
    });

    function filterMenu(searchTerm, filterTerm) {
        menuCards.forEach(card => {
            const title = card.querySelector('h4');
            if (!title) return;
            const match = title.textContent.toLowerCase().includes(searchTerm);
            const catMatch = filterTerm === 'all' || card.dataset.category === filterTerm;
            if (match && catMatch) {
                card.style.display = '';
                if (!prefersReduced) card.style.animation = `revealUp 0.35s ${ease} forwards`;
            } else {
                card.style.display = 'none';
            }
        });
    }

    // Модальне вікно для підтвердження віку 18+
    function showAgeVerification(onConfirm) {
        const modal = document.createElement('div');
        modal.id = 'ageVerificationModal';
        modal.style.cssText = 'position:fixed;inset:0;z-index:10001;background:rgba(0,0,0,0.95);' +
            'backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);display:flex;' +
            'align-items:center;justify-content:center;animation:fadeIn 0.3s ease;';
        
        modal.innerHTML = `
            <div style="background:var(--bg-card);border-radius:var(--radius-lg);padding:2.5rem;
                border:2px solid rgba(192,57,43,0.4);box-shadow:0 20px 60px rgba(0,0,0,0.8);
                max-width:500px;width:calc(100% - 2rem);text-align:center;animation:scaleIn 0.3s ease;">
                <div style="font-size:3rem;margin-bottom:1rem;">🔞</div>
                <h2 style="font-family:'Space Grotesk',sans-serif;font-size:1.6rem;font-weight:700;
                    color:var(--crimson-light);margin:0 0 1rem;">Підтвердження віку</h2>
                <p style="color:var(--text-secondary);font-size:0.95rem;line-height:1.6;margin:0 0 2rem;">
                    Ця категорія містить алкогольні напої.<br>
                    Відповідно до законодавства України, доступ до алкогольної продукції
                    дозволений лише особам, які досягли <strong style="color:var(--gold);">18 років</strong>.
                </p>
                <div style="background:rgba(192,57,43,0.1);border:1px solid rgba(192,57,43,0.3);
                    border-radius:var(--radius);padding:1rem;margin-bottom:2rem;">
                    <p style="color:var(--text);font-size:0.88rem;margin:0;line-height:1.5;">
                        ⚠️ Надання недостовірної інформації про вік може призвести до відповідальності
                        згідно з чинним законодавством України.
                    </p>
                </div>
                <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;">
                    <button id="ageConfirmYes" style="padding:12px 32px;background:var(--gradient-btn);
                        color:var(--bg-deep);border:none;border-radius:var(--radius-pill);font-weight:700;
                        font-size:0.95rem;cursor:pointer;transition:all 0.25s ease;font-family:'Space Grotesk',sans-serif;"
                        onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(198,167,94,0.4)';"
                        onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='none';">
                        ✓ Мені є 18 років
                    </button>
                    <button id="ageConfirmNo" style="padding:12px 32px;background:rgba(192,57,43,0.2);
                        color:var(--crimson-light);border:1px solid rgba(192,57,43,0.4);border-radius:var(--radius-pill);
                        font-weight:600;font-size:0.95rem;cursor:pointer;transition:all 0.25s ease;"
                        onmouseover="this.style.background='rgba(192,57,43,0.3)';"
                        onmouseout="this.style.background='rgba(192,57,43,0.2)';">
                        ✗ Мені немає 18
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        document.body.style.overflow = 'hidden';
        
        const yesBtn = modal.querySelector('#ageConfirmYes');
        const noBtn = modal.querySelector('#ageConfirmNo');
        
        yesBtn.addEventListener('click', () => {
            localStorage.setItem('age_confirmed', '1');
            modal.style.animation = 'fadeOut 0.2s ease';
            setTimeout(() => {
                modal.remove();
                document.body.style.overflow = '';
                if (onConfirm) onConfirm();
            }, 200);
        });
        
        noBtn.addEventListener('click', () => {
            modal.style.animation = 'fadeOut 0.2s ease';
            setTimeout(() => {
                modal.remove();
                document.body.style.overflow = '';
                // Повертаємо на категорію "Всі"
                const allBtn = document.querySelector('.filter-btn[data-filter="all"]');
                if (allBtn) allBtn.click();
            }, 200);
        });
    }


    if (!prefersReduced) {
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a:not([href^="#"]):not([target="_blank"])');
            if (!link) return;
            const href = link.getAttribute('href');
            if (href && !href.startsWith('http') && !href.startsWith('mailto:') && !href.startsWith('tel:') && !href.startsWith('javascript:')) {
                e.preventDefault();
                document.body.classList.add('fade-out');
                setTimeout(() => { window.location.href = href; }, 300);
            }
        });
    }


    document.querySelectorAll('.flash-messages .alert').forEach(alert => {
        setTimeout(() => {
            alert.style.transition = `opacity 0.4s ${ease}, transform 0.4s ${ease}`;
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });


    if (!prefersReduced && !isMobile) {
        const hero = document.querySelector('.hero-banner');
        if (hero) {
            window.addEventListener('scroll', () => {
                hero.style.transform = `translateY(${window.pageYOffset * 0.15}px)`;
            }, { passive: true });
        }
    }


    (function() {
        const toggle = document.getElementById('chatToggle');
        const panel = document.getElementById('chatPanel');
        const closeBtn = document.getElementById('chatClose');
        const input = document.getElementById('chatInput');
        const sendBtn = document.getElementById('chatSend');
        const messagesDiv = document.getElementById('chatMessages');
        const userListDiv = document.getElementById('chatUserList');
        const inputRow = document.getElementById('chatInputRow');
        const badge = document.getElementById('chatBadge');
        const chatTitle = document.getElementById('chatTitle');
        const backBtn = document.getElementById('chatBack');
        const closeChatBtn = document.getElementById('chatCloseChat');
        const isAdmin = window.__IS_ADMIN__ || false;
        const myUserId = window.__USER_ID__ || 0;

        if (!toggle || !panel) return;

        let activeUserId = isAdmin ? null : myUserId;
        let activeName = '';
        let lastMsgId = 0;
        let _csrfToken = '';

        function escapeHtml(str) {
            const d = document.createElement('div');
            d.textContent = str;
            return d.innerHTML;
        }

        function ensureCsrf() {
            if (_csrfToken) return Promise.resolve(_csrfToken);
            return fetch('/api/csrf', {credentials:'same-origin'}).then(r=>r.json()).then(d=>{ _csrfToken=d.csrfToken; return _csrfToken; });
        }

        toggle.addEventListener('click', () => {
            panel.classList.toggle('open');
            if (panel.classList.contains('open')) {
                lastMsgId = 0;
                if (isAdmin) { loadUserList(); } else { loadMessages(myUserId); }
            }
        });
        closeBtn.addEventListener('click', () => { panel.classList.remove('open'); });

        function apiHeaders() {
            return {};
        }

        function checkUnread() {
            fetch('/api/chat/unread', { headers: apiHeaders(), credentials: 'same-origin' })
            .then(r => r.json())
            .then(d => {
                if (d.count > 0) { badge.textContent = d.count > 9 ? '9+' : d.count; badge.style.display = 'flex'; }
                else { badge.style.display = 'none'; }
            }).catch(() => {});
        }
        checkUnread();
        setInterval(checkUnread, 8000);

        function loadUserList() {
            fetch('/api/chat/users', { headers: apiHeaders(), credentials: 'same-origin' })
            .then(r => r.json())
            .then(users => {
                userListDiv.innerHTML = '';
                if (!Array.isArray(users) || users.length === 0) {
                    userListDiv.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:0.85rem;">Активних чатів немає</div>';
                    return;
                }
                users.forEach(u => {
                    const item = document.createElement('div');
                    item.className = 'chat-user-item';
                    item.innerHTML = '<strong>' + escapeHtml(u.nickname) + '</strong>' +
                        (u.unread > 0 ? '<span class="chat-user-badge">' + parseInt(u.unread) + '</span>' : '') +
                        '<span class="chat-user-time">' + escapeHtml(u.last_msg) + '</span>';
                    item.addEventListener('click', () => openUserChat(u.user_id, u.nickname));
                    userListDiv.appendChild(item);
                });
            }).catch(() => {});
        }

        function openUserChat(userId, nickname) {
            activeUserId = userId; activeName = nickname;
            lastMsgId = 0;
            userListDiv.style.display = 'none';
            messagesDiv.style.display = 'flex';
            inputRow.style.display = 'flex';
            chatTitle.innerHTML = '<i class="fa-solid fa-user"></i> ' + escapeHtml(nickname);
            if (backBtn) backBtn.style.display = '';
            if (closeChatBtn) closeChatBtn.style.display = '';
            loadMessages(userId, true);
            input.focus();
        }

        if (backBtn) {
            backBtn.addEventListener('click', () => {
                activeUserId = null;
                messagesDiv.style.display = 'none';
                inputRow.style.display = 'none';
                userListDiv.style.display = '';
                chatTitle.innerHTML = '<i class="fa-solid fa-headset"></i> Чати';
                backBtn.style.display = 'none';
                if (closeChatBtn) closeChatBtn.style.display = 'none';
                loadUserList();
            });
        }

        if (closeChatBtn) {
            closeChatBtn.addEventListener('click', () => {
                if (!activeUserId) return;
                if (!confirm('Закрити чат з ' + activeName + '?')) return;
                ensureCsrf().then(csrf => {
                    fetch('/api/chat/' + activeUserId + '/close', {
                        method: 'POST', headers: {'X-CSRF-Token': csrf}, credentials: 'same-origin'
                    }).then(() => { if (backBtn) backBtn.click(); }).catch(() => {});
                });
            });
        }

        function loadMessages(userId, forceRefresh) {
            if (!userId) return;
            fetch('/api/chat/' + userId, { headers: apiHeaders(), credentials: 'same-origin' })
            .then(r => {
                if (!r.ok) console.error('Chat load failed:', r.status);
                return r.json();
            })
            .then(msgs => {
                if (!Array.isArray(msgs)) { console.error('Chat msgs not array:', msgs); return; }
                if (forceRefresh || lastMsgId === 0) {
                    messagesDiv.innerHTML = '';
                    lastMsgId = 0;
                }
                let added = false;
                msgs.forEach(m => {
                    if (m.id > lastMsgId) {
                        appendMessage(m);
                        lastMsgId = m.id;
                        added = true;
                    }
                });
                if (msgs.length === 0 && messagesDiv.children.length === 0) {
                    messagesDiv.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:0.85rem;">Почніть розмову</div>';
                }
                if (added || forceRefresh) messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }).catch(() => {});
        }

        function appendMessage(m) {
            const placeholder = messagesDiv.querySelector('[style*="text-align:center"]');
            if (placeholder) placeholder.remove();
            const div = document.createElement('div');
            const isMine = isAdmin ? m.is_admin : !m.is_admin;
            div.className = 'chat-msg ' + (isMine ? 'user' : 'admin');
            let html = '';
            if (isAdmin && !isMine) html += '<span class="msg-sender">' + escapeHtml(activeName || 'Користувач') + '</span>';
            else if (isAdmin && isMine) html += '<span class="msg-sender">Ви</span>';
            html += escapeHtml(m.text) + '<span class="msg-time">' + escapeHtml(m.created_at) + '</span>';
            div.innerHTML = html;
            messagesDiv.appendChild(div);
        }

        function sendMessage() {
            const text = input.value.trim();
            const targetId = isAdmin ? activeUserId : myUserId;
            if (!text || !targetId) return;
            input.value = '';
            ensureCsrf().then(csrf => {
                const hdrs = { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf };
                fetch('/api/chat/' + targetId, {
                    method: 'POST', headers: hdrs, credentials: 'same-origin',
                    body: JSON.stringify({ text: text })
                })
                .then(r => {
                    if (!r.ok) { console.error('Chat send failed:', r.status); return null; }
                    return r.json();
                })
                .then(m => {
                    if (m && m.id) {
                        appendMessage(m);
                        if (m.id > lastMsgId) lastMsgId = m.id;
                        messagesDiv.scrollTop = messagesDiv.scrollHeight;
                    }
                })
                .catch(e => console.error('Chat send error:', e));
            });
        }

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMessage(); });

        setInterval(() => {
            if (!panel.classList.contains('open')) return;
            if (isAdmin && !activeUserId) loadUserList();
            else if (activeUserId) loadMessages(activeUserId);
        }, 4000);
    })();

    // ══════ REVIEWS ══════
    (function() {
        const starRating = document.getElementById('starRating');
        const reviewText = document.getElementById('reviewText');
        const submitBtn = document.getElementById('submitReview');
        const errorDiv = document.getElementById('reviewError');

        if (!starRating || !submitBtn) return;

        let selectedStars = 0;
        let _rvCsrf = '';
        const stars = starRating.querySelectorAll('span');

        function getCsrf() {
            if (_rvCsrf) return Promise.resolve(_rvCsrf);
            return fetch('/api/csrf', {credentials:'same-origin'}).then(r=>r.json()).then(d=>{ _rvCsrf=d.csrfToken; return _rvCsrf; });
        }

        stars.forEach(star => {
            star.addEventListener('click', () => { selectedStars = parseInt(star.dataset.star); updateStars(); });
            star.addEventListener('mouseenter', () => { highlightStars(parseInt(star.dataset.star)); });
        });
        starRating.addEventListener('mouseleave', () => { updateStars(); });

        function highlightStars(n) { stars.forEach(s => { s.classList.toggle('active', parseInt(s.dataset.star) <= n); }); }
        function updateStars() { highlightStars(selectedStars); }

        submitBtn.addEventListener('click', () => {
            errorDiv.textContent = '';
            const text = reviewText.value.trim();
            if (!selectedStars) { errorDiv.textContent = 'Оберіть оцінку'; return; }
            if (!text) { errorDiv.textContent = 'Напишіть відгук'; return; }
            submitBtn.disabled = true;
            submitBtn.textContent = 'Надсилання...';

            getCsrf().then(csrf => {
                fetch('/api/reviews', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
                    credentials: 'same-origin',
                    body: JSON.stringify({ text: text, stars: selectedStars })
                })
                .then(r => {
                    if (r.status === 409) { errorDiv.textContent = 'Ви вже залишали відгук'; submitBtn.disabled = false; submitBtn.textContent = 'Надіслати'; return null; }
                    if (!r.ok) throw new Error('Status ' + r.status);
                    return r.json();
                })
                .then(data => { if (data && data.id) window.location.reload(); })
                .catch((err) => { errorDiv.textContent = 'Помилка: ' + err.message; submitBtn.disabled = false; submitBtn.textContent = 'Надіслати'; });
            });
        });
    })();

    // ══════ ADMIN: Delete reviews ══════
    (function() {
        let _delCsrf = '';
        function getCsrf() {
            if (_delCsrf) return Promise.resolve(_delCsrf);
            return fetch('/api/csrf', {credentials:'same-origin'}).then(r=>r.json()).then(d=>{ _delCsrf=d.csrfToken; return _delCsrf; });
        }
        document.querySelectorAll('.review-delete-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const reviewId = btn.dataset.reviewId;
                if (!reviewId || !confirm('Видалити цей відгук?')) return;
                btn.disabled = true; btn.textContent = '...';
                getCsrf().then(csrf => {
                    fetch('/api/reviews/' + reviewId, { method: 'DELETE', headers: {'X-CSRF-Token': csrf}, credentials: 'same-origin' })
                    .then(r => {
                        if (r.ok) {
                            const card = btn.closest('.review-card');
                            if (card) { card.style.transition = 'opacity 0.3s ease, transform 0.3s ease'; card.style.opacity = '0'; card.style.transform = 'translateX(20px)'; setTimeout(() => card.remove(), 300); }
                        } else { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-trash"></i> Видалити'; }
                    }).catch(() => { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-trash"></i> Видалити'; });
                });
            });
        });
    })();

});
