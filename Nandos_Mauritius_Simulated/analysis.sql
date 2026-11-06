-- SQLite syntax. All results describe synthetic data only.
-- 1. Overall KPIs: count orders separately to avoid counting order lines.
SELECT COUNT(DISTINCT CASE WHEN line_status='Sold' THEN order_id END) AS total_orders,
 ROUND(SUM(retained_sales_incl_vat_mur),2) AS retained_sales_incl_vat_mur,
 ROUND(SUM(sales_less_food_cost_proxy_mur),2) AS sales_less_food_cost_proxy_mur,
 ROUND(SUM(retained_sales_incl_vat_mur)/COUNT(DISTINCT CASE WHEN line_status='Sold' THEN order_id END),2) AS average_order_value_mur,
 ROUND(100.0*SUM(sales_less_food_cost_proxy_mur)/SUM(retained_sales_incl_vat_mur),2) AS food_contribution_proxy_pct
FROM order_items;
-- 2. Monthly trends
SELECT substr(o.order_date,1,7) AS month, COUNT(DISTINCT CASE WHEN i.line_status='Sold' THEN o.order_id END) AS orders,
 ROUND(SUM(i.retained_sales_incl_vat_mur),2) AS retained_sales_incl_vat_mur
FROM orders o JOIN order_items i ON i.order_id=o.order_id
GROUP BY substr(o.order_date,1,7) ORDER BY month;
-- 3. Branch performance
SELECT b.branch_name, SUM(i.retained_sales_incl_vat_mur) AS retained_sales_incl_vat_mur,
 SUM(i.sales_less_food_cost_proxy_mur) AS sales_less_food_cost_proxy_mur
FROM branches b JOIN orders o ON b.branch_id=o.branch_id
JOIN order_items i ON i.order_id=o.order_id GROUP BY b.branch_name ORDER BY retained_sales_incl_vat_mur DESC;
-- 4. Menu performance
SELECT p.product_name, SUM(i.quantity) AS units, SUM(i.retained_sales_incl_vat_mur) AS retained_sales_incl_vat_mur,
 SUM(i.sales_less_food_cost_proxy_mur) AS sales_less_food_cost_proxy_mur
FROM products p JOIN order_items i ON p.product_id=i.product_id
GROUP BY p.product_name ORDER BY retained_sales_incl_vat_mur DESC;
-- 5. Channel performance
SELECT o.sales_channel, COUNT(DISTINCT CASE WHEN i.line_status='Sold' THEN o.order_id END) AS orders, SUM(i.retained_sales_incl_vat_mur) AS retained_sales_incl_vat_mur
FROM orders o JOIN order_items i ON i.order_id=o.order_id GROUP BY o.sales_channel;
-- 6. Peak hours: orders only, avoiding item duplication
SELECT substr(order_datetime,12,2) AS hour, COUNT(*) AS orders
FROM orders WHERE payment_status!='Not Captured' GROUP BY substr(order_datetime,12,2) ORDER BY hour;

-- 7. Sales bridge. Voids/cancellations are excluded before recorded sales.
SELECT SUM(attempted_sales_incl_vat_mur) AS attempted_value,
 SUM(voided_value_incl_vat_mur) AS voided_value,
 SUM(cancelled_value_incl_vat_mur) AS cancelled_value,
 SUM(sales_after_discount_incl_vat_mur) AS recorded_sales,
 SUM(refund_amount_incl_vat_mur) AS refunds,
 SUM(retained_sales_incl_vat_mur) AS retained_sales
FROM order_items;
-- 8. Order outcomes by channel (one row per order, no item join).
SELECT sales_channel,order_status,COUNT(*) AS order_count FROM orders
GROUP BY sales_channel,order_status ORDER BY sales_channel,order_status;
-- 9. Item removals and refund reasons.
SELECT line_status,removal_reason,refund_reason,COUNT(*) AS affected_lines,
 SUM(refund_amount_incl_vat_mur) AS refunds, SUM(wasted_food_cost_mur) AS waste
FROM order_items WHERE line_status!='Sold' OR refund_amount_incl_vat_mur>0
GROUP BY line_status,removal_reason,refund_reason;
-- 10. Retained sales by channel after refunds.
SELECT o.sales_channel,COUNT(DISTINCT CASE WHEN i.line_status='Sold' THEN o.order_id END) AS paid_orders,
 SUM(i.retained_sales_incl_vat_mur) AS retained_sales
FROM orders o JOIN order_items i ON i.order_id=o.order_id GROUP BY o.sales_channel;

-- 11. Waiter upsell attribution: descriptive, not proven incremental lift.
SELECT s.waiter_name,COUNT(DISTINCT o.order_id) AS attributed_orders,
 SUM(i.retained_sales_incl_vat_mur) AS upsell_sales_incl_vat
FROM order_items i JOIN orders o USING(order_id) JOIN staff s USING(waiter_id)
WHERE i.is_waiter_upsell=1 GROUP BY s.waiter_name;
-- 12. Upsell opportunity counts must come from orders, avoiding line duplication.
SELECT waiter_id,COUNT(*) AS paid_dine_in_orders,SUM(upsell_offered) AS offers
FROM orders WHERE sales_channel='Dine-in' AND payment_status!='Not Captured' AND sale_type='Customer'
GROUP BY waiter_id;
-- 13. Wrong-order incremental waste.
SELECT waste_reason,COUNT(*) AS events,SUM(incremental_waste_cost_mur) AS cost
FROM waste_events GROUP BY waste_reason;
-- 14. Additional waste deducted once, aggregating each fact independently.
SELECT (SELECT SUM(sales_less_food_cost_proxy_mur) FROM order_items) -
 (SELECT COALESCE(SUM(incremental_waste_cost_mur),0) FROM waste_events)
 AS contribution_after_incremental_waste_proxy_mur;
-- 15. Extras by type and origin.
SELECT p.product_name,i.extra_origin,SUM(i.quantity) AS units,
 SUM(i.retained_sales_incl_vat_mur) AS sales_incl_vat
FROM order_items i JOIN products p USING(product_id)
WHERE i.item_type='Extra' GROUP BY p.product_name,i.extra_origin;

-- 16. Separate staff meals from customer sales. Paid lines only for discounts.
SELECT o.sale_type,COUNT(DISTINCT CASE WHEN i.line_status='Sold' THEN o.order_id END) AS paid_orders,
 SUM(CASE WHEN i.line_status='Sold' THEN i.pre_discount_sales_incl_vat_mur ELSE 0 END) AS sold_menu_value,
 SUM(CASE WHEN i.line_status='Sold' THEN i.discount_mur ELSE 0 END) AS sold_discounts,
 SUM(i.retained_sales_incl_vat_mur) AS receipts_incl_vat,
 SUM(i.food_cost_mur) AS modelled_ingredient_cost
FROM orders o JOIN order_items i USING(order_id) GROUP BY o.sale_type;
-- 17. Staff meal spend by branch.
SELECT b.branch_name,COUNT(DISTINCT o.order_id) AS staff_meals,
 SUM(i.retained_sales_incl_vat_mur) AS receipts_incl_vat
FROM branches b JOIN orders o USING(branch_id) JOIN order_items i USING(order_id)
WHERE o.sale_type='Staff Meal' GROUP BY b.branch_name;
