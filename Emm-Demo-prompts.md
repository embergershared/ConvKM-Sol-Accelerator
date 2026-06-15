# Dashboard demo


## Link to access Web app

[Customer Calls Sentiment Analysis dashboard](https://app-iter01l2yhy.azurewebsites.net)


## Chat prompts

`Show average handling time by topics in minutes, sorted by the longest to the shortest.`


`Generate a lines chart of the count of conversations by sentiment per day for the last 7 days.`


`What are top 3 challenges user reported.`
    # => This one gives some conversations transcripts links

`Create a bar chart of these challenges conversations per day for the last 7 days.`


`Give a summary of billing issues.`
    # => This one gives some conversations transcripts links


`When customers call in about unusual charges, what types of charges are they seeing?`
    # => This one gives some conversations transcripts links


`Turn these key topics into a structured FAQ to be used by the call center representatives.`


## Dashboard drill-down walkthrough

The four interactive widgets on the dashboard each open a drill drawer. Use this for a "see a KPI → see the trend → see the calls → read the transcript" demo, all without leaving the dashboard.

1. **Pick an anomaly from any widget:**
   - **Sentiment donut** → click the **Negative** slice
   - **Avg Handling Time by Topic bar** → click the **Billing Issues** bar
   - **Trending Topics table** → click a row, e.g. **Billing Issues**
   - **Key Phrases word cloud** → click a phrase, e.g. **account number**
2. **L1 — Time trend.** Drawer slides in from the right. Toggle **Day / Week**, hover any bar to see exact `calls`, `avg sentiment`, `satisfied %`, and `avg handle time`. Drag the **left edge of the drawer** to resize it (preference is remembered in `localStorage`).
3. **L2 — Call list.** Click any bar in the trend chart. A paginated list (25/page) of conversations in that bucket appears with sentiment / satisfied / topic / complaint chips and a summary excerpt.
4. **L3 — Transcript.** Click any row. Header chips (start, duration, sentiment, satisfied, topic, complaint, key phrases) over the AI **Summary** and the raw **Transcript**.
5. **Navigate back:** **Esc** pops one level, the **back arrow** in the header pops one level, breadcrumb items jump to that depth, **Reset drill** wipes the stack, **X** closes the drawer.
6. **Share a view:** while the drawer is open, copy the URL — it carries `#/drill/topic=Billing&bucket=week&from=...&to=...&call=...`. Paste into a colleague's chat and they land on the exact same drilled view.
7. **Keyboard:** every chart mark is `role="button"` + `tabindex=0`; **Tab** to focus, **Enter** or **Space** to open the drawer.


# Show the costs management portal Grafana
[Foundry Grafana dashboard](https://portal.azure.com/#view/Microsoft_Azure_Monitoring/AzureGrafana.ReactView/GalleryType/Azure%20Monitor/ConfigurationId/AIFoundry/QueryParams/%7B%22var-sub%22%3A%224c88693f-5cc9-4f30-9d1e-d58d4221cf25%22%2C%22var-rg%22%3A%22rg-swc-s3-sc-ccanalysis-iter-01%22%2C%22var-res%22%3A%22aif-iter01l2yhy%22%2C%22from%22%3A%222026-06-06T03%3A16%3A25.280Z%22%2C%22to%22%3A%222026-06-07T03%3A16%3A25.280Z%22%7D)


