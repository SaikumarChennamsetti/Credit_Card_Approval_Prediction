
document.addEventListener('DOMContentLoaded', () => {
    let currentStep = 1;
    
    const form = document.getElementById('predict-form');
    const sections = document.querySelectorAll('.form-section');
    const stepIndicators = document.querySelectorAll('.progress-step');
    const btnReset = document.getElementById('btn-reset');
    const resultSection = document.getElementById('result-section');
    
    
    function showStep(stepNum) {
        sections.forEach(sec => sec.classList.remove('active'));
        stepIndicators.forEach(ind => ind.classList.remove('active'));
        
        document.getElementById(`section-${stepNum}`).classList.add('active');
        
        for (let i = 1; i <= 4; i++) {
            const ind = document.getElementById(`step-indicator-${i}`);
            if (i <= stepNum) {
                ind.classList.add('active');
            }
        }
        currentStep = stepNum;
        
        if (stepNum === 4) {
            compileReviewSummary();
        }
        
        form.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    document.querySelectorAll('.btn-next').forEach(btn => {
        btn.addEventListener('click', () => {
            const nextStepId = parseInt(btn.getAttribute('data-next'));
            if (validateStep(currentStep)) {
                showStep(nextStepId);
            } else {
                showNotification("Please resolve validation errors in form fields.", "error");
            }
        });
    });

    document.querySelectorAll('.btn-prev').forEach(btn => {
        btn.addEventListener('click', () => {
            const prevStepId = parseInt(btn.getAttribute('data-prev'));
            showStep(prevStepId);
        });
    });

    function compileReviewSummary() {
        document.getElementById('sum-gender').textContent = getSelectedText('CODE_GENDER');
        document.getElementById('sum-age').textContent = document.getElementById('AGE').value;
        document.getElementById('sum-education').textContent = getSelectedText('NAME_EDUCATION_TYPE');
        document.getElementById('sum-marital').textContent = getSelectedText('NAME_FAMILY_STATUS');
        document.getElementById('sum-income').textContent = Number(document.getElementById('AMT_INCOME_TOTAL').value).toLocaleString();
        document.getElementById('sum-employment').textContent = document.getElementById('EMPLOYED_YEARS').value;
        document.getElementById('sum-occupation').textContent = getSelectedText('OCCUPATION_TYPE');
        document.getElementById('sum-housing').textContent = getSelectedText('NAME_HOUSING_TYPE');
        document.getElementById('sum-car').textContent = getSelectedText('FLAG_OWN_CAR');
        document.getElementById('sum-family').textContent = document.getElementById('CNT_FAM_MEMBERS').value;
    }

    function getSelectedText(elementId) {
        const el = document.getElementById(elementId);
        if (el && el.options && el.selectedIndex >= 0) {
            return el.options[el.selectedIndex].text;
        }
        return '-';
    }

    
    function validateStep(stepNum) {
        let isValid = true;
        const currentSec = document.getElementById(`section-${stepNum}`);
        const inputs = currentSec.querySelectorAll('input[required], select[required]');
        
        inputs.forEach(input => {
            if (!validateInputField(input)) {
                isValid = false;
            }
        });
        
        if (stepNum === 1 && isValid) {
            const children = parseInt(document.getElementById('CNT_CHILDREN').value);
            const famMembers = parseInt(document.getElementById('CNT_FAM_MEMBERS').value);
            if (children >= famMembers) {
                const errorEl = document.getElementById('error-CNT_FAM_MEMBERS');
                errorEl.textContent = "Family size must be greater than number of children.";
                document.getElementById('CNT_FAM_MEMBERS').classList.add('input-error');
                isValid = false;
            }
        }
        
        return isValid;
    }

    function validateInputField(input) {
        const fieldId = input.id;
        const errorEl = document.getElementById(`error-${fieldId}`);
        if (!errorEl) return true;
        
        input.classList.remove('input-error');
        errorEl.textContent = "";
        
        const value = input.value.trim();
        
        if (value === "") {
            errorEl.textContent = "This field is required.";
            input.classList.add('input-error');
            return false;
        }
        
        if (input.type === 'number') {
            const num = parseFloat(value);
            const min = parseFloat(input.getAttribute('min'));
            const max = parseFloat(input.getAttribute('max'));
            
            if (isNaN(num)) {
                errorEl.textContent = "Please enter a valid numeric number.";
                input.classList.add('input-error');
                return false;
            }
            if (min !== null && num < min) {
                errorEl.textContent = `Value must be at least ${min}.`;
                input.classList.add('input-error');
                return false;
            }
            if (max !== null && num > max) {
                errorEl.textContent = `Value cannot exceed ${max}.`;
                input.classList.add('input-error');
                return false;
            }
        }
        
        return true;
    }

    document.querySelectorAll('input, select').forEach(el => {
        el.addEventListener('change', () => validateInputField(el));
        el.addEventListener('input', () => validateInputField(el));
    });

    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!validateStep(4)) {
            showNotification("Application review checks failed.", "error");
            return;
        }
        
        const payload = {
            applicant_id: document.getElementById('applicant_id').value.trim() || null,
            CODE_GENDER: document.getElementById('CODE_GENDER').value,
            AGE: parseFloat(document.getElementById('AGE').value),
            NAME_FAMILY_STATUS: document.getElementById('NAME_FAMILY_STATUS').value,
            CNT_CHILDREN: parseInt(document.getElementById('CNT_CHILDREN').value),
            CNT_FAM_MEMBERS: parseInt(document.getElementById('CNT_FAM_MEMBERS').value),
            NAME_EDUCATION_TYPE: document.getElementById('NAME_EDUCATION_TYPE').value,
            NAME_INCOME_TYPE: document.getElementById('NAME_INCOME_TYPE').value,
            EMPLOYED_YEARS: parseFloat(document.getElementById('EMPLOYED_YEARS').value),
            OCCUPATION_TYPE: document.getElementById('OCCUPATION_TYPE').value,
            AMT_INCOME_TOTAL: parseFloat(document.getElementById('AMT_INCOME_TOTAL').value),
            FLAG_OWN_CAR: document.getElementById('FLAG_OWN_CAR').value,
            FLAG_OWN_REALTY: document.getElementById('FLAG_OWN_REALTY').value,
            NAME_HOUSING_TYPE: document.getElementById('NAME_HOUSING_TYPE').value
        };
        
        LoadingOverlay.show("Analyzing profile and running credit models...");
        document.getElementById('btn-submit').disabled = true;
        
        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                showNotification("Inference completed successfully. Rationale calculated.", "success");
                renderPredictionResult(result.data);
            } else {
                const errMsg = result.message || "Model calculation failed.";
                showNotification(errMsg, "error");
                if (result.data && result.data.validation_details) {
                    highlightServerValidationErrors(result.data.validation_details);
                }
            }
        } catch (err) {
            console.error(err);
            showNotification("Failed to connect to API server. Check connection.", "error");
        } finally {
            LoadingOverlay.hide();
            document.getElementById('btn-submit').disabled = false;
        }
    });

    function highlightServerValidationErrors(details) {
        showNotification("Server rejected request parameters format.", "error");
        console.error("Validation issues:", details);
    }

    
    function renderPredictionResult(data) {
        const isApproved = data.approved;
        const resultCard = document.getElementById('result-card');
        const badge = document.getElementById('result-status-badge');
        const statusText = document.getElementById('result-status-text');
        
        resultCard.className = "card result-card";
        badge.className = "badge";
        
        if (isApproved) {
            resultCard.classList.add('status-approved');
            badge.classList.add('badge-success');
            badge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Approved';
            statusText.textContent = "Congratulations! Card Application Approved";
        } else {
            resultCard.classList.add('status-rejected');
            badge.classList.add('badge-danger');
            badge.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Rejected';
            statusText.textContent = "Application Declined by AI Scoring Engine";
        }
        
        document.getElementById('res-probability').textContent = `${(data.probability * 100).toFixed(1)}%`;
        document.getElementById('res-confidence').textContent = `${(data.confidence_score * 100).toFixed(1)}%`;
        document.getElementById('res-risk').textContent = `${data.risk_level} Risk`;
        document.getElementById('res-explanation').textContent = data.explanation;
        document.getElementById('res-record-id').textContent = data.record_id || 'N/A';
        
        const riskValEl = document.getElementById('res-risk');
        riskValEl.className = "metric-value";
        if (data.risk_level === 'Low') riskValEl.classList.add('color-success');
        else if (data.risk_level === 'Medium') riskValEl.classList.add('color-warning');
        else riskValEl.classList.add('color-danger');
        
        const suggestionsBox = document.getElementById('suggestions-box');
        const listContainer = document.getElementById('res-suggestions');
        listContainer.innerHTML = "";
        
        if (data.suggestions && data.suggestions.length > 0) {
            suggestionsBox.style.display = "block";
            data.suggestions.forEach(sug => {
                const li = document.createElement('li');
                li.innerHTML = `<i class="fa-solid fa-arrow-right-long text-muted"></i> <span>${sug}</span>`;
                listContainer.appendChild(li);
            });
        } else {
            suggestionsBox.style.display = "none";
        }
        
        resultSection.style.display = "block";
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        
        setupCopyButton(data);
    }

    function setupCopyButton(data) {
        const copyBtn = document.getElementById('btn-copy-summary');
        copyBtn.onclick = () => {
            const summaryText = `[CredAI Prediction Result]\n` +
                `Status: ${data.approved ? 'APPROVED' : 'REJECTED'}\n` +
                `Probability: ${(data.probability * 100).toFixed(1)}%\n` +
                `Risk Level: ${data.risk_level}\n` +
                `Rationale: ${data.explanation}\n` +
                `Record ID: ${data.record_id || 'N/A'}`;
                
            navigator.clipboard.writeText(summaryText).then(() => {
                showNotification("Summary copied to clipboard!", "success");
            }).catch(() => {
                showNotification("Copy failed. Please manually select text.", "error");
            });
        };
    }

    
    btnReset.addEventListener('click', () => {
        form.reset();
        document.querySelectorAll('input, select').forEach(el => {
            el.classList.remove('input-error');
            const err = document.getElementById(`error-${el.id}`);
            if (err) err.textContent = "";
        });
        resultSection.style.display = "none";
        showStep(1);
        showNotification("Application inputs cleared successfully.", "info");
    });
});
