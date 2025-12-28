-- =======================================================
-- 1. DATA PREPARATION
-- =======================================================

CREATE OR REPLACE VIEW `PROJECT_ID.credit_risk_mvp.training_data` AS
SELECT
  age,
  income,
  loan_amount,
  credit_score,
  months_employed,
  num_credit_lines,
  interest_rate,
  dti_ratio,
  default_risk as label -- The target for the model
FROM `PROJECT_ID.credit_risk_mvp.credit_history`;

-- =======================================================
-- 2. MODEL TRAINING
-- =======================================================
CREATE OR REPLACE MODEL `PROJECT_ID.credit_risk_mvp.risk_score_model`
OPTIONS(
  model_type='LOGISTIC_REG',
  input_label_cols=['label'],
  enable_global_explain=TRUE
) AS
SELECT * FROM `PROJECT_ID.credit_risk_mvp.training_data`;
