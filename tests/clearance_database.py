"""Run the actual clearance SELECT against local PostgreSQL; roll back fixtures."""
import ast
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
tree = ast.parse((root / 'src/python/web_app/clearance.py').read_text())
query = next(node.value for node in ast.walk(tree)
             if isinstance(node, ast.Constant) and isinstance(node.value, str)
             and 'JOIN LATERAL' in node.value)
for key, value in [('$1', 'NULL'), ('$2', 'NULL'), ('$3', '100'), ('$4', '0')]:
    query = query.replace(key, value)
migration = (root / 'data/database/clearance_promotions.sql').read_text()
sql = f"""
BEGIN;
{migration}
INSERT INTO retail.clearance_promotions
 (product_id, sale_price, starts_at, ends_at, approved_at, approved_by, revoked_at)
SELECT product_id, base_price * fraction, CURRENT_TIMESTAMP + starts,
       CURRENT_TIMESTAMP + ends,
       CASE WHEN approved THEN CURRENT_TIMESTAMP END,
       CASE WHEN approved THEN 'local-test-fixture' END,
       CASE WHEN revoked THEN CURRENT_TIMESTAMP END
FROM (SELECT product_id, base_price FROM retail.products ORDER BY product_id LIMIT 1) p
CROSS JOIN (VALUES
 (0.8, INTERVAL '-1 day', INTERVAL '1 day', TRUE, FALSE),
 (0.9, INTERVAL '-1 day', INTERVAL '1 day', TRUE, FALSE),
 (0.1, INTERVAL '-1 day', INTERVAL '1 day', FALSE, FALSE),
 (0.1, INTERVAL '-2 day', INTERVAL '-1 day', TRUE, FALSE),
 (0.1, INTERVAL '1 day', INTERVAL '2 day', TRUE, FALSE),
 (0.1, INTERVAL '-1 day', INTERVAL '1 day', TRUE, TRUE),
 (1.1, INTERVAL '-1 day', INTERVAL '1 day', TRUE, FALSE)
) fixtures(fraction, starts, ends, approved, revoked);
CREATE TEMP TABLE clearance_test_result AS {query};
DO $$ BEGIN
 IF (SELECT COUNT(*) FROM clearance_test_result) <> 1 THEN
   RAISE EXCEPTION 'Expected one unique active approved offer';
 END IF;
 IF NOT EXISTS (SELECT 1 FROM clearance_test_result WHERE
   ABS(sale_price - ROUND((base_price * 0.8)::numeric, 2)) < 0.001) THEN
   RAISE EXCEPTION 'Incorrect discount chosen';
 END IF;
END $$;
ROLLBACK;
"""
subprocess.run(['docker', 'exec', '-i', 'ai-tour-26-zava-diy-pgvector-db',
                'psql', '-U', 'postgres', '-d', 'zava', '-v', 'ON_ERROR_STOP=1'],
               input=sql, text=True, check=True)
print('PASS: actual SQL excludes pending, expired, future, revoked and overpriced offers; lowest valid offer wins')
