import csv, random, sqlite3, json, zipfile
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).parent
OUT = ROOT / "Nandos_Mauritius_Simulated"
OUT.mkdir(exist_ok=True)
r = random.Random(42)
branches = [(1,"Nando's GBLC","North",75),(2,"Nando's Cascavelle","West",65),(3,"Nando's Phoenix","Central",85),(4,"Nando's Bagatelle","Central",95),(5,"Nando's RTM","North",70),(6,"Nando's So’flo","Central",55)]
# Published menu snapshot linked from nandos.mu, checked 2026-10-25.
# Menu states prices valid until September 2026. Costs remain invented.
products = [(1,"1/4 Chicken","Chicken",295,85),(2,"1/2 Chicken","Chicken",465,155),(3,"Full Chicken","Chicken",859,290),(4,"Nando's Classic Burger","Burgers",305,95),(5,"Nando's Classic Wrap","Wraps",305,100),(6,"Cauliflower Burger","Vegetarian",242,85),(7,"PERi-PERi Chips (Regular)","Sides",115,25),(8,"Spicy Rice (Regular)","Sides",115,28),(9,"Coleslaw (Regular)","Sides",115,25),(10,"Soft Drink 500ml","Drinks",95,18),(11,"Crystal Still Water (500 ml)","Drinks",75,12),(12,"Chocolate Fondant","Desserts",245,45)]

orders, lines = [], []
start=datetime(2025,1,1)
for day in range(365):
    date=start+timedelta(days=day)
    for bid,name,region,base in branches:
        seasonal=1.20 if date.month==12 else (0.90 if date.month in [2,6] else 1)
        weekend=1.35 if date.weekday()>=4 else 1
        count=round(base*seasonal*weekend*(1+day/365*0.10)*r.uniform(.85,1.15))
        for _ in range(count):
            oid=len(orders)+1
            hour=r.choices(list(range(11,23)),[2,8,10,6,3,2,3,7,12,10,6,2])[0]
            stamp=date.replace(hour=hour,minute=r.randrange(60),second=r.randrange(60))
            channel=r.choices(["Dine-in","Takeaway","Delivery","Call and Collect"],[.40,.25,.20,.15])[0]
            orders.append((oid,stamp.isoformat(sep=" "),date.date().isoformat(),bid,channel,r.choices(["Card","Cash","Mobile"],[.60,.25,.15])[0]))
            main=r.choices(products[:6],[30,22,8,20,15,5])[0]
            basket=[main]
            if r.random()<.78: basket.append(r.choice(products[6:9]))
            if r.random()<.82: basket.append(r.choice(products[9:11]))
            if r.random()<.15: basket.append(products[11])
            discount=0  # Discounts disabled; no promotional eligibility is inferred.
            for p in basket:
                pid,pname,cat,price,cost=p
                qty=r.choices([1,2,3],[.85,.13,.02])[0]
                gross=qty*price*100
                disc=gross*discount//100
                net=gross-disc
                food=qty*cost*100
                lines.append((len(lines)+1,oid,pid,qty,price,cost,discount,gross/100,disc/100,net/100,food/100,(net-food)/100))

# Operational rules are illustrative, not Nando's policies or observed rates.
# Run after basket generation so demand and menu sampling remain reproducible.
op = random.Random(43)
grouped = {}
for line in lines:
    grouped.setdefault(line[1], []).append(line)
updated_orders, updated_lines = [], []
for order in orders:
    oid = order[0]
    status = op.choices(["Completed","Cancelled","Voided","Partially Refunded","Fully Refunded"],
                        [.95,.02,.01,.015,.005])[0]
    order_reason = (op.choice(["Customer changed mind","Customer unreachable","Collection not collected"])
                    if status == "Cancelled" else
                    op.choice(["Duplicate entry","Incorrect order entry"]) if status == "Voided" else "")
    # In this model cancellations and voids occur before payment capture.
    # Paid orders subsequently returned are represented by refunds.
    payment_status = ("Not Captured" if status in ["Cancelled","Voided"] else
                      "Partially Refunded" if status=="Partially Refunded" else
                      "Fully Refunded" if status=="Fully Refunded" else "Paid")
    updated_orders.append((*order,status,payment_status,order_reason))
    stamp = datetime.fromisoformat(order[1])
    final_stamp = (stamp+timedelta(minutes=op.randint(1,45))).isoformat(sep=" ")
    for idx,line in enumerate(grouped[oid]):
        line_status = ("Voided" if status == "Voided" else "Cancelled" if status=="Cancelled"
                       else "Voided" if idx>0 and status=="Completed" and op.random()<.015 else "Sold")
        potential_cents = round(line[9]*100)
        sold_cents = potential_cents if line_status=="Sold" else 0
        refund_cents = (sold_cents if status=="Fully Refunded" else
                        sold_cents//2 if status=="Partially Refunded" and idx==0 else 0)
        reason = (op.choice(["Food quality","Incorrect item","Missing item"]) if refund_cents else "")
        void_reason = ("Incorrect item entry" if line_status=="Voided" and status!="Voided" else order_reason)
        # Sold food is consumed even when refunded. Some cancelled food is wasted.
        waste_cents = round(line[10]*100) if line_status=="Cancelled" and op.random()<.40 else 0
        consumed_cents = round(line[10]*100) if line_status=="Sold" else waste_cents
        retained_cents = sold_cents-refund_cents
        updated_lines.append((*line[:9],sold_cents/100,consumed_cents/100,
                              (retained_cents-consumed_cents)/100,
                              line_status,potential_cents/100,
                              potential_cents/100 if line_status=="Voided" else 0,
                              potential_cents/100 if line_status=="Cancelled" else 0,
                              refund_cents/100,retained_cents/100,waste_cents/100,
                              final_stamp if refund_cents else "",reason,
                              final_stamp if line_status!="Sold" else "",void_reason))
orders,lines = updated_orders,updated_lines
from operations_extras import enrich
orders,lines,products,staff,extra_catalog,waste = enrich(orders,lines,products)
from staff_meals import apply_staff_meals
orders,lines = apply_staff_meals(orders,lines,waste)
tables={
 "branches":(["branch_id","branch_name","region"],[b[:3] for b in branches]),
 "products":(["product_id","product_name","category","reference_price_mur","reference_food_cost_mur"],products),
 "orders":(["order_id","order_datetime","order_date","branch_id","sales_channel","payment_method","order_status","payment_status","order_status_reason","waiter_id","upsell_offered","sale_type","recipient_staff_id"],orders),
 "order_items":(["order_item_id","order_id","product_id","quantity","unit_price_mur","unit_food_cost_mur","discount_percent","pre_discount_sales_incl_vat_mur","discount_mur","sales_after_discount_incl_vat_mur","food_cost_mur","sales_less_food_cost_proxy_mur","line_status","attempted_sales_incl_vat_mur","voided_value_incl_vat_mur","cancelled_value_incl_vat_mur","refund_amount_incl_vat_mur","retained_sales_incl_vat_mur","wasted_food_cost_mur","refund_datetime","refund_reason","removed_datetime","removal_reason","item_type","is_waiter_upsell","extra_origin","discount_reason","staff_unit_price_mur","staff_price_basis"],lines)}
tables["staff"]=(["waiter_id","branch_id","waiter_name"],[(0,0,"Not waiter-served")]+staff)
tables["extra_catalog"]=(["product_id","extra_name","reference_price_mur","assumed_food_cost_mur","price_basis","unit"],extra_catalog)
tables["waste_events"]=(["waste_event_id","order_id","order_item_id","branch_id","waste_datetime","product_id","waste_quantity","incremental_waste_cost_mur","waste_reason","resolution","responsibility"],waste)
# Rebuild the generated database cleanly on every run.
(OUT/"restaurant.sqlite").unlink(missing_ok=True)
db=sqlite3.connect(":memory:")
for table,(headers,rows) in tables.items():
    with (OUT/(table+".csv")).open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(headers);w.writerows(rows)
    db.execute("DROP TABLE IF EXISTS "+table)
    types=["INTEGER" if isinstance(v,int) else "REAL" if isinstance(v,float) else "TEXT" for v in rows[0]]
    db.execute("CREATE TABLE "+table+" ("+",".join(h+" "+t for h,t in zip(headers,types))+")")
    db.executemany("INSERT INTO "+table+" VALUES ("+",".join("?" for _ in headers)+")",rows)
db.commit()
assert db.execute("SELECT COUNT(*) FROM order_items i LEFT JOIN orders o ON o.order_id=i.order_id WHERE o.order_id IS NULL").fetchone()[0]==0
assert db.execute("SELECT COUNT(*) FROM order_items WHERE abs(pre_discount_sales_incl_vat_mur-discount_mur-attempted_sales_incl_vat_mur)>.001 OR abs(retained_sales_incl_vat_mur-food_cost_mur-sales_less_food_cost_proxy_mur)>.001 OR abs(sales_after_discount_incl_vat_mur-refund_amount_incl_vat_mur-retained_sales_incl_vat_mur)>.001 OR abs(attempted_sales_incl_vat_mur-sales_after_discount_incl_vat_mur-voided_value_incl_vat_mur-cancelled_value_incl_vat_mur)>.001").fetchone()[0]==0
assert db.execute("SELECT COUNT(*) FROM order_items WHERE refund_amount_incl_vat_mur<0 OR refund_amount_incl_vat_mur>sales_after_discount_incl_vat_mur OR (line_status!='Sold' AND sales_after_discount_incl_vat_mur!=0)").fetchone()[0]==0
assert db.execute("SELECT COUNT(*) FROM orders WHERE sales_channel NOT IN ('Dine-in','Takeaway','Delivery','Call and Collect')").fetchone()[0]==0
summary=dict(orders=len(orders),order_items=len(lines),sales_after_discount_incl_vat_mur=round(sum(x[9] for x in lines),2),sales_less_food_cost_proxy_mur=round(sum(x[11] for x in lines),2))
assert len({row[0] for row in lines}) == len(lines)
assert db.execute("SELECT COUNT(*) FROM order_items i JOIN orders o USING(order_id) WHERE i.is_waiter_upsell=1 AND (o.waiter_id=0 OR o.upsell_offered=0 OR o.sales_channel!='Dine-in')").fetchone()[0]==0
assert db.execute("SELECT COUNT(*) FROM waste_events w LEFT JOIN order_items i ON w.order_item_id=i.order_item_id WHERE i.order_item_id IS NULL OR w.order_id!=i.order_id OR w.incremental_waste_cost_mur<=0").fetchone()[0]==0
assert db.execute("SELECT COUNT(*) FROM order_items i JOIN orders o USING(order_id) WHERE (o.sale_type='Staff Meal' AND (i.discount_percent<=0 OR i.discount_percent>100 OR i.discount_reason!='Staff Meal Discount' OR i.item_type='Extra')) OR (o.sale_type='Customer' AND i.discount_mur!=0)").fetchone()[0]==0
assert db.execute("SELECT COUNT(*) FROM orders o LEFT JOIN staff s ON o.recipient_staff_id=s.waiter_id WHERE o.sale_type='Staff Meal' AND (s.waiter_id IS NULL OR s.branch_id!=o.branch_id OR o.waiter_id!=0 OR o.upsell_offered!=0)").fetchone()[0]==0
summary["staff_meal_orders"]=db.execute("SELECT COUNT(*) FROM orders WHERE sale_type='Staff Meal'").fetchone()[0]
summary["staff_meal_discount_mur"]=db.execute("SELECT SUM(i.discount_mur) FROM order_items i JOIN orders o USING(order_id) WHERE o.sale_type='Staff Meal' AND i.line_status='Sold'").fetchone()[0]
summary["staff_meal_receipts_incl_vat_mur"]=db.execute("SELECT SUM(i.retained_sales_incl_vat_mur) FROM order_items i JOIN orders o USING(order_id) WHERE o.sale_type='Staff Meal'").fetchone()[0]
summary["extra_lines"]=len([x for x in lines if x[23]=="Extra"])
summary["waiter_upsell_lines"]=sum(x[24] for x in lines)
summary["wrong_order_waste_events"]=len(waste)
summary["incremental_wrong_order_waste_cost_mur"]=round(sum(w[7] for w in waste),2)
summary["contribution_after_incremental_waste_proxy_mur"]=round(sum(x[11] for x in lines)-sum(w[7] for w in waste),2)
summary["status_counts"] = dict(db.execute("SELECT order_status,COUNT(*) FROM orders GROUP BY order_status").fetchall())
summary["channel_counts"] = dict(db.execute("SELECT sales_channel,COUNT(*) FROM orders GROUP BY sales_channel").fetchall())
summary["refund_amount_incl_vat_mur"] = round(sum(x[16] for x in lines),2)
summary["retained_sales_incl_vat_mur"] = round(sum(x[17] for x in lines),2)
summary["voided_value_incl_vat_mur"] = round(sum(x[14] for x in lines),2)
summary["cancelled_value_incl_vat_mur"] = round(sum(x[15] for x in lines),2)
(OUT/"validation.json").write_text(json.dumps(summary,indent=2))
queries="""-- SQLite syntax. All results describe synthetic data only.
-- 1. Overall KPIs: count orders separately to avoid counting order lines.
SELECT COUNT(DISTINCT order_id) AS total_orders,
 ROUND(SUM(sales_after_discount_incl_vat_mur),2) AS sales_after_discount_incl_vat_mur,
 ROUND(SUM(sales_less_food_cost_proxy_mur),2) AS sales_less_food_cost_proxy_mur,
 ROUND(SUM(sales_after_discount_incl_vat_mur)/COUNT(DISTINCT order_id),2) AS average_order_value_mur,
 ROUND(100.0*SUM(sales_less_food_cost_proxy_mur)/SUM(sales_after_discount_incl_vat_mur),2) AS food_contribution_proxy_pct
FROM order_items;
-- 2. Monthly trends
SELECT substr(o.order_date,1,7) AS month, COUNT(DISTINCT o.order_id) AS orders,
 ROUND(SUM(i.sales_after_discount_incl_vat_mur),2) AS sales_after_discount_incl_vat_mur
FROM orders o JOIN order_items i ON i.order_id=o.order_id
GROUP BY substr(o.order_date,1,7) ORDER BY month;
-- 3. Branch performance
SELECT b.branch_name, SUM(i.sales_after_discount_incl_vat_mur) AS sales_after_discount_incl_vat_mur,
 SUM(i.sales_less_food_cost_proxy_mur) AS sales_less_food_cost_proxy_mur
FROM branches b JOIN orders o ON b.branch_id=o.branch_id
JOIN order_items i ON i.order_id=o.order_id GROUP BY b.branch_name ORDER BY sales_after_discount_incl_vat_mur DESC;
-- 4. Menu performance
SELECT p.product_name, SUM(i.quantity) AS units, SUM(i.sales_after_discount_incl_vat_mur) AS sales_after_discount_incl_vat_mur,
 SUM(i.sales_less_food_cost_proxy_mur) AS sales_less_food_cost_proxy_mur
FROM products p JOIN order_items i ON p.product_id=i.product_id
GROUP BY p.product_name ORDER BY sales_after_discount_incl_vat_mur DESC;
-- 5. Channel performance
SELECT o.sales_channel, COUNT(DISTINCT o.order_id) AS orders, SUM(i.sales_after_discount_incl_vat_mur) AS sales_after_discount_incl_vat_mur
FROM orders o JOIN order_items i ON i.order_id=o.order_id GROUP BY o.sales_channel;
-- 6. Peak hours: orders only, avoiding item duplication
SELECT substr(order_datetime,12,2) AS hour, COUNT(*) AS orders
FROM orders GROUP BY substr(order_datetime,12,2) ORDER BY hour;
"""

# Analyse retained sales consistently; monetary deductions are already in the line values.
queries = queries.replace("sales_after_discount_incl_vat_mur", "retained_sales_incl_vat_mur")
queries = queries.replace("COUNT(DISTINCT order_id)", "COUNT(DISTINCT CASE WHEN line_status='Sold' THEN order_id END)")
queries = queries.replace("COUNT(DISTINCT o.order_id)", "COUNT(DISTINCT CASE WHEN i.line_status='Sold' THEN o.order_id END)")
queries = queries.replace("FROM orders GROUP BY", "FROM orders WHERE payment_status!='Not Captured' GROUP BY")
queries += """
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
"""

queries += """
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
"""

queries += """
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
"""
(OUT/"analysis.sql").write_text(queries)
for q in queries.split(";"):
    if q.strip(): db.execute(q).fetchall()
(OUT/"restaurant.sqlite").write_bytes(db.serialize())
db.close()
(OUT/"README.md").write_text("""# Nando's Mauritius — Simulated Restaurant Analytics
Independent educational portfolio project by Pheisel Gopito.
Not affiliated with or endorsed by Nando's. All transactions and food costs are invented. The six branch labels identify real locations; their order volumes are arbitrary simulation assumptions, not actual branch performance. Menu item names and eleven main-menu list prices come from the takeaway PDF linked from the official Mauritius website, checked 2026-10-25. The PDF states prices valid until September 2026; they are a published snapshot, not guaranteed current prices. The quarter-chicken regular price is overridden to MUR295 based on user-provided information. Staff quarter chicken MUR95 and regular side MUR50 are user-provided prices, not independently verified. These are NOT actual Nando's sales results.

Source: https://www.nandos.mu/
Official linked menu: https://images.nandos.co.za/menu/mu/Mauritius_Takeout_Menu.pdf
The 2026 published snapshot is applied uniformly to the synthetic 2025 scenario for training. It does not establish historical 2025 prices. Standalone prices only; bundled side discounts are not modelled.

## Scope and assumptions
- 1 January–31 December 2025; MUR; timestamps in Mauritius local time.
- Six real branch labels and twelve source-backed menu items plus twelve extra product options. GBLC = Grand Baie La Croisette; RTM = Riche Terre Mall; So’flo = So’flo Mall, Floreal. Cascavelle, Phoenix and Bagatelle use their mall names. Regional groupings are illustrative.
- Seed 42. Assumed lunch/dinner peaks, stronger Friday–Sunday demand, December uplift, and gradual growth. These are generator assumptions, not discovered business facts.
- Includes completed, cancelled, voided, partially refunded and fully refunded orders. No customer identities, holidays, stockouts or tax calculations. Outcome probabilities are synthetic: 95% completed, 2% cancelled, 1% voided, 1.5% partially refunded and 0.5% fully refunded. Four channel weights: dine-in 40%, takeaway 25%, delivery 20%, call and collect 15%. These assumptions do not describe actual operations.
- Published prices include VAT. No VAT rate or VAT removal is modelled. Food costs are simulated ingredients only, excluding packaging, wastage and labour. sales_less_food_cost_proxy_mur is VAT-inclusive retained sales after refunds minus invented food costs: an illustrative contribution proxy, NOT accounting gross profit, net profit or revenue excluding VAT. Packaging charges and delivery fees are also omitted; this models food item receipts only.
- Delivery commissions, rent, wages and utilities are excluded. Channel comparisons therefore do not measure full channel profitability.
- Prices and food costs are constant across branches and time. Demand patterns are synthetic, not calibrated to real sales volumes.

## Files
Seven UTF-8 CSV tables for SQL/Power BI; restaurant.sqlite is a ready-to-query SQLite database. analysis.sql contains seventeen working starter queries. validation.json provides reconciliation totals. generate.py reproduces the data using Python's standard library.

## Model and grain
branches 1 → many orders; orders 1 → many order_items; products 1 → many order_items.
Use single-direction relationships towards order_items in Power BI. Add a calendar table linked to orders.order_date.
Do not sum order IDs. Total orders is DISTINCTCOUNT(order_items[order_id]) for product-aware counts.

## Data dictionary
- branches: branch_id (unique integer key), branch_name (real branch label; synthetic transactions), region (illustrative geographical grouping).
- products: product_id (unique key), product_name, category, reference_price_mur and reference_food_cost_mur (published VAT-inclusive list price and invented food cost per unit, respectively).
- orders: order_id (unique key), order_datetime (local ISO timestamp), order_date (ISO date), branch_id (foreign key), sales_channel (Dine-in/Takeaway/Delivery/Call and Collect), payment_method (Card/Cash/Mobile).
- order_items: order_item_id (unique line key), order_id and product_id (foreign keys), quantity (units), unit_price_mur and unit_food_cost_mur (transaction snapshots), discount_percent (0 for customer orders, effective item-specific rate for staff meals).
- pre_discount_sales_incl_vat_mur = quantity × unit_price_mur.
- discount_mur is the exact full-price value less quantity × staff_unit_price_mur for staff meals. discount_percent is derived and rounded to six decimal places for display; use the monetary amount for reconciliation.
- attempted_sales_incl_vat_mur = pre_discount_sales_incl_vat_mur − discount_mur.
- sales_after_discount_incl_vat_mur = attempted value for Sold lines, zero for removed lines.
- retained_sales_incl_vat_mur = recorded sales − refund_amount_incl_vat_mur.
- food_cost_mur = quantity × unit_food_cost_mur.
- sales_less_food_cost_proxy_mur = retained_sales_incl_vat_mur − food_cost_mur.
- food_cost_mur includes modelled consumed ingredients and cancellation waste. Refunding sold food does not reverse ingredient cost.

## Start in Power BI
1. Extract the ZIP into a permanent folder on your Windows PC.
2. Open Power BI Desktop → Get data → Text/CSV → branches.csv → Transform Data.
3. Import products.csv, orders.csv and order_items.csv the same way.
4. Set IDs and quantities to whole numbers, monetary fields to fixed decimal, order_date to Date, and order_datetime to Date/Time.
5. Create the three relationships above. Build measures from order_items.

## Initial DAX measures (create separately)
Recorded Sales Including VAT = SUM(order_items[sales_after_discount_incl_vat_mur])
Refunds Including VAT = SUM(order_items[refund_amount_incl_vat_mur])
Sales Including VAT = SUM(order_items[retained_sales_incl_vat_mur])
Paid Orders = CALCULATE(DISTINCTCOUNT(order_items[order_id]), order_items[line_status] = "Sold")
Food Contribution Proxy = SUM(order_items[sales_less_food_cost_proxy_mur])
Total Orders = DISTINCTCOUNT(order_items[order_id])
Average Order Value = DIVIDE([Sales Including VAT], [Paid Orders])
Food Contribution Proxy % = DIVIDE([Food Contribution Proxy], [Sales Including VAT])
Format amounts as MUR and Food Contribution Proxy % as percentage.

## Operational definitions and extra fields
These are explicit project conventions, not verified Nando's POS rules:
- Dine-in: food consumed on premises. Takeaway: walk-in order to go. Call and Collect: telephone order collected by customer. Delivery: order delivered to customer.
- order_status: final whole-order outcome. payment_status: Not Captured, Paid, Partially Refunded, Fully Refunded. payment_method on uncaptured orders denotes intended tender.
- Voided: entry corrected/removed before payment capture. Includes whole-order voids and extra item voids in some completed orders. At least the main remains sold for a completed order.
- Cancelled: abandoned before payment capture; excludes completed sales. No prepaid cancellation scenario is modelled.
- Refund: return of captured money, full order or half of the first item's value for a partial refund. At most one refund per item, on the original order day 1–45 minutes later. No cross-period refunds or refund payment ledger is modelled.
- line_status: Sold/Voided/Cancelled. A refunded item remains Sold, with a separate positive refund amount; do not filter it out before subtracting refunds.
- voided_value_incl_vat_mur, cancelled_value_incl_vat_mur: excluded attempted value, not cash outflows. Never subtract them again from recorded sales.
- refund_amount_incl_vat_mur: returned money; refund_datetime and refund_reason document it.
- removed_datetime and removal_reason: item void/cancellation timing and reason.
- wasted_food_cost_mur: subset of food_cost_mur from cancelled food (40% per cancelled line); zero food cost for voids. This waste is an invented assumption.
- All Orders counts every attempt. Paid Orders includes completed and subsequently refunded orders; cancellation/void rates use all attempted orders as denominator. Refund order rate uses orders with captured payment as denominator.
- Starter SQL queries 1–6 use retained sales and paid-order counts; queries 7–10 expose the sales bridge and operating outcomes. Use Paid Orders for AOV and retained sales for after-refund reporting. Refunded orders remain in paid-order counts.

## Extras, waiter upselling and wrong-order waste
- extra_catalog.csv gives twelve extra options, their units and price provenance. Mushroom, Creamy Dip, Vodka and Rhum have assumed prices; alcohol availability and serving sizes are unverified. Do not present them as confirmed Nando's menu items. Listed menu prices are snapshots, not current guarantees.
- Olives use a standalone starter price; strips and pulled chicken use published salad add-on prices. Treat these as standalone extra transactions for this exercise, not universal add-on prices or proven combinations.
- No customisation compatibility is modelled. Alcohol rows represent separate beverages, not food toppings. This is synthetic data, with no real customers.
- Extras are ordinary order_items rows (item_type=Extra), included once in all sales and refund totals. is_waiter_upsell distinguishes accepted suggestions from customer-requested extras. Refunds reverse extra sales for fully refunded orders.
- staff.csv contains 24 fictitious waiters, four per branch, plus waiter_id=0 for non-waiter channels. Dine-in is the only waiter-attributed channel in this scenario.
- upsell_offered on orders is a binary opportunity flag. 60% of paid dine-in orders receive an offer and 42% of those accept (synthetic assumptions). Some customers request extras without accepting an offer. Do not label every extra a waiter upsell.
- Offered Orders = sum of orders.upsell_offered. Accepted Orders = distinct order_items.order_id where is_waiter_upsell=1. Conversion = Accepted Orders / Offered Orders; offer rate uses paid dine-in orders. Retain fully refunded orders in acceptance counts, but subtract refunds from attributed sales. These measures describe attribution, not causal sales lift or fair waiter rankings.
- waste_events.csv records additional discarded ingredients when a wrong item/flavour/extra requires a remake. Each event links to its original order line. Assumed event rate: 0.6% of eligible sold menu lines; excludes fully refunded/cancelled/voided lines. Quantity and cost describe one discarded preparation; the corrected preparation stays in original food_cost_mur.
- Waste responsibility is unspecified kitchen/entry error. The serving waiter is an attribution link, not evidence of who made an error.
- Existing cancellation waste stays in order_items.wasted_food_cost_mur. Total waste cost = SUM(order_items.wasted_food_cost_mur) + SUM(waste_events.incremental_waste_cost_mur).
- Additional waste is NOT included in line contribution. Contribution after additional waste = SUM(order_items.sales_less_food_cost_proxy_mur) − SUM(waste_events.incremental_waste_cost_mur). This remains an illustrative VAT-inclusive proxy.
- Model: staff 1→many orders; orders 1→many waste_events. Keep waste separate from order_items and avoid joining these facts directly when summing sales; use shared dimensions or aggregate independently. Do not add a second active branch→waste path when filtering via orders.
- Wrong-order remakes retain the original sale and record additional cost; a refund alone never implies waste. Some orders can have both a partial refund and a remake.

## Staff meals (user-supplied prices and estimated fallback)
- orders.sale_type separates Customer and Staff Meal independently of sales_channel. Staff meals are not a fifth channel.
- staff_meals.py uses user-provided staff prices: quarter chicken MUR95 against regular MUR295 (MUR200 off, about 67.7966%); regular sides MUR50 against MUR115 (MUR65 off, about 56.5217%). Other menu items use an adjustable estimated 50% fallback. A 2% selection probability among eligible completed dine-in orders remains a synthetic assumption. Eligibility is synthetic: no offer, extra sale, refund or wrong-order waste event. Staff meals may retain previously voided entries.
- recipient_staff_id refers to a fictitious employee of that branch, separate from serving waiter_id. Staff meals have serving waiter_id=0 and no upsell attribution. The fictitious waiter roster doubles as the staff recipient roster for this exercise.
- staff_unit_price_mur records the per-unit staff price on staff lines (zero otherwise). staff_price_basis distinguishes User supplied from Estimated 50% fallback.
- The discount applies to the selected menu basket, excluding extras and alcohol. This scope is an assumption. Only completed staff meals are generated; no staff meal refund lifecycle is simulated.
- discount_reason records Staff Meal Discount. Show full menu value, discount, paid receipts and estimated ingredient cost separately. Filter line_status=Sold when aggregating realised staff discounts; discounts on voided entries are not granted discounts.
- Staff-meal discount is not waste or a refund, and it is not deducted twice: retained_sales_incl_vat_mur already reflects it. Ingredients retain their full simulated cost.
- Sales bridge starts with full entered menu value, less entered discount, equals attempted value; then subtract voids/cancellations and refunds to obtain retained receipts. Filter sale_type=Customer for public customer KPIs, channel comparisons and waiter opportunity rates; show staff meal receipts separately.
- In Power BI, add a sale_type slicer and a staff-meal section with paid meal count, sold discount amount and receipts. Base all-sales measures include staff meals unless explicitly filtered.
- Customer Sales Including VAT = CALCULATE([Sales Including VAT], orders[sale_type] = "Customer")
- Staff Meal Receipts Including VAT = CALCULATE([Sales Including VAT], orders[sale_type] = "Staff Meal")

## Suggested dashboard
Executive Overview: KPI cards, monthly sales, branch sales and channel mix.
Branch & Operations: weekday/hour patterns, four-channel comparisons, void/cancellation rates, refund reasons and cancellation food waste.
Menu & Profitability: quantity, sales, food cost and margin by item/category.
Label every page 'SIMULATED DATA — independent portfolio project'.
Report findings as patterns in this simulated dataset, never as actual company performance. Customer discounts are not applied; staff meals use user-supplied prices where available and estimated discounts elsewhere. No causal conclusions about pricing or promotions can be drawn.
""")
# Include the exact generator for reproducibility.
import shutil
shutil.copyfile(__file__,OUT/"generate.py")
shutil.copyfile(ROOT/"operations_extras.py",OUT/"operations_extras.py")
shutil.copyfile(ROOT/"staff_meals.py",OUT/"staff_meals.py")
archive=ROOT.parent/"Nandos_Mauritius_Simulated_Project.zip"
with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
    for f in sorted(OUT.iterdir()): z.write(f,OUT.name+"/"+f.name)
print(json.dumps(summary))
print(archive)
