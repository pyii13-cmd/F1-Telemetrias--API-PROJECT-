"""
F1 Tire Degradation Analysis - Main Pipeline
Analyze tire degradation across teams and compounds using F1 telemetry data.
"""
import sys
import io
from pathlib import Path

# Fix Windows Unicode output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from data_loader import F1DataLoader
from preprocessor import F1DataPreprocessor
from degradation_model import TireDegradationModel
from web_exporter import export_dashboard_data
from visualizer import DegradationVisualizer

import pandas as pd


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def generate_summary_report(summary_df: pd.DataFrame, metadata: dict):
    """Generate a text summary report of the analysis."""
    print_header("📋 ANALYSIS SUMMARY REPORT")

    print("\n📊 Dataset Overview:")
    print(f"  • Total laps analyzed: {metadata['total_laps_processed']:,}")
    print(f"  • Laps filtered out: {metadata['total_laps_raw'] - metadata['total_laps_processed']:,} "
          f"({metadata['removal_rate']*100:.1f}%)")
    print(f"  • Fuel correction applied: {metadata['fuel_correction']:.3f} s/lap")
    print(f"  • Teams: {len(metadata['teams'])}")
    print(f"  • Drivers: {len(metadata['drivers'])}")
    print(f"  • Stints analyzed: {metadata['stints']}")
    print(f"  • Compounds: {', '.join(metadata['compounds'])}")

    print("\n🏆 Best Tire Management by Compound:")
    for compound in sorted(summary_df['Compound'].unique()):
        compound_data = summary_df[summary_df['Compound'] == compound].copy()
        compound_data = compound_data.sort_values('Degradation_s_per_lap')

        print(f"\n  {compound}:")
        for i, (idx, row) in enumerate(compound_data.head(3).iterrows(), 1):
            print(f"    {i}. {row['Team']:20s} - {row['Degradation_s_per_lap']:+.4f} s/lap "
                  f"(base pace: {row['BasePace_s']:.3f}s, {row['Stints']} stints)")

    print("\n📈 Degradation Range by Compound:")
    for compound in sorted(summary_df['Compound'].unique()):
        compound_data = summary_df[summary_df['Compound'] == compound]
        deg_min = compound_data['Degradation_s_per_lap'].min()
        deg_max = compound_data['Degradation_s_per_lap'].max()
        deg_avg = compound_data['Degradation_s_per_lap'].mean()

        print(f"  {compound:7s}: {deg_min:+.4f}s to {deg_max:+.4f}s per lap "
              f"(avg: {deg_avg:+.4f}s, Δ: {deg_max-deg_min:.4f}s)")

    print("\n" + "=" * 70 + "\n")


def main():
    """Main execution pipeline."""

    print_header("🏎️  F1 TIRE DEGRADATION ANALYSIS PIPELINE")
    print("\nSenior Motorsport Data Engineer - Telemetry & Strategy Analysis")
    print("Analyzing tire compound degradation impact on lap times\n")

    # Configuration
    YEAR = 2024
    GP = "Monaco"  # You can change this to any recent GP
    TEAMS = None   # None = analyze all teams, or specify list like ['Red Bull Racing', 'Ferrari']

    print(f"📅 Target Race: {YEAR} {GP} Grand Prix")
    print(f"🎯 Teams: {'All teams' if TEAMS is None else ', '.join(TEAMS)}")

    try:
        # Step 1: Load Data
        print_header("STEP 1: DATA LOADING")
        loader = F1DataLoader(cache_dir="./data/cache")
        raw_data = loader.get_race_data(YEAR, GP, teams=TEAMS)

        if len(raw_data) == 0:
            print("\n❌ ERROR: No data loaded. Check GP name and year.")
            print("   Try: 'Bahrain', 'Saudi Arabia', 'Australia', 'Monaco', etc.")
            return 1

        # Step 2: Preprocess Data
        print_header("STEP 2: DATA PREPROCESSING")
        preprocessor = F1DataPreprocessor(fuel_correction=0.040)
        processed_data, metadata = preprocessor.process(raw_data)

        if len(processed_data) == 0:
            print("\n❌ ERROR: No valid laps after preprocessing.")
            return 1

        # Step 3: Degradation Modeling
        print_header("STEP 3: DEGRADATION MODELING")
        model = TireDegradationModel()
        summary_df = model.analyze_all_teams(processed_data)

        if len(summary_df) == 0:
            print("\n❌ ERROR: No degradation models could be fitted.")
            return 1

        # Save summary to CSV
        output_csv = Path("./data/degradation_summary.csv")
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        summary_df.to_csv(output_csv, index=False)
        export_dashboard_data(csv_path=output_csv, race=f"{YEAR} {GP} Grand Prix")
        print(f"\n✓ Summary saved to: {output_csv.absolute()}")

        # Step 4: Generate Visualizations
        print_header("STEP 4: VISUALIZATION GENERATION")
        visualizer = DegradationVisualizer(output_dir="./data/plots")
        visualizer.generate_all_plots(summary_df, model.results)

        # Step 5: Generate Report
        generate_summary_report(summary_df, metadata)

        print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
        print(f"\n📁 Outputs saved to:")
        print(f"   • CSV summary: ./data/degradation_summary.csv")
        print(f"   • Plots: ./data/plots/")
        print(f"   • Cache: ./data/cache/")

        return 0

    except Exception as e:
        print(f"\n❌ PIPELINE ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
