-- 1. Create External Table (Points to GCS)
-- Note: Replace @BUCKET_NAME with the actual bucket at runtime
CREATE OR REPLACE EXTERNAL TABLE `credit_risk_mvp.raw_docai_output`
(
  text STRING,
  confidence FLOAT64
)
OPTIONS (
  format = 'JSON',
  uris = ['gs://@BUCKET_NAME/batch_results/*.json'],
  ignore_unknown_values = TRUE
);

-- 2. Create Clean View
CREATE OR REPLACE VIEW `credit_risk_mvp.loan_applications_clean` AS
SELECT
  REGEXP_EXTRACT(text, r'Applicant ID: ([a-zA-Z0-9\-]+)') as customer_id,
  CAST(REGEXP_EXTRACT(text, r'Declared Annual Income: \$(\d+)') AS INT64) as income,
  CAST(REGEXP_EXTRACT(text, r'Requested Loan Amount: \$(\d+)') AS INT64) as loan_amount,
  REGEXP_EXTRACT(text, r'Application Date: ([\d\-]+)') as app_date
FROM `credit_risk_mvp.raw_docai_output`
WHERE text IS NOT NULL;

-- 3. Create Training Data View
CREATE OR REPLACE VIEW `credit_risk_mvp.training_data` AS
SELECT
    t1.customer_id,
    t1.credit_score,
    t1.missed_payments_last_12m,
    t1.existing_debt,
    t2.income,
    t2.loan_amount,
    CASE 
      WHEN (t1.existing_debt + t2.loan_amount) / NULLIF(t2.income, 0) > 0.6 THEN 1
      WHEN t1.credit_score < 500 THEN 1
      ELSE 0 
    END as is_default
FROM `credit_risk_mvp.credit_history` t1 
JOIN `credit_risk_mvp.loan_applications_clean` t2 
ON t1.customer_id = t2.customer_id;

-- 4. Train the Model
CREATE OR REPLACE MODEL `credit_risk_mvp.risk_score_model`
OPTIONS(
  model_type='LOGISTIC_REG',
  input_label_cols=['is_default'],
  enable_global_explain=TRUE
) AS
SELECT * EXCEPT(customer_id) FROM `credit_risk_mvp.training_data`;
