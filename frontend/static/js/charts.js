
let chartApprovals = null;
let chartRisk = null;
let chartTrends = null;

function formatISTDate(dateInput) {
    if (!dateInput) return "";
    try {
        const d = new Date(dateInput);
        if (isNaN(d.getTime())) return dateInput;
        
        const options = {
            timeZone: 'Asia/Kolkata',
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        };
        const formatter = new Intl.DateTimeFormat('en-GB', options);
        let formatted = formatter.format(d);
        return formatted.replace(/am$/i, 'AM').replace(/pm$/i, 'PM');
    } catch (e) {
        console.error("Error formatting IST date:", e);
        return dateInput;
    }
}

function getISTDayString(dateInput) {
    if (!dateInput) return "";
    try {
        const d = new Date(dateInput);
        if (isNaN(d.getTime())) return "";
        
        const formatter = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'Asia/Kolkata',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
        return formatter.format(d);
    } catch (e) {
        console.error("Error getting IST day string:", e);
        return "";
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;

    if (path.startsWith('/dashboard') || path === '/dashboard.html') {
        initDashboard();
    } else if (path.startsWith('/history') || path === '/history.html') {
        initHistory();
    }
});


async function initDashboard() {
    console.log("Initializing Analytics Dashboard...");
    
    const refreshBtn = document.getElementById('btn-refresh-dashboard');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => fetchAndRenderDashboardData());
    }
    
    await fetchAndRenderDashboardData();
}

async function fetchAndRenderDashboardData() {
    LoadingOverlay.show("Loading dashboard analytics data...");
    
    try {
        const response = await fetch('/api/history?per_page=1000');
        const data = await response.json();
        
        if (response.ok && data.success) {
            const records = data.data.records;
            updateDashboardMetrics(records);
            renderDashboardCharts(records);
            populateRecentPredictions(records.slice(0, 5));
        } else {
            showNotification("Failed to fetch history analytics: " + data.message, "error");
        }
    } catch (err) {
        console.error(err);
        showNotification("Failed to connect to backend server.", "error");
    } finally {
        LoadingOverlay.hide();
    }
}

function updateDashboardMetrics(records) {
    const total = records.length;
    const approved = records.filter(r => r.prediction_result === 1).length;
    const rejected = total - approved;
    const approvalRate = total > 0 ? (approved / total) * 100 : 0;
    
    let totalConfidence = 0;
    records.forEach(r => {
        totalConfidence += r.confidence_score;
    });
    const avgConfidence = total > 0 ? (totalConfidence / total) * 100 : 0;
    
    document.getElementById('stat-total').textContent = total;
    document.getElementById('stat-approved').textContent = approved;
    document.getElementById('stat-rejected').textContent = rejected;
    document.getElementById('stat-approval-rate').textContent = `${approvalRate.toFixed(1)}%`;
    document.getElementById('stat-avg-confidence').textContent = `${avgConfidence.toFixed(1)}%`;
}

function populateRecentPredictions(recentRecords) {
    const tbody = document.getElementById('recent-predictions-rows');
    if (!tbody) return;
    
    tbody.innerHTML = "";
    
    if (recentRecords.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No predictions logged yet.</td></tr>`;
        return;
    }
    
    recentRecords.forEach(r => {
        const tr = document.createElement('tr');
        const formattedDate = formatISTDate(r.created_at);
        const appVal = r.applicant_id || `ID-${r.id}`;
        
        const badgeClass = r.prediction_result === 1 ? 'badge-success' : 'badge-danger';
        const badgeLabel = r.prediction_result === 1 ? 'Approved' : 'Rejected';
        
        tr.innerHTML = `
            <td><strong>${appVal}</strong></td>
            <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
            <td>${(r.approval_probability * 100).toFixed(1)}%</td>
            <td>${(r.confidence_score * 100).toFixed(1)}%</td>
            <td>${formattedDate}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderDashboardCharts(records) {
    const approved = records.filter(r => r.prediction_result === 1).length;
    const rejected = records.length - approved;
    
    let lowRisk = 0, medRisk = 0, highRisk = 0;
    records.forEach(r => {
        const prob = r.approval_probability;
        if (prob >= 0.8) lowRisk++;
        else if (prob >= 0.5) medRisk++;
        else highRisk++;
    });

    const dailyVolume = {};
    records.forEach(r => {
        const day = getISTDayString(r.created_at);
        dailyVolume[day] = (dailyVolume[day] || 0) + 1;
    });
    
    const sortedDates = Object.keys(dailyVolume).sort();
    const sortedVolumes = sortedDates.map(d => dailyVolume[d]);

    if (chartApprovals) chartApprovals.destroy();
    if (chartRisk) chartRisk.destroy();
    if (chartTrends) chartTrends.destroy();

    const baseChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: '#f5f5f7', font: { family: 'Inter', size: 11 } }
            }
        }
    };

    const ctxApp = document.getElementById('chart-approvals');
    if (ctxApp) {
        chartApprovals = new Chart(ctxApp, {
            type: 'pie',
            data: {
                labels: ['Approved', 'Rejected'],
                datasets: [{
                    data: [approved, rejected],
                    backgroundColor: ['#10b981', '#ef4444'],
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1
                }]
            },
            options: baseChartOptions
        });
    }

    const ctxRisk = document.getElementById('chart-risk');
    if (ctxRisk) {
        chartRisk = new Chart(ctxRisk, {
            type: 'doughnut',
            data: {
                labels: ['Low Risk', 'Medium Risk', 'High Risk'],
                datasets: [{
                    data: [lowRisk, medRisk, highRisk],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                    borderColor: 'rgba(255,255,255,0.08)',
                    borderWidth: 1
                }]
            },
            options: baseChartOptions
        });
    }

    const ctxTrend = document.getElementById('chart-trends');
    if (ctxTrend) {
        chartTrends = new Chart(ctxTrend, {
            type: 'line',
            data: {
                labels: sortedDates.length > 0 ? sortedDates : ['No Data'],
                datasets: [{
                    label: 'Applications Evaluated',
                    data: sortedVolumes.length > 0 ? sortedVolumes : [0],
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99,102,241,0.1)',
                    fill: true,
                    tension: 0.35,
                    borderWidth: 2
                }]
            },
            options: {
                ...baseChartOptions,
                scales: {
                    x: {
                        grid: { color: '#3f3f4f' },
                        ticks: { color: '#f5f5f7', font: { family: 'Inter' } }
                    },
                    y: {
                        grid: { color: '#3f3f4f' },
                        ticks: { color: '#f5f5f7', font: { family: 'Inter' }, stepSize: 1 }
                    }
                }
            }
        });
    }
}


let historyCurrentPage = 1;
const historyPerPage = 10;

function initHistory() {
    console.log("Initializing History Logs Table...");
    
    document.getElementById('search-applicant-id').addEventListener('input', debounce(() => {
        historyCurrentPage = 1;
        fetchAndRenderHistory();
    }, 400));
    
    document.getElementById('filter-status').addEventListener('change', () => {
        historyCurrentPage = 1;
        fetchAndRenderHistory();
    });
    
    document.getElementById('filter-risk').addEventListener('change', () => {
        historyCurrentPage = 1;
        fetchAndRenderHistory();
    });
    
    document.getElementById('sort-order').addEventListener('change', () => {
        historyCurrentPage = 1;
        fetchAndRenderHistory();
    });
    
    document.getElementById('btn-refresh-history').addEventListener('click', () => {
        fetchAndRenderHistory();
    });

    document.getElementById('btn-page-prev').addEventListener('click', () => {
        if (historyCurrentPage > 1) {
            historyCurrentPage--;
            fetchAndRenderHistory();
        }
    });

    document.getElementById('btn-page-next').addEventListener('click', () => {
        historyCurrentPage++;
        fetchAndRenderHistory();
    });

    const modal = document.getElementById('details-modal');
    document.getElementById('btn-close-modal').addEventListener('click', () => {
        modal.classList.remove('show');
        modal.setAttribute('aria-hidden', 'true');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
            modal.setAttribute('aria-hidden', 'true');
        }
    });

    fetchAndRenderHistory();
}

async function fetchAndRenderHistory() {
    const searchVal = document.getElementById('search-applicant-id').value.trim();
    const statusVal = document.getElementById('filter-status').value;
    const riskVal = document.getElementById('filter-risk').value;
    const sortOrder = document.getElementById('sort-order').value;
    
    let url = `/api/history?page=${historyCurrentPage}&per_page=${historyPerPage}&sort_order=${sortOrder}`;
    
    if (searchVal) url += `&applicant_id=${encodeURIComponent(searchVal)}`;
    if (statusVal !== "") url += `&prediction_result=${statusVal}`;
    if (riskVal) url += `&risk_level=${riskVal}`;
    
    LoadingOverlay.show("Fetching database history...");
    
    try {
        const response = await fetch(url);
        const result = await response.json();
        
        if (response.ok && result.success) {
            renderHistoryRows(result.data.records);
            renderPaginationControls(result.data);
        } else {
            showNotification(result.message || "Failed to load log history.", "error");
        }
    } catch (err) {
        console.error(err);
        showNotification("Error connecting to server database.", "error");
    } finally {
        LoadingOverlay.hide();
    }
}

function renderHistoryRows(records) {
    const tbody = document.getElementById('history-rows-container');
    const emptyState = document.getElementById('history-empty-state');
    
    tbody.innerHTML = "";
    
    if (records.length === 0) {
        emptyState.style.display = "block";
        document.getElementById('pagination-container').style.display = "none";
        return;
    }
    
    emptyState.style.display = "none";
    document.getElementById('pagination-container').style.display = "flex";
    
    records.forEach(r => {
        const tr = document.createElement('tr');
        const formattedDate = formatISTDate(r.created_at);
        const appVal = r.applicant_id || `ID-${r.id}`;
        
        const badgeClass = r.prediction_result === 1 ? 'badge-success' : 'badge-danger';
        const badgeLabel = r.prediction_result === 1 ? 'Approved' : 'Rejected';
        
        let riskClass = 'badge-success';
        let riskText = 'Low';
        if (r.approval_probability < 0.5) {
            riskClass = 'badge-danger';
            riskText = 'High';
        } else if (r.approval_probability < 0.8) {
            riskClass = 'badge-warning';
            riskText = 'Medium';
        }

        tr.innerHTML = `
            <td>#${r.id}</td>
            <td><strong>${appVal}</strong></td>
            <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
            <td>${(r.approval_probability * 100).toFixed(1)}%</td>
            <td>${(r.confidence_score * 100).toFixed(1)}%</td>
            <td><span class="badge ${riskClass}">${riskText} Risk</span></td>
            <td>${formattedDate}</td>
            <td class="text-center">
                <button class="btn btn-secondary btn-sm" onclick="showRecordDetails(${r.id})">
                    <i class="fa-solid fa-eye"></i> Details
                </button>
                <button class="btn btn-outline btn-sm" onclick="confirmDeleteRecord(${r.id})" style="border-color: var(--danger); color: var(--danger); margin-left: 6px;">
                    <i class="fa-solid fa-trash-can"></i> Delete
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderPaginationControls(data) {
    const summary = document.getElementById('pagination-summary');
    const pageContainer = document.getElementById('page-numbers-container');
    
    const totalRecords = data.total_records;
    const totalPages = data.total_pages;
    const page = data.current_page;
    
    const startIdx = totalRecords > 0 ? (page - 1) * historyPerPage + 1 : 0;
    const endIdx = Math.min(page * historyPerPage, totalRecords);
    
    summary.textContent = `Showing ${startIdx} to ${endIdx} of ${totalRecords} entries`;
    
    document.getElementById('btn-page-prev').disabled = (page <= 1);
    document.getElementById('btn-page-next').disabled = (page >= totalPages);
    
    pageContainer.innerHTML = "";
    for (let i = 1; i <= totalPages; i++) {
        const btn = document.createElement('button');
        btn.className = `btn btn-secondary btn-sm page-number-btn ${i === page ? 'active' : ''}`;
        btn.textContent = i;
        btn.addEventListener('click', () => {
            historyCurrentPage = i;
            fetchAndRenderHistory();
        });
        pageContainer.appendChild(btn);
    }
}


async function showRecordDetails(id) {
    const modal = document.getElementById('details-modal');
    const content = document.getElementById('modal-content-body');
    content.innerHTML = `<p class="text-center">Loading record details...</p>`;
    modal.classList.add('show');
    modal.setAttribute('aria-hidden', 'false');

    try {
        const response = await fetch(`/api/history/${id}`);
        const result = await response.json();
        
        if (response.ok && result.success) {
            const rec = result.data;
            const input = rec.customer_input;
            
            content.innerHTML = `
                <div class="modal-detail-grid grid">
                    <div style="grid-column: span 2; border-bottom: 1px solid var(--border-glass); padding-bottom: 12px; margin-bottom: 12px;">
                        <h4 class="detail-section-title">Evaluation Summary</h4>
                        <p class="summary-item"><strong>Status:</strong> ${rec.prediction_result === 1 ? '<span class="badge badge-success">Approved</span>' : '<span class="badge badge-danger">Rejected</span>'}</p>
                        <p class="summary-item" style="margin-top: 8px;"><strong>Reasoning:</strong> ${rec.explanation}</p>
                    </div>

                    <div>
                        <h4 class="detail-section-title">Demographics</h4>
                        <table class="modal-data-table">
                            <tr><td><strong>Gender:</strong></td><td>${input.CODE_GENDER === 'M' ? 'Male' : 'Female'}</td></tr>
                            <tr><td><strong>Age:</strong></td><td>${input.AGE} Years</td></tr>
                            <tr><td><strong>Education:</strong></td><td>${input.NAME_EDUCATION_TYPE}</td></tr>
                            <tr><td><strong>Marital:</strong></td><td>${input.NAME_FAMILY_STATUS}</td></tr>
                            <tr><td><strong>Family Size:</strong></td><td>${input.CNT_FAM_MEMBERS}</td></tr>
                            <tr><td><strong>Children:</strong></td><td>${input.CNT_CHILDREN}</td></tr>
                        </table>
                    </div>

                    <div>
                        <h4 class="detail-section-title">Financial & Work</h4>
                        <table class="modal-data-table">
                            <tr><td><strong>Annual Income:</strong></td><td>$${Number(input.AMT_INCOME_TOTAL).toLocaleString()}</td></tr>
                            <tr><td><strong>Car Owner:</strong></td><td>${input.FLAG_OWN_CAR === 'Y' ? 'Yes' : 'No'}</td></tr>
                            <tr><td><strong>Property:</strong></td><td>${input.FLAG_OWN_REALTY === 'Y' ? 'Yes' : 'No'}</td></tr>
                            <tr><td><strong>Housing:</strong></td><td>${input.NAME_HOUSING_TYPE}</td></tr>
                            <tr><td><strong>Work Tenure:</strong></td><td>${input.EMPLOYED_YEARS} Years</td></tr>
                            <tr><td><strong>Occupation:</strong></td><td>${input.OCCUPATION_TYPE}</td></tr>
                        </table>
                    </div>
                </div>
            `;
        } else {
            content.innerHTML = `<p class="text-center text-muted" style="color: var(--danger);">Failed to retrieve record parameters: ${result.message}</p>`;
        }
    } catch (err) {
        content.innerHTML = `<p class="text-center text-muted" style="color: var(--danger);">Failed to connect to API server.</p>`;
    }
}

async function confirmDeleteRecord(id) {
    const confirmation = confirm("Are you sure you want to permanently delete this prediction record from the logs?");
    if (!confirmation) return;
    
    LoadingOverlay.show("Deleting record from database...");
    
    try {
        const response = await fetch(`/api/history/${id}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (response.ok && result.success) {
            showNotification(`Record ID ${id} deleted successfully.`, "success");
            
            const rowCount = document.querySelectorAll('#history-rows-container tr').length;
            if (rowCount <= 1 && historyCurrentPage > 1) {
                historyCurrentPage--;
            }
            
            fetchAndRenderHistory();
        } else {
            showNotification("Failed to delete record: " + result.message, "error");
        }
    } catch (err) {
        console.error(err);
        showNotification("Failed to connect to backend server.", "error");
    } finally {
        LoadingOverlay.hide();
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
