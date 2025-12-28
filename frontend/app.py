import os
import logging
from flask import Flask, render_template_string, request, jsonify
from google.cloud import bigquery

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
PROJECT_ID = os.environ.get('PROJECT_ID')
if not PROJECT_ID:
    raise ValueError("PROJECT_ID environment variable must be set.")

client = bigquery.Client(project=PROJECT_ID)

# --- HTML TEMPLATE (Banking Style) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>CoreBanking Risk System</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; max-width: 900px; margin: 40px auto; background: #f4f6f9; color: #333; }
        .container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
        h1 { color: #1a73e8; margin-bottom: 5px; }
        .subtitle { color: #666; margin-bottom: 30px; font-size: 0.9em; }
        
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }
        
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 600; color: #444; }
        input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; box-sizing: border-box; }
        
        button { background: #1a73e8; color: white; border: none; padding: 15px 30px; font-size: 16px; font-weight: bold; cursor: pointer; border-radius: 6px; width: 100%; transition: background 0.2s; }
        button:hover { background: #1557b0; }
        
        .action-link { 
            color: #1a73e8; cursor: pointer; font-size: 0.9em; text-decoration: underline; display: inline-block; margin-top: 5px; 
        }
        
        #result-panel { background: #f8f9fa; padding: 25px; border-radius: 8px; border-left: 5px solid #ddd; display: none; }
        .data-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.9em; border-bottom: 1px solid #eee; padding-bottom: 5px; }
        .data-label { color: #666; }
        .data-value { font-weight: bold; }
        
        .status-box { margin-top: 20px; padding: 15px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 1.2em; }
        .approved { background: #e6f4ea; color: #137333; border: 1px solid #ceead6; }
        .rejected { background: #fce8e6; color: #c5221f; border: 1px solid #fad2cf; }
    </style>
</head>
<body>
    <div class="container">
        <h1>CoreBanking Risk Engine</h1>
        <div class="subtitle">Credit Risk Profiler | GCP | BigQuery ML</div>
        
        <div class="grid">
            <div>
                <form id="loanForm">
                    <div class="form-group">
                        <label>Customer ID</label>
                        <input type="text" name="customer_id" id="custId" placeholder="Paste ID here" required>
                        <button type="button" class="action-link" style="background:none; color:#1a73e8; border:none; padding:0; width:auto; text-align:left;" onclick="getRandomId()">
                            🎲 Auto-fill existing customer
                        </button>
                    </div>
                    <div class="form-group">
                        <label>Requested Loan Amount ($)</label>
                        <input type="number" name="loan_amount" value="25000" required>
                    </div>
                    <button type="submit" id="btnSubmit">Process Application</button>
                </form>
            </div>

            <div id="result-panel">
                <h3>Customer Profile Fetched</h3>
                <div id="profile-data"></div>
                
                <h3>Risk Decision</h3>
                <div id="decision-box" class="status-box"></div>
                <div style="margin-top:10px; text-align:center; font-size:0.8em; color:#666;">
                    Confidence: <span id="confidence-score"></span>%
                </div>
            </div>
        </div>
    </div>

    <script>
        async function getRandomId() {
            const btn = document.querySelector('.action-link');
            const originalText = btn.innerText;
            btn.innerText = 'Fetching...';
            try {
                const res = await fetch('/random-customer');
                const data = await res.json();
                if(data.error) {
                    alert('Could not fetch ID: ' + data.error);
                } else {
                    document.getElementById('custId').value = data.customer_id;
                }
            } catch(e) {
                console.error(e);
                alert('Network error fetching random customer');
            } finally {
                btn.innerText = originalText;
            }
        }

        document.getElementById('loanForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('btnSubmit');
            const resultPanel = document.getElementById('result-panel');
            
            btn.disabled = true;
            btn.innerText = 'Analyzing History...';
            
            const formData = new FormData(e.target);
            const payload = Object.fromEntries(formData.entries());

            try {
                const res = await fetch('/process-loan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                
                if (data.error) {
                    alert("Error: " + data.error);
                    return;
                }

                // Render Customer Data
                const profileHtml = `
                    <div class="data-row"><span class="data-label">Income:</span> <span class="data-value">$${data.profile.income}</span></div>
                    <div class="data-row"><span class="data-label">Credit Score:</span> <span class="data-value">${data.profile.credit_score}</span></div>
                    <div class="data-row"><span class="data-label">Current Debt:</span> <span class="data-value">${(data.profile.dti_ratio * 100).toFixed(1)}% DTI</span></div>
                    <div class="data-row"><span class="data-label">History:</span> <span class="data-value">${data.profile.months_employed} months employed</span></div>
                `;
                document.getElementById('profile-data').innerHTML = profileHtml;

                // Render Decision
                const box = document.getElementById('decision-box');
                if (data.prediction === 1) {
                    box.className = 'status-box rejected';
                    box.innerText = 'HIGH RISK - REJECTED';
                } else {
                    box.className = 'status-box approved';
                    box.innerText = 'LOW RISK - APPROVED';
                }
                document.getElementById('confidence-score').innerText = (data.probability * 100).toFixed(2);
                
                resultPanel.style.display = 'block';

            } catch (err) {
                alert("System Error: " + err);
            } finally {
                btn.disabled = false;
                btn.innerText = 'Process Application';
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/random-customer', methods=['GET'])
def get_random_customer():
    """Helper to find a valid ID for the demo"""
    try:
        query = f"SELECT customer_id FROM `{PROJECT_ID}.credit_risk_mvp.credit_history` LIMIT 50"
        job = client.query(query)
        rows = list(job.result())
        import random
        if not rows: return jsonify({'error': 'No data found in table'}), 404
        # Return a random ID from the first 50
        return jsonify({'customer_id': rows[random.randint(0, len(rows)-1)].customer_id})
    except Exception as e:
        logger.error(f"Random fetch failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/process-loan', methods=['POST'])
def process_loan():
    try:
        req = request.json
        # FIX: .strip() removes hidden spaces/newlines from copy-paste
        cust_id = str(req.get('customer_id', '')).strip()
        new_loan = req.get('loan_amount')
        
        # 1. FETCH CUSTOMER PROFILE
        profile_query = f"""
            SELECT * EXCEPT(customer_id, default_risk)
            FROM `{PROJECT_ID}.credit_risk_mvp.credit_history`
            WHERE customer_id = '{cust_id}'
            LIMIT 1
        """
        logger.info(f"Looking up Customer: [{cust_id}]") # Log exact string for debugging
        
        profile_job = client.query(profile_query)
        profile_rows = list(profile_job.result())
        
        if not profile_rows:
            logger.warning(f"Customer {cust_id} NOT FOUND in BigQuery.")
            return jsonify({'error': f"Customer ID '{cust_id}' not found. Try using the Auto-fill button."}), 404
            
        profile = profile_rows[0]
        
        # 2. RUN PREDICTION
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
        logger.info("Running Prediction...")
        pred_job = client.query(predict_query)
        results = list(pred_job.result())
        row = results[0]
        
        # 3. PARSE RESULTS
        probs = row.predicted_label_probs
        confidence = 0.0
        for p in probs:
            label = p['label'] if isinstance(p, dict) else p.label
            prob = p['prob'] if isinstance(p, dict) else p.prob
            if label == row.predicted_label:
                confidence = prob

        return jsonify({
            'profile': {
                'income': profile.income,
                'credit_score': profile.credit_score,
                'dti_ratio': profile.dti_ratio,
                'months_employed': profile.months_employed
            },
            'prediction': int(row.predicted_label),
            'probability': confidence
        })

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
