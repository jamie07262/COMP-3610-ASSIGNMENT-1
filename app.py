from urllib.request import urlretrieve
from pathlib import Path
import streamlit as st
import polars as pl
import pandas as pd
import plotly.express as px
from polars import lit


st.set_page_config(page_title="NYC Yellow Taxi Data Dashboard", layout="wide")

st.title("NYC Yellow Taxi Data Dashboard")
st.markdown("""
This dashboard provides insights into NYC Yellow Taxi trips patterns, including top 10 busiest pickup zones, fare patterns, payment types, tip behavior, and popular pickup-dropoff pairs. Use the side navigation to explore different aspects of the data.
""")

@st.cache_data
def load_data():
    # Ensure files are downloaded before loading
    raw_dir = Path("data/raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    files = [
        ("https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet", raw_dir/"yellow_taxi_data.parquet"),
        ("https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv", raw_dir/"taxi_zone_lookup.csv"),
    ]
    for url, filename in files:
        if not filename.exists():
            try:
                urlretrieve(url, filename)
            except Exception as e:
                st.error(f"Failed to download {filename.name}: {e}")
                st.stop()
                
    """
    Load the taxi data and do some basic prep work using polars.
    """
    expected_result = [
        "tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID",
        "passenger_count", "trip_distance", "fare_amount", "tip_amount", "total_amount", "payment_type"
    ]
    try:
        df = pl.read_parquet('data/raw/yellow_taxi_data.parquet')
    except FileNotFoundError:
        st.error("Can't find the dataset! Download failed or file missing.")
        st.stop()

    # Validate columns and types
    missing = [m for m in expected_result if m not in df.columns]
    if missing:
        st.error(f"Missing expected columns: {missing}")
        st.stop()
    if df.schema.get("tpep_pickup_datetime") != pl.Datetime:
        st.error(f"tpep_pickup_datetime is {df.schema.get('tpep_pickup_datetime')}, expected Datetime")
        st.stop()
    if df.schema.get("tpep_dropoff_datetime") != pl.Datetime:
        st.error(f"tpep_dropoff_datetime is {df.schema.get('tpep_dropoff_datetime')}, expected Datetime")
        st.stop()

    # using sample size of 100k to clean for visualization on streamlit
    if df.height > 100000:
        df = df.sample(n=100000, seed=42)

    # Remove nulls
    df = df.drop_nulls()

    #filtering invalid trips: trips with zero or negative distance, negative fares, or fares exceeding $500
    df = (
        df.filter((pl.col("fare_amount") > 0) & (pl.col("fare_amount") <= 500))
          .filter(pl.col("trip_distance") > 0)
    )

    #removing trips where dropoff time is before pickup time
    df = df.filter(pl.col("tpep_dropoff_datetime") >= pl.col("tpep_pickup_datetime"))

    # Add trip duration in minutes
    df = df.with_columns([
        ((pl.col("tpep_dropoff_datetime") - pl.col("tpep_pickup_datetime")).dt.total_seconds() / 60).alias('trip_duration_minutes'),
    ])

    # Add trip speed
    df = df.with_columns([
        (
            pl.when(pl.col("trip_duration_minutes") > 0)
            .then(pl.col("trip_distance") / (pl.col("trip_duration_minutes") / 60))
            .otherwise(None)
            .alias('trip_speed_mph')
        )
    ])

    # Add pickup hour and weekday
    df = df.with_columns([
        pl.col('tpep_pickup_datetime').dt.hour().alias('pickup_hour'),
        pl.col('tpep_pickup_datetime').dt.weekday().alias('pickup_weekday'),
        pl.col('tpep_pickup_datetime').dt.date().alias('pickup_date')
    ])

    # Add trip_duration_sec and trip_duration_min 
    df = df.with_columns([
        (pl.col('trip_duration_minutes') * 60).alias('trip_duration_sec'),
        pl.col('trip_duration_minutes').alias('trip_duration_min')
    ])

    # Add tip_percentage
    df = df.with_columns([
        (pl.col('tip_amount') / pl.col('fare_amount') * 100).fill_null(0).alias('tip_percentage')
    ])

    return df

df = load_data()

########PAGE NAVIGATION############
page = st.sidebar.selectbox("Navigation", ("Key Metrics", "Visualizations"))

########SIDEBAR FILTERS############
st.sidebar.header("Filters")

# Date range - pretty self-explanatory
st.sidebar.subheader("Date Range")
min_date = pd.to_datetime("2020-12-31").date()
max_date = pd.to_datetime("2024-02-01").date()

date_range = st.sidebar.date_input(
    "Pick your dates:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Handle the annoying case where user only selects one date
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    # If date_range is a numpy array, get the first element
    if hasattr(date_range, '__getitem__'):
        start_date = end_date = date_range[0]
    else:
        start_date = end_date = date_range
start_date = pd.to_datetime(start_date).date()
end_date = pd.to_datetime(end_date).date()

# Hour range slider
st.sidebar.subheader("Hour Range")
hour_min, hour_max = st.sidebar.slider(
    "Hour of Day:",
    min_value=0,
    max_value=23,
    value=(0, 23),
    step=1
)

# Payment type multi-select
st.sidebar.subheader("Payment Type")
payment_map = {1: 'Credit Card', 2: 'Cash', 3: 'No Charge', 4: 'Dispute'}
if 'payment_name' not in df.columns:
    df = df.with_columns([
        pl.when(pl.col('payment_type') == 1).then(lit('Credit Card'))
         .when(pl.col('payment_type') == 2).then(lit('Cash'))
         .when(pl.col('payment_type') == 3).then(lit('No Charge'))
         .when(pl.col('payment_type') == 4).then(lit('Dispute'))
         .otherwise(lit('Other')).alias('payment_name')
    ])
payment_options = list(payment_map.values())
selected_payments = st.sidebar.multiselect(
    "Payment methods:",
    options=payment_options,
    default=payment_options
)

# ============== APPLY FILTERS ==============
filtered_df = df.filter(
    (pl.col('pickup_date') >= pl.lit(start_date)) &
    (pl.col('pickup_date') <= pl.lit(end_date)) &
    (pl.col('pickup_hour') >= hour_min) &
    (pl.col('pickup_hour') <= hour_max) &
    (pl.col('payment_name').is_in(selected_payments))
)

# For pandas/plotly
filtered_pdf = filtered_df.to_pandas()

# Show filtered trip count
st.sidebar.divider()
st.sidebar.metric("Filtered Trips", f"{len(filtered_pdf):,}")
st.sidebar.caption(f"out of {len(df):,} ({len(filtered_pdf)/len(df)*100:.1f}%)")

#########PAGES############

if page == "Key Metrics":
    st.header("Key Metrics")
    
    total_trips = len(df)
    avg_fare = df['fare_amount'].mean()
    total_revenue = df['fare_amount'].sum()
    avg_trip_distance = df['trip_distance'].mean()
    avg_trip_duration = df['trip_duration_min'].mean()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Trips", f"{total_trips:,}")
    col2.metric("Avg Fare", f"${avg_fare:.2f}")
    col3.metric("Total Revenue", f"${total_revenue:,.2f}")
    col4.metric("Avg Trip Distance", f"{avg_trip_distance:.1f} miles")
    col5.metric("Avg Trip Duration", f"{avg_trip_duration:.1f} mins")
  

if page == "Visualizations":
    st.header("Visualizations")
    
    pdf = df.to_pandas()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Top Pickup Zones",
        "Average Fare by Hour",
        "Trip Distance Histogram",
        "Payment Type Breakdown",
        "Trips Heatmap"
    ])


    with tab1:
        st.subheader("Bar chart: Top 10 pickup zones by trip count")
        # Group by PULocationID and count trips
        top_zones = filtered_pdf.groupby('PULocationID').size().reset_index(name='trip_count')
        zone_lookup = pd.read_csv('data/raw/taxi_zone_lookup.csv')
        # Merge to get zone names
        top_zones = top_zones.merge(zone_lookup, left_on='PULocationID', right_on='LocationID', how='left')
        # Sort and select top 10
        top_zones = top_zones.sort_values('trip_count', ascending=False).head(10)
        fig = px.bar(
            top_zones,
            x='Zone',
            y='trip_count',
            title='Top 10 Pickup Zones by Trip Count',
            labels={'Zone': 'Pickup Zone', 'trip_count': 'Trip Count'}
        )
        fig.update_yaxes(dtick=1000)
        fig.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig, width='stretch')
        st.subheader("Insights from Top Pickup Zones")
        st.markdown("""
        Upper East Side South, JFK Airport and Midtown Center are the busiest pickup zones, with a trip count of over 4k. 
        This reflects the high demand for taxis in these areas, especially to and from the airports. As well as tourist hotspots like Times Sq/Theater District and Penn Station.
        """)

    with tab2:
        st.subheader("Line chart: Average fare by hour of day")
        avg_fare_by_hour = filtered_pdf.groupby('pickup_hour')['fare_amount'].mean().reset_index()
        fig = px.line(
            avg_fare_by_hour,
            x='pickup_hour',
            y='fare_amount',
            title='Average Fare by Hour of Day',
            labels={'pickup_hour': 'Hour of Day', 'fare_amount': 'Average Fare ($)'},
            markers=True
        )
        fig.update_traces(hovertemplate='Hour: %{x}<br>Avg Fare: $%{y:.2f}')
        fig.update_layout(xaxis=dict(dtick=1), height=500, hovermode='x unified')
        st.plotly_chart(fig, width='stretch')
        
        st.subheader("Insights from Average Fare by Hour")
        st.markdown("""
        The average fare is highest at early mornings (4am-6am) most likely due to high demand for airport trips or workers commuting to early shifts.
        There is a noticeable dip in the average fare later during the day, which can be due to shorter trips. The fare picks back up during late night due to nightlife.  
        """)

    with tab3:
        st.subheader("Histogram: Distribution of trip distances (0-50 miles)")
        fig = px.histogram(
            filtered_pdf,
            x='trip_distance',
            nbins=50,
            title='Distribution of Trip Distances (0-50 miles)',
            labels={'trip_distance': 'Trip Distance (miles)'},
            color_discrete_sequence=['#3498DB'],
            range_x=[0, 50]
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, width='stretch')
        
        st.subheader("Insights from Trip Distance Distribution")
        st.markdown("""
        The majority of taxi trips are short, this is evident from the high concentration of trips under 10 miles. Majority
        of the trips where between 0-5 miles. This shows that the taxi is mainly used for local travel in NYC. The distribution
        is heavily right-skewed, with a long tail of longer trips, which likely represent airport rides or trips to outer boroughs.
         """)

    with tab4:
        st.subheader("Bar chart: Breakdown of payment types")
        payment_counts = filtered_pdf['payment_name'].value_counts(normalize=True).reset_index()
        payment_counts.columns = ['payment_name', 'trips_percentage']
        payment_counts['trips_percentage'] *= 100
        fig = px.bar(
            payment_counts,
            x='payment_name',
            y='trips_percentage',
            title='Payment Type Distribution (%)',
            labels={'payment_name': 'Payment Type', 'trips_percentage': 'Percentage of Trips'},
            color='payment_name',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig, width='stretch')
        
        st.subheader("Insights from Payment Type Breakdown")
        st.markdown("""
        Credit cards is the dominant payment method, this is shown by '83.5%' of the trips being paid by credit card.
        This reflects the shift to cashless payments in NYC. However, cash payments are still a significant '15.3%' of trips.
        This shows that some riders still prefer to pay with cash. The other payment types (No Charge, Dispute) are very rare.
        """)

    with tab5:
        st.subheader("Trip Volume Heatmap")

        # Pivot for the heatmap 
        heatmap_data = filtered_pdf.groupby([
            'pickup_weekday', 'pickup_hour'
        ]).size().unstack(fill_value=0)

        weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        if all(isinstance(i, int) and 0 <= i < len(weekday_names) for i in heatmap_data.index):
            heatmap_data.index = [weekday_names[i] for i in heatmap_data.index]

        fig = px.imshow(
            heatmap_data,
            labels=dict(x='Hour of Day', y='Day of Week', color='Trips'),
            x=heatmap_data.columns,
            y=list(heatmap_data.index),
            color_continuous_scale='YlOrRd',
            title='When Are Taxis Busiest?'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, width='stretch')
        
        st.subheader("Insights from Trip Volume Heatmap")
        st.markdown("""
        The heatmap shows that the taxi demand is the lowest during the early mornings throughout the week. 
        There is a noticeable increase in demand during the weekday rush hours i.e end of workday. There is also a
        high demand going into the late night and going into the weekend. This is likely due to people doing social activities and going out.
    """)
