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

    window.taskEditor = function () {
        return {
            saving: false,
            VTableSheetCtor: null,
            sheetInstance: null,
            activeTable: null,
            applyingPatch: false,
            resizeHandler: null,
            columns: [],
            rowMeta: [],
            rowKeyMap: new Map(),
            stats: {
                skuRows: 0,
                totalQty: 0,
                totalAmount: 0,
            },
            init() {
                this.initStats();
                this.loadVTable();
            },
            getConfig() {
                return readJsonScript('task-editor-config', {});
            },
            getRecords() {
                return readJsonScript('task-grid-records', []);
            },
            getTargetMonths() {
                return readJsonScript('task-target-months', []);
            },
            initStats() {
                const records = this.getRecords();
                this.stats.skuRows = new Set(records.map((item) => item.sku_id)).size;
                this.stats.totalQty = records.reduce((sum, item) => sum + Number(item.sales_qty || 0), 0);
                this.stats.totalAmount = records.reduce((sum, item) => sum + Number(item.sales_amount || 0), 0);
            },
            formatMoney(value) {
                return Number(value || 0).toFixed(2);
            },
            formatNumber(value) {
                return Number(value || 0).toLocaleString('zh-CN');
            },
            async loadVTable() {
                if (!window.VTableSheet) {
                    return;
                }
                this.VTableSheetCtor = window.VTableSheet;
                this.initVTable();
            },
            buildGridModel(records, targetMonths) {
                const config = this.getConfig();
                const editable = !!config.canEdit;
                const skuMap = new Map();

                records.forEach((record) => {
                    if (!skuMap.has(record.sku_id)) {
                        skuMap.set(record.sku_id, {
                            sku_id: record.sku_id,
                            sku_code: record.sku_code,
                            sku_name: record.sku_name,
                            brand: record.brand || '-',
                            unit_price: Number(record.unit_price || 0),
                            months: {},
                            row_total_qty: 0,
                            row_total_amount: 0,
                        });
                    }

                    const row = skuMap.get(record.sku_id);
                    row.unit_price = Number(record.unit_price || row.unit_price || 0);
                    row.months[record.target_month] = {
                        sales_qty: Number(record.sales_qty || 0),
                        stock_qty: Number(record.stock_qty || 0),
                        sales_amount: Number(record.sales_amount || 0),
                    };
                    row.row_total_qty += Number(record.sales_qty || 0);
                    row.row_total_amount += Number(record.sales_amount || 0);
                });

                this.columns = [
                    { title: 'SKU 编码', field: 'sku_code', width: 130, editable: false },
                    { title: 'SKU 名称', field: 'sku_name', width: 240, editable: false },
                    { title: '品牌', field: 'brand', width: 140, editable: false },
                    { title: '单价', field: 'unit_price', width: 110, editable },
                ];

                targetMonths.forEach((month, index) => {
                    this.columns.push(
                        { title: `${month} / M+${index + 1} 销量`, field: `${month}__sales_qty`, width: 120, editable, month, metric: 'sales_qty' },
                        { title: `${month} / M+${index + 1} 库存`, field: `${month}__stock_qty`, width: 120, editable, month, metric: 'stock_qty' },
                        { title: `${month} / M+${index + 1} 销售额`, field: `${month}__sales_amount`, width: 140, editable: false, month, metric: 'sales_amount' },
                    );
                });

                this.columns.push(
                    { title: '合计销量', field: 'row_total_qty', width: 120, editable: false },
                    { title: '合计销售额', field: 'row_total_amount', width: 150, editable: false },
                );

                const rows = Array.from(skuMap.values()).map((row) => {
                    const values = [row.sku_code, row.sku_name, row.brand, row.unit_price];
                    targetMonths.forEach((month) => {
                        const monthData = row.months[month] || { sales_qty: 0, stock_qty: 0, sales_amount: 0 };
                        values.push(monthData.sales_qty, monthData.stock_qty, monthData.sales_amount);
                    });
                    values.push(row.row_total_qty, row.row_total_amount);
                    return values;
                });

                this.rowMeta = Array.from(skuMap.values()).map((row) => ({
                    sku_id: row.sku_id,
                    sku_code: row.sku_code,
                }));
                this.rowKeyMap = new Map(this.rowMeta.map((row, index) => [String(row.sku_id), index]));
                return rows;
            },
            buildSheetOptions(dataRows) {
                return {
                    showFormulaBar: false,
                    showSheetTab: false,
                    defaultRowHeight: 32,
                    defaultColWidth: 120,
                    sheets: [
                        {
                            sheetKey: 'task-grid',
                            sheetTitle: '任务明细',
                            active: true,
                            columns: this.columns.map((column) => ({
                                title: column.title,
                                width: column.width,
                            })),
                            data: dataRows,
                            showHeader: true,
                            frozenColCount: 4,
                        }
                    ],
                    theme: {
                        underlayBackgroundColor: '#f8fafc',
                    },
                };
            },
            initVTable() {
                const container = document.getElementById('task-vtable-container');
                const fallback = document.getElementById('task-report-fallback');
                if (!container || !this.VTableSheetCtor) {
                    return;
                }

                const rows = this.buildGridModel(this.getRecords(), this.getTargetMonths());
                try {
                    this.sheetInstance = new this.VTableSheetCtor(container, this.buildSheetOptions(rows));
                    this.activeTable = this.sheetInstance.getActiveSheet?.() || this.sheetInstance.activeSheet || null;
                    fallback?.classList.add('is-enhanced');
                    this.attachCellListener();
                    this.resizeHandler = () => this.resizeSheet();
                    window.addEventListener('resize', this.resizeHandler);
                    this.resizeSheet();
                } catch (error) {
                    console.error('VTableSheet init failed', error);
                    container.innerHTML = '<div class="grid-error">表格增强加载失败，已切换到兼容视图。</div>';
                    fallback?.classList.remove('is-enhanced');
                }
            },
            attachCellListener() {
                const config = this.getConfig();
                if (!config.canEdit || !this.activeTable || !this.activeTable.on) {
                    return;
                }

                this.activeTable.on('change_cell_value', (event) => {
                    if (this.applyingPatch) {
                        return;
                    }

                    const col = event?.col ?? event?.colIndex;
                    const row = event?.row ?? event?.rowIndex;
                    if (typeof col !== 'number' || typeof row !== 'number' || row <= 0) {
                        return;
                    }

                    const columnMeta = this.columns[col];
                    const rowMeta = this.rowMeta[row - 1];
                    if (!columnMeta || !rowMeta || !columnMeta.editable) {
                        return;
                    }

                    const nextValue = event?.currentValue ?? event?.changedValue ?? event?.value;
                    const body = new URLSearchParams({
                        sku_id: String(rowMeta.sku_id),
                        field: columnMeta.metric || columnMeta.field,
                        value: String(nextValue ?? ''),
                    });
                    if (columnMeta.month) {
                        body.set('target_month', columnMeta.month);
                    }

                    this.persistCellChange(body, rowMeta, columnMeta, row, col);
                });
            },
            resizeSheet() {
                if (!this.sheetInstance) {
                    return;
                }

                const container = document.getElementById('task-vtable-container');
                const width = container?.clientWidth || 1200;
                if (typeof this.sheetInstance.resize === 'function') {
                    this.sheetInstance.resize(width, 560);
                } else if (typeof this.sheetInstance.render === 'function') {
                    this.sheetInstance.render();
                }
            },
            getColumnIndex(field) {
                return this.columns.findIndex((column) => column.field === field);
            },
            setCellValue(col, row, value) {
                if (!this.activeTable) {
                    return;
                }

                if (typeof this.activeTable.changeCellValue === 'function') {
                    this.activeTable.changeCellValue(col, row, value);
                    return;
                }
                if (typeof this.activeTable.setCellValue === 'function') {
                    this.activeTable.setCellValue(col, row, value);
                }
            },
            applyServerPatch(payload, rowMeta) {
                const rowIndex = this.rowKeyMap.get(String(rowMeta.sku_id));
                if (rowIndex === undefined) {
                    return;
                }

                const visualRow = rowIndex + 1;
                const updatedRow = payload.updated_row || {};
                this.applyingPatch = true;

                try {
                    const unitPriceIndex = this.getColumnIndex('unit_price');
                    if (unitPriceIndex >= 0) {
                        this.setCellValue(unitPriceIndex, visualRow, Number(payload.unit_price || 0));
                    }

                    Object.entries(updatedRow).forEach(([month, cellData]) => {
                        const salesQtyIndex = this.getColumnIndex(`${month}__sales_qty`);
                        const stockQtyIndex = this.getColumnIndex(`${month}__stock_qty`);
                        const salesAmountIndex = this.getColumnIndex(`${month}__sales_amount`);

                        if (salesQtyIndex >= 0) {
                            this.setCellValue(salesQtyIndex, visualRow, Number(cellData.sales_qty || 0));
                        }
                        if (stockQtyIndex >= 0) {
                            this.setCellValue(stockQtyIndex, visualRow, Number(cellData.stock_qty || 0));
                        }
                        if (salesAmountIndex >= 0) {
                            this.setCellValue(salesAmountIndex, visualRow, Number(cellData.sales_amount || 0));
                        }
                    });

                    const rowTotalQtyIndex = this.getColumnIndex('row_total_qty');
                    const rowTotalAmountIndex = this.getColumnIndex('row_total_amount');
                    if (rowTotalQtyIndex >= 0) {
                        this.setCellValue(rowTotalQtyIndex, visualRow, Number(payload.row_total_qty || 0));
                    }
                    if (rowTotalAmountIndex >= 0) {
                        this.setCellValue(rowTotalAmountIndex, visualRow, Number(payload.row_total_amount || 0));
                    }
                } finally {
                    this.applyingPatch = false;
                }

                this.stats.totalQty = Number(payload.task_total_qty || 0);
                this.stats.totalAmount = Number(payload.task_total_amount || 0);
            },
            persistCellChange(body, rowMeta, columnMeta, rowIndex, colIndex) {
                const config = this.getConfig();
                this.saving = true;
                fetch(config.updateCellUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': config.csrfToken,
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: body.toString(),
                })
                    .then(async (response) => {
                        const data = await response.json();
                        if (!response.ok || !data.ok) {
                            throw new Error(data.error || '保存失败');
                        }
                        this.applyServerPatch(data, rowMeta);
                    })
                    .catch((error) => {
                        window.alert(error.message || '保存失败');
                        const record = this.getRecords().find((item) => {
                            if (item.sku_id !== rowMeta.sku_id) {
                                return false;
                            }
                            if (columnMeta.month) {
                                return item.target_month === columnMeta.month;
                            }
                            return true;
                        });

                        if (!record) {
                            return;
                        }

                        const rollbackField = columnMeta.metric || columnMeta.field;
                        const fallbackValue = rollbackField === 'unit_price'
                            ? Number(record.unit_price || 0)
                            : Number(record[rollbackField] || 0);
                        this.setCellValue(colIndex, rowIndex, fallbackValue);
                    })
                    .finally(() => {
                        this.saving = false;
                    });
            },
        };
    };
})();
