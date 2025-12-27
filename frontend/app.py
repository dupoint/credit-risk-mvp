import streamlit as st
from google.cloud import bigquery
import os

# Page Config
st.set_page_config(page_title="Credit Risk Portal", page_icon="🏦")

# Initialize BQ Client
# (Cloud Run injects credentials automatically, so no keys needed!)
# DYNAMIC PROJECT DETECTION:
# When running on Cloud Run, the 'GOOGLE_CLOUD_PROJECT' env var is set automatically.
# When running locally, you can set this env var or fallback to your default gcloud config.
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "credit-score-mvp") 
client = bigquery.Client(project=project_id)

st.title("🏦 Risk Decision Engine")
st.markdown("---")

# --- LEFT COLUMN: INPUTS ---
col1, col2 = st.columns(2)

with col1:
    st.header("1. Applicant Details")
    customer_id = st.text_input("Customer ID", value="12345-abc")
    # In a real app, these would come from the form, but let's allow overrides
    income = st.number_input("Annual Income ($)", value=80000, step=1000)
    loan_amount = st.number_input("Requested Loan ($)", value=20000, step=1000)

# --- ACTION: FETCH HISTORY ---
if customer_id:
    # Look up the "Offline" features (History)
    # Uses f-string to inject the dynamic project_id
    query = f"""
        SELECT credit_score, existing_debt, missed_payments_last_12m
        FROM `{project_id}.credit_risk_mvp.credit_history`
        WHERE customer_id = '{customer_id}'
        LIMIT 1
    """
    
    try:
        df = client.query(query).to_dataframe()
        
        if not df.empty:
            history = df.iloc[0]
            with col2:
                st.header("2. Risk Profile (Found)")
                st.info(f"Credit Score: **{history['credit_score']}**")
                st.info(f"Existing Debt: **${history['existing_debt']:,}**")
                st.info(f"Missed Payments: **{history['missed_payments_last_12m']}**")
        else:
            with col2:
                st.warning("Customer ID not found in history.")
                history = None
    except Exception as e:
        st.error(f"Database Error: {e}")
        history = None

st.markdown("---")

# --- ACTION: PREDICT ---
if st.button("🚀 Analyze Risk", type="primary"):
    if history is not None:
        # Construct the Prediction Query
        # We pass the Form Inputs + The Historical Data to the Model
        # Uses f-string to inject the dynamic project_id
        predict_sql = f"""
        SELECT *
        FROM ML.PREDICT(
          MODEL `{project_id}.credit_risk_mvp.risk_score_model`,
          (
            SELECT 
              {history['credit_score']} as credit_score,
              {history['missed_payments_last_12m']} as missed_payments_last_12m,
              {history['existing_debt']} as existing_debt,
              {income} as income,
              {loan_amount} as loan_amount
          )
        )
        """
        
        pred_df = client.query(predict_sql).to_dataframe()
        prediction = pred_df.iloc[0]
        
        # 1 = Default (Risky), 0 = Pay (Safe)
        is_risky = prediction['predicted_is_default'] == 1
        probs = prediction['predicted_is_default_probs']
        
        # Extract confidence score
        confidence = [p['prob'] for p in probs if p['label'] == prediction['predicted_is_default']][0]

        st.header("3. Decision")
        if is_risky:
            st.error(f"❌ LOAN DENIED (Risk Probability: {confidence:.1%})")
        else:
            st.success(f"✅ LOAN APPROVED (Confidence: {confidence:.1%})")
            
        # Explainability (Simple Rule Check)
        dti = (history['existing_debt'] + loan_amount) / income
        st.caption(f"Calculated Debt-to-Income Ratio: {dti:.2%}")
        if dti > 0.6:
            st.caption("⚠️ Warning: High DTI detected.")
            
    else:
        st.error("Cannot predict without valid Customer History.")