BEGIN;

CREATE POLICY quiz_taker_read
ON retail.customers
FOR SELECT TO quiz_taker
USING (true);

CREATE POLICY quiz_taker_read
ON retail.products
FOR SELECT TO quiz_taker
USING (true);

CREATE POLICY quiz_taker_read
ON retail.orders
FOR SELECT TO quiz_taker
USING (true);

CREATE POLICY quiz_taker_read
ON retail.order_items
FOR SELECT TO quiz_taker
USING (true);

COMMIT;