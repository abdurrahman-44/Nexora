# NEXORA ERP — Nexora Intelligence (AI & ML Engine Documentation)

## 1. Overview

The **Nexora Intelligence Engine** provides four production-minded, transparent, and auditable AI capabilities backed by real historical time-series and transactional records stored in PostgreSQL:

1. **Inventory Demand Forecasting** (`/api/v1/ai/forecast/inventory`)
2. **Sales & Revenue Forecasting** (`/api/v1/ai/forecast/sales`)
3. **Business Anomaly Detection** (`/api/v1/ai/anomalies/analyze`)
4. **Nexora AI Business Copilot** (`/api/v1/ai/copilot/chat`)

---

## 2. Feature 1: Inventory Demand Forecasting

### Inputs
- Historical daily/weekly product sales (`invoice_items`, `sales_order_items`) and `stock_movements` (`ISSUE`).
- Product attributes: `category_id`, `lead_time_days`, `reorder_level`, current `quantity_on_hand`.

### Model Pipeline
1. **Moving Average Baseline (`MOVING_AVERAGE`)**: 7-day / 14-day rolling window estimator.
2. **Seasonal Naive Baseline (`SEASONAL_NAIVE`)**: Weekly/monthly seasonal lag estimator with trend drift.
3. **Gradient Boosted Regressor (`XGBOOST` / `GradientBoostingRegressor`)**: Lag features (`lag_1`, `lag_7`, `lag_14`, `lag_30`), rolling mean/std features, calendar/seasonality features, and product velocity.
4. **Automatic Model Selection & Insufficient Data Guard**:
   - When a product has fewer than 14 historical data points, the engine explicitly marks confidence as `LOW_DATA_BASELINE` and uses conservative moving-average estimation rather than claiming high-precision ML accuracy.

### Evaluation Metrics (Backtested on Holdout Window)
- **MAE (Mean Absolute Error)**: $\text{MAE} = \frac{1}{n}\sum_{i=1}^{n} |y_i - \hat{y}_i|$
- **RMSE (Root Mean Squared Error)**: $\text{RMSE} = \sqrt{\frac{1}{n}\sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$
- **WAPE (Weighted Absolute Percentage Error)**: $\text{WAPE} = \frac{\sum_{i=1}^{n} |y_i - \hat{y}_i|}{\sum_{i=1}^{n} |y_i|} \times 100\%$

### Outputs
- **7-Day, 30-Day, and 90-Day Forecast** with 90% prediction intervals (`lower_bound`, `upper_bound`).
- **Stockout Risk Classification**: Compares projected demand over `lead_time_days` against `quantity_available` (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Suggested Reorder Quantity**: $\max(0, \text{Demand}_{\text{30D}} + \text{SafetyStock} - \text{AvailableStock})$.

---

## 3. Feature 2: Sales & Revenue Forecasting

- Aggregates historical posted invoice revenues by month and product category.
- Generates 1-month, 3-month, and 6-month revenue forecasts with prediction intervals (`[lower_bound, upper_bound]`).
- Compares actual historical revenue vs. backtested model predictions and displays `MAE`, `RMSE`, and `WAPE` transparently on the UI.

---

## 4. Feature 3: Business Anomaly Detection

Combines **Unsupervised Machine Learning (`IsolationForest` / multidimensional Z-Score)** with **Domain Rule Checks** across five operational vectors:

1. **Unexpected Stock Adjustments**: Large negative or unscheduled manual stock adjustments outside normal variance.
2. **Unusual Expense Spikes**: Expenses exceeding $2.5\sigma$ of the department/category rolling mean.
3. **Abnormal Purchase Unit Prices**: Purchase order items priced significantly above historical weighted average cost ($> +25\%$).
4. **Potential Duplicate Invoices / Bills**: Same supplier/customer, identical or near-identical amount within a 7-day window.
5. **Unusual Off-Hours / High-Velocity Transactions**: High-value journal entries or payments recorded with atypical patterns.

**Human-in-the-Loop Policy**: Every detected anomaly is logged in `anomaly_events` with `anomaly_score (0.00 - 1.00)`, `severity`, `reason`, and `recommended_action`. Anomalies **never** automatically accuse employees of fraud or block posted accounting records without human review (`OPEN` -> `UNDER_REVIEW` -> `RESOLVED` / `DISMISSED`).

---

## 5. Feature 4: Nexora AI Business Copilot

### Security & Governance Architecture
- **No Raw SQL Generation**: The Copilot never executes arbitrary LLM-generated SQL.
- **Permission-Scoped Read-Only Tools**:
  - `get_financial_summary` (requires `finance.view` or `dashboard.view`)
  - `get_low_stock_replenishment` (requires `inventory.view`)
  - `get_top_suppliers` (requires `procurement.view`)
  - `compare_quarterly_revenue` (requires `finance.reports.view` or `sales.view`)
  - `get_delayed_projects` (requires `projects.view`)
  - `get_pending_approvals_summary` (requires `approvals.view`)
  - `get_hr_workforce_summary` (requires `employees.view`; never exposes individual salaries without `hr.confidential.view`)
- **Provider Abstraction**: Supports configurable OpenAI-compatible API (`NEXORA_LLM_PROVIDER=openai|ollama|local_deterministic`), with a deterministic analytical reasoning synthesizer built in so the Copilot works out-of-the-box in offline/sandboxed environments and seamlessly upgrades when an external LLM API key is provided.
- **Fact vs. Interpretation Separation**: Every Copilot response returns structured `factual_data` (exact database figures and date ranges), `source_references` (e.g., `GL Accounts 4000-5999`, `Stock Balances Warehouse W-CMB`), and a clearly labeled `ai_interpretation` narrative.
