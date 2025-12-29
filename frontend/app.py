import os
import logging
import json
from flask import Flask, render_template_string, request, jsonify
from google.cloud import bigquery
from google.cloud import storage

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

PROJECT_ID = os.environ.get('PROJECT_ID')
if not PROJECT_ID: raise ValueError("PROJECT_ID environment variable must be set.")

bq_client = bigquery.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)
BUCKET_NAME = f"{PROJECT_ID}-data"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CoreBanking Risk Engine</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 950px; margin: 40px auto; background: #f4f6f9; color: #333; }
        .container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
        h1 { color: #1a73e8; margin-bottom: 5px; }
        .subtitle { color: #666; margin-bottom: 30px; font-size: 0.9em; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 600; color: #444; }
        input, select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; box-sizing: border-box; }
        button { background: #1a73e8; color: white; border: none; padding: 15px 30px; font-size: 16px; font-weight: bold; cursor: pointer; border-radius: 6px; width: 100%; transition: background 0.2s; }
        button:hover { background: #1557b0; }
        
        /* STATUS BOX STYLES */
        .status-box { margin-top: 20px; padding: 15px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 1.2em; }
        .approved { background: #e6f4ea; color: #137333; border: 1px solid #ceead6; }
        .rejected { background: #fce8e6; color: #c5221f; border: 1px solid #fad2cf; }
        .manual-review { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }

        #inbox-section { background: #fff8e1; padding: 20px; border-radius: 6px; border: 1px solid #ffe0b2; margin-bottom: 30px; }
        
        /* NEW: JSON PREVIEW BOX */
        #json-preview { 
            background: #2d2d2d; 
            color: #76ff03; 
            font-family: 'Consolas', monospace; 
            padding: 15px; 
            border-radius: 4px; 
            margin-top: 15px; 
            font-size: 0.85em;
            display: none; /* Hidden by default */
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>CoreBanking Risk Engine</h1>
        <div class="subtitle">Credit Risk Profiler Demo | Real-Time Decisioning + HITL Workflows</div>

        <div id="inbox-section">
            <label style="color: #f57f17;">📂 Digital Inbox (Incoming Applications)</label>
            <div style="display: flex; gap: 10px; align-items: center;">
                <select id="fileSelect" style="flex: 1;">
                    <option value="">Loading pending files...</option>
                </select>
                <button type="button" onclick="loadApplication()" style="width: auto; padding: 10px 25px;">Load JSON</button>
            </div>
            
            <pre id="json-preview"></pre>
        </div>
        
        <div class="grid">
            <div>
                <form id="loanForm">
                    <div class="form-group">
                        <label>Customer ID</label>
                        <input type="text" name="customer_id" id="custId" readonly required style="background: #eee; cursor: not-allowed;">
                        <small style="color:#888;">Locked: Populated from Inbox Source</small>
                    </div>
                    <div class="form-group">
                        <label>Requested Loan Amount ($)</label>
                        <input type="number" name="loan_amount" id="loanAmt" required>
                    </div>
                    <button type="submit" id="btnSubmit">Process Application</button>
                </form>
            </div>

            <div id="result-panel" style="display:none;">
                <h3>Customer Profile (BigQuery)</h3>
                <div id="profile-data"></div>
                
                <h3>Risk Engine Decision</h3>
                <div id="decision-box" class="status-box"></div>
                <div style="margin-top:10px; text-align:center; font-size:0.8em; color:#666;">
                    Model Confidence: <span id="confidence-score"></span>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 1. Fetch File List
        async function fetchInbox() {
            try {
                const res = await fetch('/list-applications');
                const files = await res.json();
                const select = document.getElementById('fileSelect');
                select.innerHTML = '<option value="">-- Select Pending App --</option>';
                files.forEach(f => {
                    const opt = document.createElement('option');
                    opt.value = f;
                    opt.innerText = f;
                    select.appendChild(opt);
                });
            } catch(e) { console.error(e); }
        }
        fetchInbox();

        // 2. Load & Preview JSON
        async function loadApplication() {
            const filename = document.getElementById('fileSelect').value;
            if(!filename) return;
            try {
                const res = await fetch(`/get-application?file=${filename}`);
                const data = await res.json();
                
                // Fill Form
                document.getElementById('custId').value = data.customer_id;
                document.getElementById('loanAmt').value = data.loan_amount;
                
                // NEW: Show JSON Preview
                const preview = document.getElementById('json-preview');
                preview.style.display = 'block';
                preview.innerText = "// Raw JSON Content from GCS Bucket:\\n" + JSON.stringify(data, null, 2);
                
            } catch(e) { alert("Error loading file"); }
        }

        // 3. Process Logic
        document.getElementById('loanForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('btnSubmit');
            btn.innerText = 'Analyzing...';
            
            const formData = new FormData(e.target);
            try {
                const res = await fetch('/process-loan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(Object.fromEntries(formData.entries()))
                });
                const data = await res.json();
                
                const profileDiv = document.getElementById('profile-data');
                const box = document.getElementById('decision-box');
                const confSpan = document.getElementById('confidence-score');

                if (data.prediction === 'HITL') {
                    // HITL / New User
                    box.className = 'status-box manual-review';
                    box.innerText = '⚠️ MANUAL REVIEW REQUIRED';
                    profileDiv.innerHTML = '<div style="color:#856404; font-style:italic; padding:10px; background:#fff3cd; border-radius:4px;">Target Profile not found in Warehouse.<br>Net-New Customer Workflow triggered.</div>';
                    confSpan.innerText = 'N/A';
                } else {
                    // Standard Decision
                    profileDiv.innerHTML = `
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid #eee; padding:5px 0;"><span>Income:</span> <b>$${data.profile.income.toLocaleString()}</b></div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px solid #eee; padding:5px 0;"><span>Credit Score:</span> <b>${data.profile.credit_score}</b></div>
                        <div style="display:flex; justify-content:space-between; padding:5px 0;"><span>History:</span> <b>${data.profile.months_employed} months</b></div>
                    `;
                    
                    if (data.prediction === 1) {
                        box.className = 'status-box rejected';
                        box.innerText = 'REJECTED 🛑';
                    } else {
                        box.className = 'status-box approved';
                        box.innerText = 'APPROVED ✅';
                    }
                    confSpan.innerText = (data.probability * 100).toFixed(2) + '%';
                }
                
                document.getElementById('result-panel').style.display = 'block';
                
            } catch(e) { alert(e); } 
            finally { btn.innerText = 'Process Application'; }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/list-applications', methods=['GET'])
def list_apps():
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix="applications/")
        files = sorted([b.name for b in blobs if b.name.endswith('.json')])
        return jsonify(files) 
    except Exception as e: return jsonify([])

@app.route('/get-application', methods=['GET'])
def get_app():
    filename = request.args.get('file')
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        data = json.loads(blob.download_as_string())
        return jsonify(data)
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/process-loan', methods=['POST'])
def process_loan():
    try:
        req = request.json
        cust_id = str(req.get('customer_id', '')).strip()
        new_loan = req.get('loan_amount')
        
        # 1. FETCH PROFILE
        profile_query = f"""
            SELECT * EXCEPT(customer_id, default_risk)
            FROM `{PROJECT_ID}.credit_risk_mvp.credit_history`
            WHERE customer_id = '{cust_id}' LIMIT 1
        """
        job = bq_client.query(profile_query)
        rows = list(job.result())
        
        # HITL CHECK
        if not rows:
            return jsonify({
                'prediction': 'HITL',
                'probability': 0.0,
                'message': 'Net New Customer'
            })
            
        profile = rows[0]
        
        # 2. RUN ML PREDICTION
        predict_query = f"""
            SELECT * FROM ML.PREDICT(
                MODEL `{PROJECT_ID}.credit_risk_mvp.risk_score_model`,
                (SELECT 
                    {profile.age} AS age,
                    {profile.income} AS income,
                    {new_loan} AS loan_amount,
                    {profile.credit_score} AS credit_score,
                    {profile.months_employed} AS months_employed,
                    {profile.num_credit_lines} AS num_credit_lines,
                    {profile.interest_rate} AS interest_rate,
                    {profile.dti_ratio} AS dti_ratio
                )
            )
        """
        pred_row = list(bq_client.query(predict_query).result())[0]
        
        probs = pred_row.predicted_label_probs
        confidence = 0.0
        for p in probs:
            label = p['label'] if isinstance(p, dict) else p.label
            prob = p['prob'] if isinstance(p, dict) else p.prob
            if label == pred_row.predicted_label:
                confidence = prob

        return jsonify({
            'profile': {'income': profile.income, 'credit_score': profile.credit_score, 'months_employed': profile.months_employed},
            'prediction': int(pred_row.predicted_label),
            'probability': confidence
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))