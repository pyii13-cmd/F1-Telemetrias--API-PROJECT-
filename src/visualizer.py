"""
Visualization Module - Generate charts for tire degradation analysis.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import List, Optional


class DegradationVisualizer:
    """Create professional visualizations for F1 tire degradation analysis."""

    def __init__(self, output_dir: str = "./data/plots"):
        """
        Initialize the visualizer with output directory.

        Args:
            output_dir: Directory to save generated plots
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Set professional style
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (14, 8)
        plt.rcParams['font.size'] = 11
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['axes.labelsize'] = 12

        # F1 compound colors
        self.compound_colors = {
            'SOFT': '#FF0000',      # Red
            'MEDIUM': '#FFD700',    # Yellow/Gold
            'HARD': '#FFFFFF',      # White (with edge)
            'INTERMEDIATE': '#00FF00',  # Green
            'WET': '#0000FF'        # Blue
        }

        print(f"[OK] Visualizer initialized (output: {self.output_dir.absolute()})")

    def plot_degradation_by_team(
        self,
        summary_df: pd.DataFrame,
        compound: str,
        save_name: Optional[str] = None
    ):
        """
        Plot degradation rate comparison across teams for a specific compound.

        Args:
            summary_df: Summary DataFrame with degradation metrics
            compound: Compound to visualize
            save_name: Optional custom filename
        """
        data = summary_df[summary_df['Compound'] == compound].copy()
        data = data.sort_values('Degradation_s_per_lap')

        fig, ax = plt.subplots(figsize=(12, 8))

        # Bar plot with error bars
        x_pos = np.arange(len(data))
        bars = ax.barh(
            x_pos,
            data['Degradation_s_per_lap'],
            xerr=data['Degradation_std'],
            color=self.compound_colors.get(compound, '#888888'),
            edgecolor='black',
            linewidth=1.5,
            alpha=0.8
        )

        ax.set_yticks(x_pos)
        ax.set_yticklabels(data['Team'])
        ax.set_xlabel('Degradation (seconds per lap)', fontweight='bold')
        ax.set_title(
            f'Tire Degradation by Team - {compound} Compound',
            fontweight='bold',
            fontsize=16
        )
        ax.grid(axis='x', alpha=0.3)
        ax.axvline(0, color='black', linewidth=0.8)

        # Add value labels
        for i, (idx, row) in enumerate(data.iterrows()):
            value = row['Degradation_s_per_lap']
            ax.text(
                value + 0.001, i, f'{value:+.4f}s',
                va='center', fontsize=9, fontweight='bold'
            )

        plt.tight_layout()

        filename = save_name or f'degradation_by_team_{compound.lower()}.png'
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  [OK] Saved: {filepath.name}")

    def plot_stint_evolution(
        self,
        stint_data: pd.DataFrame,
        team: str,
        compound: str,
        driver: str,
        stint: int,
        model_result: dict,
        save_name: Optional[str] = None
    ):
        """
        Plot lap time evolution for a single stint with fitted model.

        Args:
            stint_data: DataFrame with TyreLife and LapTimeCorrected
            team: Team name
            compound: Compound name
            driver: Driver code
            stint: Stint number
            model_result: Result dictionary from TireDegradationModel
            save_name: Optional custom filename
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        tyre_life = stint_data['TyreLife'].values
        lap_times = stint_data['LapTimeCorrected'].values

        # Scatter plot of actual laps
        ax.scatter(
            tyre_life, lap_times,
            s=100, alpha=0.7,
            color=self.compound_colors.get(compound, '#888888'),
            edgecolors='black', linewidth=1.5,
            label='Actual lap times', zorder=3
        )

        # Plot fitted model
        x_smooth = np.linspace(tyre_life.min(), tyre_life.max(), 100)

        if model_result['best_model'] == 'linear':
            linear_model = model_result['linear']['model']
            y_smooth = linear_model.predict(x_smooth.reshape(-1, 1))
            label = f"Linear fit (R² = {model_result['linear']['r2_score']:.3f})"
        else:
            poly_model = model_result['polynomial']['model']
            poly_features = model_result['polynomial']['poly_features']
            X_smooth = poly_features.transform(x_smooth.reshape(-1, 1))
            y_smooth = poly_model.predict(X_smooth)
            label = f"Polynomial fit (R² = {model_result['polynomial']['r2_score']:.3f})"

        ax.plot(x_smooth, y_smooth, 'r-', linewidth=2.5, label=label, zorder=2)

        # Labels and styling
        ax.set_xlabel('Tire Age (laps)', fontweight='bold')
        ax.set_ylabel('Lap Time (seconds, fuel-corrected)', fontweight='bold')
        ax.set_title(
            f'{team} - {driver} - Stint {stint} ({compound})\n'
            f'Degradation: {model_result["linear"]["degradation_per_lap"]:+.4f} s/lap',
            fontweight='bold', fontsize=14
        )
        ax.legend(loc='best', fontsize=10)
        ax.grid(alpha=0.3)

        plt.tight_layout()

        filename = save_name or f'stint_{team}_{driver}_{compound}_s{stint}.png'
        filename = filename.replace(' ', '_')
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  [OK] Saved: {filepath.name}")

    def plot_compound_comparison(
        self,
        summary_df: pd.DataFrame,
        teams: Optional[List[str]] = None,
        save_name: Optional[str] = None
    ):
        """
        Plot compound degradation comparison across teams.

        Args:
            summary_df: Summary DataFrame with all compounds
            teams: List of teams to include (None = all)
            save_name: Optional custom filename
        """
        if teams:
            data = summary_df[summary_df['Team'].isin(teams)].copy()
        else:
            data = summary_df.copy()

        compounds = sorted(data['Compound'].unique())
        teams_list = sorted(data['Team'].unique())

        fig, ax = plt.subplots(figsize=(14, 8))

        x = np.arange(len(teams_list))
        width = 0.8 / len(compounds)

        for i, compound in enumerate(compounds):
            compound_data = data[data['Compound'] == compound]
            compound_data = compound_data.set_index('Team').reindex(teams_list)

            offset = width * (i - len(compounds) / 2 + 0.5)
            bars = ax.bar(
                x + offset,
                compound_data['Degradation_s_per_lap'],
                width,
                label=compound,
                color=self.compound_colors.get(compound, '#888888'),
                edgecolor='black',
                linewidth=1.2,
                alpha=0.85
            )

        ax.set_xlabel('Team', fontweight='bold')
        ax.set_ylabel('Degradation (seconds per lap)', fontweight='bold')
        ax.set_title('Tire Degradation by Compound and Team', fontweight='bold', fontsize=16)
        ax.set_xticks(x)
        ax.set_xticklabels(teams_list, rotation=45, ha='right')
        ax.legend(title='Compound', fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(0, color='black', linewidth=0.8)

        plt.tight_layout()

        filename = save_name or 'compound_comparison_all_teams.png'
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  [OK] Saved: {filepath.name}")

    def plot_base_pace_vs_degradation(
        self,
        summary_df: pd.DataFrame,
        compound: str,
        save_name: Optional[str] = None
    ):
        """
        Scatter plot showing relationship between base pace and degradation.

        Args:
            summary_df: Summary DataFrame
            compound: Compound to analyze
            save_name: Optional custom filename
        """
        data = summary_df[summary_df['Compound'] == compound].copy()

        fig, ax = plt.subplots(figsize=(12, 8))

        scatter = ax.scatter(
            data['BasePace_s'],
            data['Degradation_s_per_lap'],
            s=200,
            c=self.compound_colors.get(compound, '#888888'),
            edgecolors='black',
            linewidth=2,
            alpha=0.7
        )

        # Annotate team names
        for idx, row in data.iterrows():
            ax.annotate(
                row['Team'],
                (row['BasePace_s'], row['Degradation_s_per_lap']),
                fontsize=9,
                fontweight='bold',
                ha='center',
                va='bottom',
                xytext=(0, 5),
                textcoords='offset points'
            )

        ax.set_xlabel('Base Pace (seconds, at TyreLife=0)', fontweight='bold')
        ax.set_ylabel('Degradation (seconds per lap)', fontweight='bold')
        ax.set_title(
            f'Base Pace vs Degradation - {compound} Compound',
            fontweight='bold',
            fontsize=16
        )
        ax.grid(alpha=0.3)
        ax.axhline(0, color='black', linewidth=0.8, linestyle='--', alpha=0.5)

        plt.tight_layout()

        filename = save_name or f'pace_vs_degradation_{compound.lower()}.png'
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"  [OK] Saved: {filepath.name}")

    def generate_all_plots(self, summary_df: pd.DataFrame, model_results: list):
        """
        Generate complete visualization suite.

        Args:
            summary_df: Summary DataFrame from degradation analysis
            model_results: List of detailed results from TireDegradationModel
        """
        print("\n" + "="*60)
        print("[ANALYSIS] GENERATING VISUALIZATIONS")
        print("="*60 + "\n")

        compounds = sorted(summary_df['Compound'].unique())

        # 1. Degradation by team for each compound
        print("Creating degradation comparison plots...")
        for compound in compounds:
            self.plot_degradation_by_team(summary_df, compound)

        # 2. Compound comparison
        print("\nCreating compound comparison plot...")
        self.plot_compound_comparison(summary_df)

        # 3. Base pace vs degradation
        print("\nCreating pace vs degradation plots...")
        for compound in compounds:
            self.plot_base_pace_vs_degradation(summary_df, compound)

        # 4. Sample stint evolutions (2 per compound)
        print("\nCreating sample stint evolution plots...")
        for result in model_results[:6]:  # Limit to avoid too many plots
            if result['stint_details']:
                stint = result['stint_details'][0]
                self.plot_stint_evolution(
                    result['raw_data'][
                        (result['raw_data']['Driver'] == stint['driver']) &
                        (result['raw_data']['Stint'] == stint['stint'])
                    ],
                    result['team'],
                    result['compound'],
                    stint['driver'],
                    stint['stint'],
                    stint
                )

        print(f"\n[OK] All plots saved to: {self.output_dir.absolute()}")
        print("="*60 + "\n")
