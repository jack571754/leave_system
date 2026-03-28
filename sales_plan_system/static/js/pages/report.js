(function () {
    function readJsonScript(id, fallback) {
        const raw = document.getElementById(id);
        if (!raw) {
            return fallback;
        }

        try {
            return JSON.parse(raw.textContent || '');
        } catch (error) {
            return fallback;
        }
    }

    window.reportData = function () {
        return {
            planMonth: '',
            groupBy: '',
            approvalStatus: '',
            init() {
                const config = readJsonScript('report-config', {});
                this.planMonth = config.planMonth || '';
                this.groupBy = config.groupBy || 'department';
                this.approvalStatus = config.approvalStatus || '';
            },
            getConfig() {
                return readJsonScript('report-config', {});
            },
            loadReport() {
                const config = this.getConfig();
                const params = new URLSearchParams({
                    month: this.planMonth,
                    group_by: this.groupBy,
                    approval_status: this.approvalStatus,
                });
                window.location.href = `${config.reportUrl}?${params.toString()}`;
            },
            exportUrl() {
                const config = this.getConfig();
                const params = new URLSearchParams({
                    month: this.planMonth,
                    approval_status: this.approvalStatus,
                });
                return `${config.exportUrl}?${params.toString()}`;
            },
        };
    };
})();
