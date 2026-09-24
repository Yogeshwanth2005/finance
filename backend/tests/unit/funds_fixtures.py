"""A small AMFI NAVAll.txt lookalike: real layout (header row, category lines, fund-house lines, semicolon rows), invented schemes."""

NAVALL_SAMPLE = """Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date

Open Ended Schemes(Equity Scheme - Large Cap Fund)

Alpha Mutual Fund

100001;INF000A01001;-;Alpha Bluechip Fund;Direct Plan;Growth Option;150.1000;23-Sep-2026
100002;INF000A01002;-;Alpha Bluechip Fund;Regular Plan;Growth Option;140.0000;23-Sep-2026
100003;INF000A01003;-;Alpha Bluechip Fund;Direct Plan;IDCW Option;120.0000;23-Sep-2026
100004;INF000A01004;-;Alpha Dormant Large Cap Fund;Direct Plan;Growth Option;90.0000;01-Jun-2026

Beta Mutual Fund

100005;INF000B01005;-;Beta Investor’s Large Cap Fund;Direct Plan;Growth Option;88.5000;23-Sep-2026

Open Ended Schemes(Equity Scheme - Large & Mid Cap Fund)

Alpha Mutual Fund

100010;INF000A01010;-;Alpha Large & Mid Cap Fund;Direct Plan;Growth Option;55.0000;23-Sep-2026

Open Ended Schemes(Equity Schemes - Mid Cap Fund)

Beta Mutual Fund

200001;INF000B02001;-;Beta Midcap Fund;Direct Plan;Growth Option;N.A.;23-Sep-2026
200002;INF000B02002;-;Beta Mid Opportunities Fund;Direct Plan;Growth Option;75.5000;22-Sep-2026

Open Ended Schemes(Equity Scheme - Small Cap Fund)

Beta Mutual Fund

300001;INF000B03001;-;Beta Small Cap Fund;Direct Plan;Growth Option;210.0000;23-Sep-2026

Open Ended Schemes(Other Scheme - Index Funds)

Alpha Mutual Fund

400001;INF000A04001;-;Alpha Nifty 50 Index Fund;Direct Plan;Growth Option;30.0000;23-Sep-2026
400002;INF000A04002;-;Alpha Nifty Next 50 Index Fund;Direct Plan;Growth Option;28.0000;23-Sep-2026
400003;INF000A04003;-;Alpha Nifty 500 Index Fund;Direct Plan;Growth Option;27.0000;23-Sep-2026
400004;INF000A04004;-;Alpha Nifty 50 Equal Weight Index Fund;Direct Plan;Growth Option;26.0000;23-Sep-2026
400005;INF000A04005;-;Alpha Nifty50 Value 20 Index Fund;Direct Plan;Growth Option;25.0000;23-Sep-2026
400006;INF000A04006;-;Alpha Sensex Index Fund;Direct Plan;Growth Option;24.0000;23-Sep-2026

Close Ended Schemes(Growth)

Gamma Mutual Fund

500001;INF000G05001;-;Gamma Fixed Term Large Cap Fund;Direct Plan;Growth Option;10.0000;23-Sep-2026
"""

# every scheme of NAVALL_SAMPLE that is Direct + Growth, has a numeric NAV and is live against the file's newest date
NAVALL_LIVE_CODES = {"100001", "100005", "100010", "200002", "300001", "400001", "400002", "400003", "400004", "400005", "400006", "500001"}

# AMFI's dated NAV report as it really comes: another column order than NAVAll.txt, category lines with spaces inside the
# parentheses, empty plan and option columns on some rows. The last three rows are ones the parser must drop.
NAV_REPORT_SAMPLE = """Scheme Code;NAV Name;Plan;Option;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Net Asset Value;Date

Open Ended Schemes ( Money Market )


Taurus Mutual Fund
139619;Taurus Investor Education Pool - Unclaimed Dividend - Growth;;;;;10.0000;15-Sep-2026
139617;Taurus Unclaimed Redemption - Growth;;Growth;;;17.7597;15-Sep-2026

Open Ended Schemes ( Equity Scheme - Multi Cap Fund )


Aditya Birla Sun Life Mutual Fund
148921;Aditya Birla Sun Life Multi-Cap Fund-Direct Growth;Direct Plan;GROWTH;INF209KB1Y49;;22.43;15-Sep-2026
148921;Aditya Birla Sun Life Multi-Cap Fund-Direct Growth;Direct Plan;GROWTH;INF209KB1Y49;;22.51;16-Sep-2026
148920;Aditya Birla Sun Life Multi-Cap Fund-Direct IDCW Payout;Direct Plan;IDCW Payout;INF209KB1Y56;;N.A.;15-Sep-2026
148919;Aditya Birla Sun Life Multi-Cap Fund-Regular-IDCW Payout;Regular Plan;IDCW Payout;INF209KB1Y31;;0.0000;15-Sep-2026
153309;BAJAJ FINSERV MULTI CAP FUND - DIRECT - GROWTH;Direct Plan;Growth;INF0QA701AV7;;12.267;not a date
"""
