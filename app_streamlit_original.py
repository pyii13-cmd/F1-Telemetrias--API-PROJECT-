"""
F1 Tire Degradation Analysis - Interactive Streamlit Application
Advanced telemetry exploration with stint analysis, fuel correction and degradation modeling.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_loader import F1DataLoader
from preprocessor import F1DataPreprocessor
from degradation_model import TireDegradationModel

# Page config
st.set_page_config(
    page_title="F1 Tire Degradation Analysis",
    page_icon="[F1]",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        color: #E10600;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6B7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_race_data(year: int, gp: str):
    """Load and cache race data."""
    loader = F1DataLoader(cache_dir="./data/cache")
    return loader.get_race_data(year, gp)


@st.cache_data
def preprocess_data(_raw_data, fuel_correction: float):
    """Preprocess and cache processed data. (Cacha: _raw_data is not hashed per Streamlit)"""
    preprocessor = F1DataPreprocessor(fuel_correction=fuel_correction)
    processed_data, metadata = preprocessor.process(_raw_data)
    return processed_data, metadata


@st.cache_data
def run_degradation_analysis(_processed_data, _summary_df=None):
    """Run and cache degradation analysis."""
    # Ensure we have a DataFrame, not raw FastF1 object
    if hasattr(_processed_data, 'columns') and isinstance(_processed_data, pd.DataFrame):
        df = _processed_data
    else:
        # If passed wrong type, return empty summary (prevents crash)
        return pd.DataFrame(), []
    model = TireDegradationModel()
    summary_df = model.analyze_all_teams(df)
    return summary_df, model.results


def calculate_pace_ranking(df: pd.DataFrame, compound: str):
    """Calculate net pace ranking corrected for fuel and compound."""
    compound_data = df[df['Compound'] == compound].copy()

    # Group by team and calculate average corrected lap time
    pace_ranking = compound_data.groupby('Team').agg({
        'LapTimeCorrected': ['mean', 'std', 'count']
    }).reset_index()

    pace_ranking.columns = ['Team', 'AvgPace', 'StdPace', 'Laps']
    pace_ranking = pace_ranking.sort_values('AvgPace')
    pace_ranking['Rank'] = range(1, len(pace_ranking) + 1)
    pace_ranking['DeltaToLeader'] = pace_ranking['AvgPace'] - pace_ranking['AvgPace'].iloc[0]

    return pace_ranking


def calculate_fuel_sensitivity(df: pd.DataFrame, team: str):
    """Calculate degradation difference between high fuel (early) and low fuel (late) stints."""
    team_data = df[df['Team'] == team].copy()

    if len(team_data) < 20:
        return None

    # Split into high fuel (first 30%) and low fuel (last 30%) laps
    sorted_data = team_data.sort_values('LapNumber')
    n_laps = len(sorted_data)

    high_fuel = sorted_data.iloc[:int(n_laps * 0.3)]
    low_fuel = sorted_data.iloc[int(n_laps * 0.7):]

    if len(high_fuel) < 5 or len(low_fuel) < 5:
        return None

    # Calculate degradation slopes
    from scipy import stats

    high_slope, _, _, _, _ = stats.linregress(
        high_fuel['TyreLife'], high_fuel['LapTimeCorrected']
    )

    low_slope, _, _, _, _ = stats.linregress(
        low_fuel['TyreLife'], low_fuel['LapTimeCorrected']
    )

    return {
        'high_fuel_degradation': high_slope,
        'low_fuel_degradation': low_slope,
        'sensitivity': high_slope - low_slope
    }


def main():
    # Header
    st.markdown('<div class="main-header">[F1] F1 Tire Degradation Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Advanced Telemetry Explorer • Race Pace & Strategy Analysis</div>', unsafe_allow_html=True)

    # Sidebar configuration
    st.sidebar.title("[CFG] Configuration")

    # Race selection
    st.sidebar.subheader("Race Selection")
    year = st.sidebar.selectbox("Season", [2024, 2023], index=0)
    gp = st.sidebar.selectbox(
        "Grand Prix",
        ["Monaco", "Bahrain", "Saudi Arabia", "Australia", "Miami", "Imola", "Spain", "Canada"]
    )

    # Fuel correction
    st.sidebar.subheader("Analysis Parameters")
    fuel_correction = st.sidebar.slider(
        "Fuel Correction (s/lap)",
        min_value=0.030,
        max_value=0.060,
        value=0.040,
        step=0.005,
        help="Seconds gained per lap due to fuel burn (0.035-0.05s typical)"
    )

    # Load data button
    if st.sidebar.button("[RELOAD] Load Race Data", type="primary"):
        st.session_state['data_loaded'] = False

    # Load data
    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = False

    try:
        with st.spinner(f"Loading {year} {gp} Grand Prix data..."):
            raw_data = load_race_data(year, gp)
            processed_data, metadata = preprocess_data(raw_data, fuel_correction)
            summary_df, model_results = run_degradation_analysis(processed_data, None)
            st.session_state['data_loaded'] = True
            st.session_state['raw_data'] = raw_data
            st.session_state['processed_data'] = processed_data
            st.session_state['metadata'] = metadata
            st.session_state['summary_df'] = summary_df
            st.session_state['model_results'] = model_results
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Try selecting a different Grand Prix or check your internet connection.")
        return

    if not st.session_state['data_loaded']:
        st.info("[CLICK] Configure race parameters in the sidebar and load data to begin analysis.")
        return

    # Get data from session
    processed_data = st.session_state['processed_data']
    metadata = st.session_state['metadata']
    summary_df = st.session_state['summary_df']
    model_results = st.session_state['model_results']

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("[DATA] Total Laps", f"{metadata['total_laps_processed']:,}")

    with col2:
        st.metric("[F1] Teams", metadata['teams'])

    with col3:
        st.metric("[COMP] Compounds", len(metadata['compounds']))

    with col4:
        best_team = summary_df.sort_values('Degradation_s_per_lap').iloc[0]['Team']
        st.metric("[BEST] Best Tire Mgmt", best_team.split()[0])

    st.divider()

    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "[PLOT] Stint Explorer",
        "[F1] Pace Ranking",
        "[DATA] Degradation Analysis",
        "[FUEL] Fuel Sensitivity",
        "[DOC] Methodology"
    ])

    # TAB 1: Stint Explorer
    with tab1:
        st.header("Stint-by-Stint Race Pace Explorer")

        col1, col2 = st.columns([2, 1])

        with col1:
            teams = sorted(processed_data['Team'].unique())
            selected_teams = st.multiselect(
                "Select Team(s) to Compare",
                teams,
                default=[teams[0]] if teams else [],
                max_selections=2
            )

        with col2:
            compounds = sorted(processed_data['Compound'].unique())
            selected_compound = st.selectbox("Filter by Compound", ["All"] + compounds)

        if selected_teams:
            # Filter data
            team_data = processed_data[processed_data['Team'].isin(selected_teams)].copy()

            if selected_compound != "All":
                team_data = team_data[team_data['Compound'] == selected_compound]

            # Stint selector
            available_stints = sorted(team_data['Stint'].unique())
            selected_stint = st.selectbox(
                "Filter by Stint",
                ["All Stints"] + [f"Stint {int(s)}" for s in available_stints]
            )

            if selected_stint != "All Stints":
                stint_num = int(selected_stint.split()[1])
                team_data = team_data[team_data['Stint'] == stint_num]

            # Plot evolution
            fig = go.Figure()

            colors = px.colors.qualitative.Set1

            for idx, team in enumerate(selected_teams):
                team_subset = team_data[team_data['Team'] == team]

                for driver in team_subset['Driver'].unique():
                    driver_data = team_subset[team_subset['Driver'] == driver]

                    fig.add_trace(go.Scatter(
                        x=driver_data['LapNumber'],
                        y=driver_data['LapTimeCorrected'],
                        mode='lines+markers',
                        name=f"{team} - {driver}",
                        line=dict(color=colors[idx % len(colors)], width=2),
                        marker=dict(size=6),
                        hovertemplate=(
                            f"<b>{team} - {driver}</b><br>" +
                            "Lap: %{x}<br>" +
                            "Time: %{y:.3f}s<br>" +
                            "<extra></extra>"
                        )
                    ))

            fig.update_layout(
                title=f"Lap Time Evolution - {selected_stint if selected_stint != 'All Stints' else 'All Stints'}",
                xaxis_title="Lap Number",
                yaxis_title="Lap Time (seconds, fuel-corrected)",
                height=500,
                hovermode='x unified',
                showlegend=True
            )

            st.plotly_chart(fig, use_container_width=True)

            # Stats table
            st.subheader("Stint Statistics")

            stint_stats = team_data.groupby(['Team', 'Driver', 'Stint', 'Compound']).agg({
                'LapTimeCorrected': ['mean', 'std', 'min', 'max'],
                'TyreLife': ['min', 'max'],
                'LapNumber': 'count'
            }).reset_index()

            stint_stats.columns = ['Team', 'Driver', 'Stint', 'Compound', 'Avg Time', 'Std Dev', 'Best', 'Worst', 'Min Tyre Life', 'Max Tyre Life', 'Laps']

            st.dataframe(
                stint_stats.style.format({
                    'Avg Time': '{:.3f}s',
                    'Std Dev': '{:.3f}s',
                    'Best': '{:.3f}s',
                    'Worst': '{:.3f}s'
                }),
                use_container_width=True
            )

    # TAB 2: Pace Ranking
    with tab2:
        st.header("Net Pace Ranking (Fuel & Compound Corrected)")

        col1, col2 = st.columns(2)

        with col1:
            ranking_compound = st.selectbox(
                "Select Compound for Ranking",
                sorted(processed_data['Compound'].unique()),
                key="ranking_compound"
            )

        pace_ranking = calculate_pace_ranking(processed_data, ranking_compound)

        # Delta to leader chart
        st.subheader("[DATA] Delta to Leader")

        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=pace_ranking['Team'],
            y=pace_ranking['DeltaToLeader'],
            marker_color=['#FFD700' if i == 0 else '#C0C0C0' if i == 1 else '#CD7F32' if i == 2 else '#E10600' for i in range(len(pace_ranking))],
            text=[f"+{d:.3f}s" if d > 0 else f"{d:.3f}s" for d in pace_ranking['DeltaToLeader']],
            textposition='outside',
            hovertemplate=(
                "<b>%{x}</b><br>" +
                "Delta: %{y:.3f}s<br>" +
                "<extra></extra>"
            )
        ))

        fig.update_layout(
            title=f"Time Delta to Leader - {ranking_compound} Compound",
            xaxis_title="Team",
            yaxis_title="Delta (seconds)",
            height=500,
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

        # Pace metrics table
        st.subheader("[TABLE] Detailed Pace Metrics")

        pace_display = pace_ranking.copy()
        pace_display['Rank'] = ['[1] 1' if r == 1 else '[2] 2' if r == 2 else '[3] 3' if r == 3 else str(r) for r in pace_display['Rank']]

        st.dataframe(
            pace_display[['Rank', 'Team', 'AvgPace', 'StdPace', 'DeltaToLeader', 'Laps']].style.format({
                'AvgPace': '{:.3f}s',
                'StdPace': '{:.3f}s',
                'DeltaToLeader': '+{:.3f}s'
            }),
            use_container_width=True,
            hide_index=True
        )

    # TAB 3: Degradation Analysis
    with tab3:
        st.header("Tire Degradation Analysis by Compound")

        deg_compound = st.selectbox(
            "Select Compound",
            sorted(summary_df['Compound'].unique()),
            key="deg_compound"
        )

        compound_data = summary_df[summary_df['Compound'] == deg_compound].sort_values('Degradation_s_per_lap')

        col1, col2 = st.columns(2)

        with col1:
            # Degradation bar chart
            fig = go.Figure()

            colors = ['#10B981' if d < 0 else '#EF4444' for d in compound_data['Degradation_s_per_lap']]

            fig.add_trace(go.Bar(
                x=compound_data['Team'],
                y=compound_data['Degradation_s_per_lap'],
                marker_color=colors,
                text=[f"{d:+.4f}" for d in compound_data['Degradation_s_per_lap']],
                textposition='outside',
                hovertemplate=(
                    "<b>%{x}</b><br>" +
                    "Degradation: %{y:.4f}s/lap<br>" +
                    "<extra></extra>"
                )
            ))

            fig.update_layout(
                title=f"Degradation Rate - {deg_compound}",
                xaxis_title="Team",
                yaxis_title="Degradation (s/lap)",
                height=400,
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Base pace vs degradation scatter
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=compound_data['BasePace_s'],
                y=compound_data['Degradation_s_per_lap'],
                mode='markers+text',
                marker=dict(size=15, color='#E10600', line=dict(width=2, color='white')),
                text=compound_data['Team'].str.split().str[0],
                textposition='top center',
                hovertemplate=(
                    "<b>%{text}</b><br>" +
                    "Base Pace: %{x:.3f}s<br>" +
                    "Degradation: %{y:.4f}s/lap<br>" +
                    "<extra></extra>"
                )
            ))

            fig.update_layout(
                title="Base Pace vs Degradation",
                xaxis_title="Base Pace (seconds)",
                yaxis_title="Degradation (s/lap)",
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

        # Degradation table
        st.subheader("[TABLE] Degradation Metrics")

        st.dataframe(
            compound_data[['Team', 'BasePace_s', 'Degradation_s_per_lap', 'Stints', 'TotalLaps']].style.format({
                'BasePace_s': '{:.3f}s',
                'Degradation_s_per_lap': '{:+.4f}s/lap'
            }).background_gradient(subset=['Degradation_s_per_lap'], cmap='RdYlGn_r'),
            use_container_width=True,
            hide_index=True
        )

    # TAB 4: Fuel Sensitivity
    with tab4:
        st.header("[FUEL] Fuel Load Sensitivity Analysis")

        st.info("""
        **Analysis Goal**: Compare tire degradation rates between high fuel (early race, heavy car)
        and low fuel (late race, light car) conditions to identify teams with fuel-sensitive performance.
        """)

        teams = sorted(processed_data['Team'].unique())
        sensitivity_data = []

        for team in teams:
            result = calculate_fuel_sensitivity(processed_data, team)
            if result:
                sensitivity_data.append({
                    'Team': team,
                    'High Fuel Deg.': result['high_fuel_degradation'],
                    'Low Fuel Deg.': result['low_fuel_degradation'],
                    'Sensitivity': result['sensitivity']
                })

        if sensitivity_data:
            sensitivity_df = pd.DataFrame(sensitivity_data).sort_values('Sensitivity', ascending=False)

            # Sensitivity bar chart
            fig = go.Figure()

            fig.add_trace(go.Bar(
                x=sensitivity_df['Team'],
                y=sensitivity_df['Sensitivity'],
                marker_color=['#EF4444' if s > 0.001 else '#10B981' for s in sensitivity_df['Sensitivity']],
                text=[f"{s:+.4f}" for s in sensitivity_df['Sensitivity']],
                textposition='outside',
                hovertemplate=(
                    "<b>%{x}</b><br>" +
                    "Sensitivity: %{y:.4f}s/lap<br>" +
                    "<extra></extra>"
                )
            ))

            fig.update_layout(
                title="Fuel Load Sensitivity (High Fuel - Low Fuel Degradation)",
                xaxis_title="Team",
                yaxis_title="Sensitivity Δ (s/lap)",
                height=500,
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

            # Detailed comparison
            st.subheader("[DATA] High vs Low Fuel Degradation Comparison")

            fig = go.Figure()

            fig.add_trace(go.Bar(
                name='High Fuel (Heavy)',
                x=sensitivity_df['Team'],
                y=sensitivity_df['High Fuel Deg.'],
                marker_color='#FF6B6B'
            ))

            fig.add_trace(go.Bar(
                name='Low Fuel (Light)',
                x=sensitivity_df['Team'],
                y=sensitivity_df['Low Fuel Deg.'],
                marker_color='#4ECDC4'
            ))

            fig.update_layout(
                title="Degradation: High Fuel vs Low Fuel",
                xaxis_title="Team",
                yaxis_title="Degradation (s/lap)",
                height=400,
                barmode='group'
            )

            st.plotly_chart(fig, use_container_width=True)

            # Table
            st.dataframe(
                sensitivity_df.style.format({
                    'High Fuel Deg.': '{:+.4f}s/lap',
                    'Low Fuel Deg.': '{:+.4f}s/lap',
                    'Sensitivity': '{:+.4f}s/lap'
                }).background_gradient(subset=['Sensitivity'], cmap='RdYlGn_r'),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("Insufficient data for fuel sensitivity analysis.")

    # TAB 5: Methodology
    with tab5:
        st.header("[DOC] Analysis Methodology")

        with st.expander("🔍 **Data Filtering & Cleaning**", expanded=True):
            st.markdown(f"""
            ### Lap Exclusion Criteria

            To isolate pure race pace, the following laps are excluded:

            1. **In-laps**: Laps ending in pit entry
            2. **Out-laps**: Laps starting from pit exit
            3. **Safety Car laps**: TrackStatus ∈ {{SC, VSC, Yellow}}
            4. **Outliers**: Laps > 2σ from median lap time

            **Results for {gp}:**
            - Initial laps: {metadata['total_laps_raw']:,}
            - Valid laps: {metadata['total_laps_processed']:,}
            - Removal rate: {metadata['removal_rate']*100:.1f}%
            """)

        with st.expander("[FUEL] **Fuel Correction Model**"):
            st.markdown(f"""
            ### Fuel Load Correction

            As the car burns fuel, it becomes lighter and faster. To isolate tire degradation,
            we correct for this effect:

            **Formula:**
            ```
            LapTime_corrected = LapTime_raw + (LapNumber × fuel_correction)
            ```

            **Current correction rate:** `{fuel_correction:.3f}s per lap`

            This means for a 50-lap race:
            - Lap 1: +{fuel_correction:.3f}s correction
            - Lap 25: +{fuel_correction*25:.3f}s correction
            - Lap 50: +{fuel_correction*50:.3f}s correction

            **Rationale:** A lighter car (end of race) would naturally be ~1.5-2.5s faster than
            a full fuel load (start). This correction removes that advantage to reveal pure tire performance.
            """)

        with st.expander("📉 **Degradation Regression Model**"):
            st.markdown("""
            ### Linear Regression Model

            For each team-compound-stint combination:

            **Model:**
            ```
            LapTime_corrected = β₀ + β₁ × TyreLife + ε
            ```

            Where:
            - `β₀` = **Base pace** (lap time at TyreLife = 0)
            - `β₁` = **Degradation rate** (seconds lost per lap)
            - `TyreLife` = Age of tire (laps on current set)
            - `ε` = Residual error

            **Polynomial Model (Degree 2):**
            ```
            LapTime_corrected = β₀ + β₁ × TyreLife + β₂ × TyreLife² + ε
            ```

            Used to detect non-linear "cliff" effects when tires suddenly lose performance.

            **Model Selection:**
            - If R² improvement > 0.05: Use polynomial
            - Otherwise: Use linear (simpler, more interpretable)
            """)

        with st.expander("[F1] **Net Pace Ranking**"):
            st.markdown("""
            ### Pace Ranking Methodology

            **Step 1: Fuel Correction**
            Apply fuel correction to all lap times (as above).

            **Step 2: Compound Normalization** *(Future Enhancement)*
            Theoretical time deltas between compounds:
            - Soft → Medium: ~0.3-0.5s slower
            - Medium → Hard: ~0.3-0.5s slower

            **Step 3: Aggregation**
            Calculate mean corrected lap time per team-compound.

            **Step 4: Ranking**
            Sort teams by average corrected lap time.
            Delta to leader = Team_Time - Leader_Time
            """)

        with st.expander("[DATA] **Statistical Validation**"):
            st.markdown("""
            ### Quality Metrics

            **Minimum Data Requirements:**
            - Stint analysis: ≥ 5 laps per stint
            - Fuel sensitivity: ≥ 20 total laps
            - Degradation model: ≥ 8 laps for polynomial, ≥ 5 for linear

            **R² Threshold:**
            - Good fit: R² > 0.7
            - Acceptable: 0.5 < R² < 0.7
            - Poor fit: R² < 0.5 (flagged in analysis)

            **Outlier Detection:**
            - Z-score method: |z| > 2
            - IQR method: Q1 - 1.5×IQR or Q3 + 1.5×IQR
            """)


if __name__ == "__main__":
    main()
