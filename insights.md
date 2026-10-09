# Insights (computed from cleaned data)
Revenue basis: Delivered orders only (3,316 of 4,944 clean orders). Cancelled/Returned orders keep a `revenue` value in the CSV but are excluded from sales totals.

## Q1 Top 5 categories
category
Electronics       ₹4,306,437
Home & Kitchen    ₹3,273,186
Clothing          ₹2,157,533
Beauty              ₹891,605
Books               ₹475,472
Insight: Electronics earns 39% of revenue; the top two categories together earn 68%.
(After cleaning only 5 categories exist, so the top 5 is all of them.)

## Q2 Monthly revenue
order_date
2025-01-01      ₹707,038
2025-02-01      ₹777,024
2025-03-01      ₹772,163
2025-04-01      ₹889,772
2025-05-01      ₹898,651
2025-06-01      ₹776,206
2025-07-01      ₹794,124
2025-08-01      ₹820,693
2025-09-01      ₹726,723
2025-10-01    ₹1,416,280
2025-11-01    ₹1,139,896
2025-12-01    ₹1,385,662
Freq: MS
Insight: Oct-Dec average ₹1.31M/month vs ₹0.80M for Jan-Sep (+65%); peak month Oct.

## Q3 Top 3 cities
city
Mumbai       ₹2,211,005
Delhi        ₹1,983,959
Bengaluru    ₹1,937,353

## Bonus: discount vs no-discount orders
Mean revenue per discounted order ₹3,109 vs ₹3,631 for undiscounted (Welch t-test p=0.000). Caution: this gap is mostly product mix (discount is spread across cheap and expensive items), not proof that discounts lower spend.
Share of orders Cancelled/Returned by category: Home & Kitchen 34%, Beauty 33%, Books 33%, Clothing 33%, Electronics 33%.
