"""JobPulse dashboard. Run: streamlit run streamlit_app.py"""
import sqlite3
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "jobpulse.db"

# Single-series charts use one hue; light/dark steps of the same blue.
BAR_LIGHT, BAR_DARK = "#2a78d6", "#3987e5"

st.set_page_config(page_title="JobPulse", page_icon="📈", layout="wide")


@st.cache_data(ttl=3600)
def load() -> dict[str, pd.DataFrame]:
    conn = sqlite3.connect(DB_PATH)
    rankings = pd.read_sql("SELECT * FROM rankings", conn)
    postings = pd.read_sql(
        """SELECT source, remote, location,
                  substr(COALESCE(posted_at, ingested_at), 1, 7) AS month
           FROM raw_postings""",
        conn,
    )
    conn.close()
    return {"rankings": rankings, "postings": postings}


def bar_color() -> str:
    return BAR_DARK if st.get_option("theme.base") == "dark" else BAR_LIGHT


def ranking_chart(df: pd.DataFrame, value_title: str) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=4, height=18, color=bar_color())
        .encode(
            x=alt.X("postings:Q", title=value_title, axis=alt.Axis(grid=True, tickMinStep=1)),
            y=alt.Y("skill:N", sort="-x", title=None),
            tooltip=[
                alt.Tooltip("skill:N", title="Skill"),
                alt.Tooltip("postings:Q", title="Postings"),
            ],
        )
        .properties(height=max(220, 26 * len(df)))
    )


def show_ranking(rankings: pd.DataFrame, month: str, category: str, value_title: str) -> None:
    df = (
        rankings.query("month == @month and category == @category")
        .nsmallest(15, "rank")
        .sort_values("rank")
    )
    if df.empty:
        st.info("No data for this month yet.")
        return
    st.altair_chart(ranking_chart(df, value_title), use_container_width=True)
    with st.expander("View as table"):
        st.dataframe(
            df[["rank", "skill", "postings"]].set_index("rank"),
            use_container_width=True,
        )


data = load()
rankings, postings = data["rankings"], data["postings"]

st.title("📈 JobPulse")
st.caption(
    "What the job market is asking for — live postings from Remotive, RemoteOK, "
    "Arbeitnow and Adzuna (6 countries), refreshed weekly."
)

months = sorted(rankings["month"].unique(), reverse=True)
month = st.selectbox("Month", months, index=0)

month_postings = postings[postings["month"] == month]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Postings analyzed", f"{len(month_postings):,}")
c2.metric("Data sources", month_postings["source"].nunique())
remote_share = month_postings["remote"].mean() * 100 if len(month_postings) else 0
c3.metric("Remote share", f"{remote_share:.0f}%")
c4.metric("All-time postings", f"{len(postings):,}")

tab_tech, tab_lang, tab_domain, tab_soft, tab_remote = st.tabs(
    ["🛠 Technologies", "💻 Programming languages", "🏢 Domains & roles", "🤝 Soft skills", "🌍 Remote jobs"]
)

with tab_tech:
    st.subheader(f"Top technologies — {month}")
    show_ranking(rankings, month, "technology", "Postings mentioning it")

with tab_lang:
    st.subheader(f"Top programming languages — {month}")
    show_ranking(rankings, month, "programming_language", "Postings mentioning it")

with tab_domain:
    st.subheader(f"Top domains & role areas — {month}")
    show_ranking(rankings, month, "domain", "Postings mentioning it")

with tab_soft:
    st.subheader(f"Top soft skills — {month}")
    show_ranking(rankings, month, "soft_skill", "Postings mentioning it")

with tab_remote:
    st.subheader(f"Remote hiring — {month}")
    remote = month_postings[month_postings["remote"] == 1]
    if remote.empty:
        st.info("No remote postings for this month yet.")
    else:
        st.write(
            f"**{len(remote):,}** of {len(month_postings):,} postings this month "
            f"are remote ({remote_share:.0f}%)."
        )
        loc = (
            remote["location"]
            .fillna("Unspecified")
            .str.strip()
            .replace("", "Unspecified")
            .value_counts()
            .head(15)
            .rename_axis("skill")          # reuse ranking_chart's column names
            .reset_index(name="postings")
        )
        st.caption("Top locations/regions remote postings are open to")
        st.altair_chart(
            ranking_chart(loc, "Remote postings"), use_container_width=True
        )
        with st.expander("View as table"):
            st.dataframe(loc.set_index("skill"), use_container_width=True)

st.divider()
st.caption(
    "Data: free public job APIs, ingested weekly by GitHub Actions. "
    "Extraction: rule-based skill matching (spaCy EntityRuler) — trained NER model coming next. "
    "Built as a $0-budget learning project."
)
