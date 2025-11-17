## 🟢 EASY LEVEL - Basic Queries

### Ultra-Short Queries (NEW SOTA Feature!)
1. "Boiler kwh" ⭐ **Test short-form parsing**
2. "HVAC watts" ⭐ **Test unit recognition**
3. "Compressor power" ⭐ **Test 2-word queries**
4. "top 3" ⭐ **Test heuristic disambiguation**
5. "top 5 machines" ⭐ **Test ranking queries**

### Energy Consumption Queries
6. "What's the power consumption of Compressor-1?"
7. "How much energy did Boiler-1 use?"
8. "Show me Conveyor-A energy"
9. "What about HVAC-EU-North power?"
10. "Compressor-EU-1 consumption"
11. "Compressor-1 kwh" ⭐ **Test machine+unit format**
12. "total kwh" ⭐ **Test factory-wide short query**

### Machine Status Queries (Enhanced with Rich Responses!)
13. "Is Boiler-1 running?"
14. "What's the status of Compressor-1?"
15. "Check HVAC-EU-North"
16. "Is Boiler-1 online?" ⭐ **Test online/offline keywords**
17. "Compressor-1 availability" ⭐ **Test availability queries**
18. "Is Boiler-1 online and what's its power?" ⭐ **Test multi-part**

### Anomaly Detection & Historical Analysis
73. "Were there any anomalies for Boiler-1 yesterday?" ⭐ **Rich: time ago + severity**
74. "Show me all machines with high temperature alerts in the last 24 hours" ⭐ **Test filtering**
75. "What's the anomaly trend for Compressor-1 in the last week?" ⭐ **Rich: trend analysis**
76. "Which machines have had the most anomalies this month?" ⭐ **Test ranking by anomalies**
77. "Show me the top 3 machines with critical anomalies" ⭐ **Test severity + ranking**

---

## 🟡 MEDIUM LEVEL - Time-Based Queries

### Energy with Duration (Now with Rich Responses!)
25. "How much energy did Compressor-1 use in the last 24 hours?" ⭐ **Rich: timestamps, peaks**
26. "Boiler-1 consumption yesterday"
27. "Show me Conveyor-A energy last week"
28. "hourly energy for Boiler-1" ⭐ **Test implicit duration**
29. "daily usage Compressor-1" ⭐ **Test implicit daily**
30. "Show me Compressor-1 daily usage" ⭐ **Test natural phrasing**
31. "weekly energy" ⭐ **Test short temporal**
32. "monthly consumption" ⭐ **Test monthly queries**

### Comparisons
33. "Compare Compressor-1 and Boiler-1"
34. "Compare Conveyor-A and HVAC-EU-North"
35. "Boiler vs Compressor" ⭐ **Test short comparison**
36. "Compare energy usage of Boiler-1 and Conveyor-A"
37. "Compressor-1 vs Boiler-1 efficiency"

### Cost Analysis
38. "What's the energy cost today?"
39. "Cost analysis for this month"
40. "cost?" ⭐ **Test ultra-short cost query**
41. "How much did we spend on energy this week?"
42. "Energy cost for Compressor-1"

---

## 🔴 CHALLENGE LEVEL - Complex Queries

### Multi-Entity Queries with Rich Responses
68. "Show me the energy consumption of Compressor-1 from October 27, 3 PM to October 28, 10 AM" ⭐ **Rich: timestamps + totals**
69. "How much energy did all machines use this month?" ⭐ **Test factory aggregation**
70. "What's the hourly energy consumption for Boiler-1 in the last 48 hours?" ⭐ **Rich: hourly breakdown**
71. "Compare energy consumption of Boiler-1 vs Compressor-1 in the last week" ⭐ **Rich: comparison with %**
72. "What's the average energy consumption of Boiler-1 during peak hours (8 AM to 6 PM) for the last 3 days?" ⭐ **Complex temporal**

### Factory-Wide Queries (Now with OVOS Endpoints!)
56. "show me factory overview" ⭐ **Uses /ovos/summary**
57. "total factory consumption" ⭐ **Test factory-wide**
58. "factory status" ⭐ **Rich response with insights**
59. "Give me a complete factory overview" ⭐ **Test verbose**

### Top Consumers (NEW - Fixed with Heuristics!)
60. "top 3" ⭐ **CRITICAL: Heuristic override**
61. "top 5" ⭐ **Test ranking**
62. "top 10 machines" ⭐ **Test with context**
63. "highest 3" ⭐ **Test alternative phrasing**
64. "show top 3" ⭐ **Test with action verb**
65. "which machine uses most energy?" ⭐ **Test natural**
66. "rank machines by energy" ⭐ **Test explicit ranking**
67. "top consumers" ⭐ **Test without number**

### Anomaly Detection & Historical Analysis
73. "Were there any anomalies for Boiler-1 yesterday?" ⭐ **Rich: time ago + severity**
74. "Show me all machines with high temperature alerts" ⭐ **Test filtering**
75. "What's the anomaly trend for Compressor-1?" ⭐ **Rich: trend analysis**
76. "Which machines have had the most anomalies?" ⭐ **Test ranking**
77. "Any unusual patterns in HVAC-EU-North?" ⭐ **Test natural phrasing**

### Cost Analysis & Production Correlation
78. "What's the energy cost for Boiler-1 this week?" ⭐ **Rich: cost + consumption**
79. "Calculate total factory energy cost" ⭐ **Test factory-wide**
80. "Which machine has highest cost?" ⭐ **Test ranking by cost**
81. "Show me production metrics for Compressor-1" ⭐ **Test production data**
82. "What's the efficiency of Boiler-1?" ⭐ **Test efficiency**

### Forecasting & Predictions
83. "Forecast energy consumption for Compressor-1 tomorrow" ⭐ **Test forecasting**
84. "What's the predicted energy usage for Boiler-1 next week?" ⭐ **Test prediction**
85. "Show me energy forecast for the next 7 days" ⭐ **Test multi-day**
86. "Predict Conveyor-A power consumption" ⭐ **Test natural**
87. "Energy forecast for HVAC-EU-North" ⭐ **Test short form**

### Baseline & Comparative Analysis
88. "Check baseline status for Compressor-1" ⭐ **Test baseline**
89. "Is Boiler-1 baseline trained?" ⭐ **Test status check**
90. "Compare Conveyor-A actual vs baseline" ⭐ **Test comparison**
91. "Show me anomalies for Compressor-1 in the last week" ⭐ **Rich: weekly view**
92. "Any unusual patterns detected?" ⭐ **Test general anomaly**

---

## 🎯 EDGE CASES & STRESS TESTS

### Ultra-Short Ambiguous Queries (Heuristic Tests)
93. "3" ⭐ **Should ask for clarification**
94. "watts" ⭐ **Should ask which machine**
95. "top" ⭐ **Should ask top what**
96. "energy" ⭐ **Should ask which machine/scope**
97. "status" ⭐ **Should ask which machine**

### Ambiguous Natural Queries
98. "How's everything?" ⭐ **Should trigger factory_overview**
99. "Show me data" ⭐ **Should ask what kind**
100. "What's happening?" ⭐ **Should trigger factory_overview or anomalies**
101. "Tell me about the machines" ⭐ **Should trigger factory_overview**

### Typos & Name Variations
102. "Compressor 1 power" ⭐ **Test space handling**
103. "boiler1 consumption" ⭐ **Test no space**
104. "HVAC EU North energy" ⭐ **Test hyphen variations**
105. "conveyer A status" ⭐ **Test misspelling**
106. "Compressor EU 1 power" ⭐ **Test extra space**

### Wrong Machine Names
107. "What about Machine-99?" ⭐ **Should say not found**
108. "Show me Pump-A energy" ⭐ **Should say not found**
109. "Turbine-1 status" ⭐ **Should say not found**
110. "Generator-5 consumption" ⭐ **Should say not found**

### Invalid/Edge Time Ranges
111. "Show me energy from last year" ⭐ **Should handle gracefully**
112. "Energy consumption in 2020" ⭐ **Should say no data**
113. "Show me data from tomorrow" ⭐ **Should say not available yet**

### Mixed Intent Queries (Multi-Part)
114. "Show me Compressor-1 energy and compare it with Boiler-1" ⭐ **Test dual intent**
115. "What's the status and energy cost of HVAC-EU-North?" ⭐ **Test multi-part**
116. "Compare machines and show anomalies" ⭐ **Test chaining**
117. "Factory overview and top consumers" ⭐ **Test combined**
118. "Is Boiler-1 online and what's its power?" ⭐ **Test multi-question**
