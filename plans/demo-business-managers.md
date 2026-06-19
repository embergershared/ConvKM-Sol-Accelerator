# Demo Script: Conversation Knowledge Mining for Business Managers

**Target audience:** Business managers of the call center (electrical power utility)
**Duration:** 15–20 minutes
**Format:** Screen recording, narrated live
**Environment:** `https://app-iter02n7y67.azurewebsites.net`
**Key message:** *AI turns thousands of call transcripts into actionable insights in seconds.*

---

## Before You Record — Checklist

- [ ] Open the app URL in a clean browser window (incognito recommended — no bookmarks bar)
- [ ] Zoom browser to 100% (Ctrl+0), full-screen the browser (F11)
- [ ] Clear any existing chat history (click the "New conversation" button once)
- [ ] Make sure the dashboard loads all 7 widgets without errors
- [ ] Test the drill-down drawer opens correctly on one widget click
- [ ] Start your screen recording tool (OBS, PowerPoint Record, Windows Game Bar)
- [ ] Have this script open on a second monitor or printed

---

## Step 1 — Opening & Context Setting (1–2 min)

### What to show
Open the app. The dashboard should be fully loaded with all widgets visible.

### What to say
> "Hello, I'm going to show you a solution we've built that turns thousands of customer call transcripts into actionable insights — in seconds, not days."
>
> "Imagine you're a call center manager at a power utility. You get hundreds, sometimes thousands of calls per day. Customers call about billing issues, service outages, account changes. The question is: how do you spot trends, identify problems, and act — before they become bigger issues?"
>
> "This solution uses Microsoft AI to automatically analyze every conversation, in both transcript and audi file formats to surface the patterns of interest."

### Key points
- **Pain point:** Manual review of call transcripts is slow and misses patterns
- **Value prop:** AI processes ALL calls, not a sample, and surfaces trends automatically
- **Technology:** Built on Microsoft Azure AI Foundry — enterprise-grade, secure, in your cloud

---

## Step 2 — Dashboard Overview: KPIs at a Glance (2–3 min)

### What to show
Point out each of the 7 dashboard widgets, pausing on each:
1. **Total Calls** card — total volume of analyzed conversations
2. **Average Handle Time** card — avg call duration
3. **Satisfied %** card — customer satisfaction rate
4. **Sentiment Donut** — positive/neutral/negative breakdown
5. **Average Handling Time by Topic** — horizontal bar chart
6. **Trending Topics** — table of top topics by volume, predetermined
7. **Key Phrases** — word cloud of frequently mentioned terms during the calls

### What to say
> "When you first land on the dashboard, you get the big picture — instantly."
>
> "You have the call volume, average handle time, and satisfaction rate. These are the headline KPIs."
>
> "The sentiment donut breaks down how customers are feeling — positive, neutral, or negative. You can immediately see if there's a spike in negative sentiment."
>
> "The topics are predetermined and are specifically searched for during the analysis."
>
> "The topics bar chart shows what people are calling about and how long those calls take. If 'Billing Issues' suddenly has the longest handle time, that's a signal worth investigating."
>
> "The Key Phrases word cloud gives you the exact language customers are using — 'account number,' 'unusual charges,' 'service outage.' These are the words your agents hear every day, now visible at a glance. Their color reflects the sentiment associated with the call they are said."

### Key points
- **No manual work:** These insights are generated automatically from every call, whatever their input format
- **Real-time awareness:** Managers see the current state without waiting for weekly reports
- **Pattern detection:** Spot anomalies (sentiment spikes, new topics) the moment they appear

---

## Step 3 — Dashboard Filters (1 min)

### What to show
Click on the filter controls. Show how you can filter by:
- Date range
- Sentiment
- Topic
- With recording

Apply a filter (e.g., filter to "Negative" sentiment only) and show the dashboard updating.

### What to say
> "You can slice and dice the data using these filters. Let me filter to negative sentiment only."
>
> "Now every chart updates to show only the calls where customers were unhappy. This is how you zoom into problem areas."

### Key points
- **Self-service analytics:** Managers don't need to ask an analyst — they filter themselves
- **Interactive:** Every filter instantly updates all widgets

---

## Step 4 — Drill-Down: From KPI to Individual Call (3–4 min)

### What to show
This is the "wow moment." Walk through the 3-level drill:

1. **L1 — Click the "Negative" slice** on the Sentiment donut
   - The drill drawer slides in from the right
   - Show the time trend chart (bars = call volume, line = sentiment over time)
   - Point out the Day/Week toggle
   - Hover over a bar to show the tooltip (calls count, avg sentiment, satisfied %, avg handle time)

2. **L2 — Click a bar** (pick a day with high negative volume)
   - The call list appears — paginated grid of individual conversations
   - Point out the sentiment chips, topic tags, and summary excerpts

3. **L3 — Click a call row**
   - The full transcript opens with header chips (start time, duration, sentiment, topic, complaint flag, key phrases)
   - Show the AI-generated summary at the top
   - Show the raw transcript below

4. **Navigate back** — use the breadcrumb, back arrow, or Esc key to pop levels

### What to say
> "Now here's where it gets really powerful. I see that negative sentiment is elevated. Let me click on the negative slice to investigate."
>
> "A panel opens showing me the trend over time. I can see exactly which days had the most negative calls. Let me hover here — this day had 15 negative calls with an average satisfaction of only 20%."
>
> "Let me click on that day to see the actual calls."
>
> "Now I have a list of every conversation from that day. I can see sentiment, topic, whether the customer was satisfied, and a quick summary. Let me click into this one."
>
> "Here's the full transcript. At the top I get the AI-generated summary, the key phrases, and the complaint classification. Below is the actual conversation. In three clicks, I went from a high-level KPI to reading the exact words a customer said."
>
> "I can navigate back using this breadcrumb, the back arrow, or just press Escape."

### Key points
- **3-click root cause analysis:** KPI → trend → call list → transcript
- **No separate tools needed:** Everything is in one place, one interface
- **AI summarization:** The summary at the top saves you from reading the entire transcript
- **Evidence-based decisions:** You're not guessing — you're reading the actual conversations

---

## Step 5 — Shareable Drill Link (30 sec)

### What to show
While the drill drawer is open at any level, copy the browser URL. Show that the URL contains the drill state (hash fragment).

### What to say
> "One more thing about the drill-down. Notice the URL has updated. If I copy this link and send it to a colleague, they'll land on the exact same view I'm looking at. No need to explain how to get there — they see what I see."

### Key points
- **Collaboration:** Share specific findings via URL — works in Teams, email, Slack
- **Reproducible:** The exact drill state is encoded in the link

---

## Step 6 — AI Chat: Ask Questions in Natural Language (4–5 min)

### What to show
Close the drill drawer. Move to the Chat panel. Enter these prompts one by one, pausing to show each result:

**Prompt 1 — Data analysis:**
```
Show average handling time by topics in minutes, sorted by the longest to the shortest.
```
*Wait for response. Point out the structured answer.*

**Prompt 2 — Chart generation:**
```
Generate a lines chart of the count of conversations by sentiment per day for the last 7 days.
```
*Wait for the chart to render inline. This is the "wow" moment for AI capabilities.*

Switch model: grok then gpt

**Prompt 3 — Insight discovery with citations:**
```
What are top 3 challenges user reported?
```
*Wait for response. Click on a citation chip to show the source conversation.*

**Prompt 4 — Visual follow-up:**
```
Create a bar chart of these challenges conversations per day for the last 7 days.
```
*Show the follow-up chart building on context from the previous question.*

**Prompt 5 — Summarization:**
```
Give a summary of Billing Issues.
```
*Show how it synthesizes across multiple conversations. Click a citation.*

**Prompt 6 — Deep investigation:**
```
When customers call in about unusual charges, what types of charges are they seeing?
```
*Show the detailed breakdown with source citations.*

**Prompt 7 — Actionable output:**
```
Turn these key topics into a structured FAQ to be used by the call center representatives.
```
*Show the generated FAQ — this is the "from insight to action" moment.*

### What to say
> "Beyond the dashboard, you can ask the AI any question about your call data using plain English."
>
> *(After Prompt 1)* "I asked for average handling time by topic. It queried the data and gave me a sorted breakdown — no SQL, no pivot tables, just a question."
>
> *(After Prompt 2)* "Now I asked it to generate a chart. The AI created a line chart showing sentiment trends over the past week — right here in the conversation."
>
> *(After Prompt 3)* "Here's something powerful. I asked for the top challenges customers reported. It analyzed the conversations and identified three main themes. See these clickable chips? Each one links to the actual conversation the AI used as evidence. You can verify every answer."
>
> *(After Prompt 5)* "I asked for a summary of billing issues. The AI synthesized insights across dozens of conversations into one concise summary. Again, every claim is backed by a source you can click."
>
> *(After Prompt 7)* "Now watch this. I asked the AI to turn these topics into a structured FAQ for our call center reps. It generated a ready-to-use FAQ document — directly from the actual customer conversations. This is how AI turns raw data into actionable material your team can use tomorrow."

### Key points
- **Natural language:** No training needed — ask questions like you'd ask an analyst
- **Chart generation:** AI creates visualizations on demand — line charts, bar charts
- **Grounded in data:** Every answer cites specific conversations (clickable citations)
- **Contextual follow-up:** The AI remembers previous questions in the conversation
- **From insight to action:** Go from "what are the problems" to "here's the FAQ for reps" in minutes

---

## Step 7 — Citations: Trust & Verification (1 min)

### What to show
Click on one of the citation chips from a previous chat response. Show the citation panel that opens with the source conversation details.

### What to say
> "I want to highlight one more thing about trust. Every answer the AI gives you includes citations — these numbered chips. Click one, and it shows you the exact conversation the AI referenced."
>
> "This is critical for business decisions. You're not just trusting the AI blindly — you can verify every insight against the original data. The AI shows its work."

### Key points
- **Transparency:** AI shows its sources — builds trust with business stakeholders
- **Auditability:** Every insight is traceable to specific conversations
- **Responsible AI:** The footer reminds users that AI-generated content should be reviewed

---

## Step 8 — Closing: The Business Impact (1 min)

### What to say
> "Let me recap what we saw during these 20 minutes:"
>
> "We looked at hundreds of calls through the dashboard, spotted a negative sentiment trend, drilled down to the specific calls causing it, read the actual transcripts, listen to the calls recording, asked the AI to find patterns, generate charts on the fly, and create a ready-to-use FAQ for our agents."
>
> "Without this solution, that workflow would take an analyst days — pulling data, building reports, reading transcripts manually. With AI, it takes minutes."
>
> "This is what AI turns hundreds of call transcripts into actionable insights in seconds looks like in practice."
>
> "The solution runs entirely in your Azure environment — your data stays in your cloud, secured by your policies. And because it's built on Microsoft AI Foundry, it scales with your call volume."

### Key points
- **Time savings:** Days → minutes for insight generation
- **Self-service:** Managers explore data themselves, no analyst dependency
- **Enterprise-ready:** Azure-hosted, secure, scalable
- **Actionable:** From raw data to FAQs, training materials, and trend reports

---

## Appendix: Troubleshooting During Recording

| Issue | Fix |
|---|---|
| Dashboard doesn't load | Refresh the page; check browser console for API errors |
| Chat response is slow | Wait patiently — streaming takes 10-30s for complex queries. Comment: "The AI is analyzing the data right now" |
| Chart doesn't render in chat | Try a simpler prompt: "Create a bar chart of calls by sentiment" |
| Drill drawer doesn't open | Make sure you click directly on a chart element (slice, bar, row, word) |
| Citation panel is empty | The citation may reference a conversation that wasn't indexed. Move to the next one |
| "AI-generated content may be incorrect" tag visible | Leave it — it shows responsible AI practices. Mention it positively |

---

## Appendix: Timing Guide

| Step | Topic | Target Time | Running Total |
|---|---|---|---|
| 1 | Opening & Context | 1–2 min | 2 min |
| 2 | Dashboard KPIs | 2–3 min | 5 min |
| 3 | Filters | 1 min | 6 min |
| 4 | Drill-Down (3 levels) | 3–4 min | 10 min |
| 5 | Shareable Link | 30 sec | 10.5 min |
| 6 | AI Chat (7 prompts) | 4–5 min | 15.5 min |
| 7 | Citations | 1 min | 16.5 min |
| 8 | Closing | 1 min | 17.5 min |
