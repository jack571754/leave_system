(function () {
    function updateClock() {
        const target = document.getElementById('current-time');
        if (!target) {
            return;
        }
        const now = new Date();
        const date = now.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'long',
        });
        const time = now.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
        });
        target.innerHTML = `<div>${date}</div><div>${time}</div>`;
    }

    function updateApprovalBadge() {
        const badge = document.getElementById('approval-badge');
        const config = window.appShell || {};
        if (!badge || !config.approvalBadgeUrl) {
            return;
        }

        fetch(config.approvalBadgeUrl)
            .then((response) => response.json())
            .then((data) => {
                if (data.count > 0) {
                    badge.textContent = data.count;
                    badge.classList.remove('hidden');
                } else {
                    badge.classList.add('hidden');
                }
            })
            .catch(() => {});
    }

    updateClock();
    window.setInterval(updateClock, 1000);

    if ((window.appShell || {}).shouldPollApprovals) {
        updateApprovalBadge();
        window.setInterval(updateApprovalBadge, 60000);
    }
})();
