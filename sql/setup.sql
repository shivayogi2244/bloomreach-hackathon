-- ============================================================
-- PICK A HOME for the tables (any of these works):
--   Option A: workspace.default            (always exists)
--   Option B: databricks-hackathon.shivayogimath_dc
--   Option C: any catalog.schema you can write to
--
-- To switch: find/replace the prefix on every line below,
-- then set in .env:  DATABRICKS_TABLE=<catalog>.<schema>.loop_segments
-- ============================================================

CREATE OR REPLACE TABLE workspace.default.loop_customers (
  email        STRING,
  first_name   STRING,
  last_name    STRING,
  total_spent  DOUBLE,
  order_count  INT,
  last_order_at DATE
);

INSERT INTO workspace.default.loop_customers VALUES
  ('maya@example.com','Maya','Patel', 2480.00, 9,  DATE '2026-09-01'),
  ('liam@example.com','Liam','Chen',  1890.00, 7,  DATE '2026-08-12'),
  ('ava@example.com','Ava','Nolan',  1520.00, 6,  DATE '2026-05-30'),
  ('noah@example.com','Noah','Reid',  1100.00, 4,  DATE '2026-03-14'),
  ('zoe@example.com','Zoe','Marsh',   980.00, 5,  DATE '2026-04-02'),
  ('raj@example.com','Raj','Iyer',    640.00, 3,  DATE '2026-06-21');

CREATE OR REPLACE TABLE workspace.default.loop_segments AS
SELECT c.*,
  CASE
    WHEN c.total_spent >= 1500 AND c.last_order_at >= date_sub(current_date(), 45) THEN 'vip'
    WHEN c.last_order_at <  date_sub(current_date(), 90) THEN 'churn_risk'
    WHEN c.order_count <= 2 THEN 'new'
    ELSE 'active'
  END AS segment
FROM workspace.default.loop_customers c;

-- Sanity check: expect 6 rows, Ava/Zoe/Noah = churn_risk
SELECT * FROM workspace.default.loop_segments ORDER BY total_spent DESC;
