# Nando’s Mauritius Analytics

A restaurant analytics portfolio project inspired by my experience in restaurant service at Nando’s Mauritius. The report uses simulated 2025 data.

![Power BI Sales Overview showing sales trends, branch performance, and order channels](sales-overview.png)

## Dashboard pages

| Page | What it shows |
| --- | --- |
| [Sales Overview](sales-overview.png) | Customer sales, order volume, average order value, refunds, and sales trends |
| [Operations](operations.png) | Cancelled and voided orders, plus wrong-order waste costs by branch and reason |
| [Upselling](upselling.png) | Waiter upsell sales by extra |
| [Staff Meals](staff-meals.png) | Staff meal receipts, discounts by branch, and monthly order counts |

## How it works

Python generates and prepares the simulated restaurant data. MySQL stores the data in relational tables. Power BI connects the tables, calculates reporting metrics, and presents them across four report pages.

[Download the simulated dataset and project scripts](Nandos_Mauritius_Simulated_Project.zip)


## View the report

Open [Nandos_Mauritius_Dashboard.pbix](Nandos_Mauritius_Dashboard.pbix) in Power BI Desktop or use the screenshots above to preview each page.

This is an independent portfolio project built with simulated data.
