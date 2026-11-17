"""
Degradation Modeling Module - Calculate tire degradation metrics using regression.
"""
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import r2_score
from typing import Dict, Tuple, Optional
import logging

# DISABLE ALL LOGGING
logging.basicConfig(level=logging.CRITICAL, handlers=[logging.NullHandler()])

# Override print to catch any remaining Unicode
_original_print = print
def _safe_print(*args, **kwargs):
    try:
        _original_print(*args, **kwargs)
    except Exception:
        pass
print = _safe_print


class TireDegradationModel:
    """Model tire degradation per team and compound using regression."""

    def __init__(self):
        """Initialize the degradation model."""
        self.results = {}
        print("[OK] Tire Degradation Model initialized")

    def fit_linear_model(
        self,
        tyre_life: np.ndarray,
        lap_times: np.ndarray
    ) -> Dict:
        """
        Fit a linear regression model: LapTime = base_pace + degradation * TyreLife

        Args:
            tyre_life: Array of tire ages (laps)
            lap_times: Array of corrected lap times (seconds)

        Returns:
            Dictionary with model parameters and metrics
        """
        X = tyre_life.reshape(-1, 1)
        y = lap_times

        model = LinearRegression()
        model.fit(X, y)

        predictions = model.predict(X)
        r2 = r2_score(y, predictions)
        residuals = y - predictions

        return {
            'base_pace': model.intercept_,  # Lap time at TyreLife=0
            'degradation_per_lap': model.coef_[0],  # Seconds lost per lap
            'r2_score': r2,
            'predictions': predictions,
            'residuals': residuals,
            'model': model
        }

    def fit_polynomial_model(
        self,
        tyre_life: np.ndarray,
        lap_times: np.ndarray,
        degree: int = 2
    ) -> Dict:
        """
        Fit a polynomial regression to capture non-linear "cliff" effects.

        Args:
            tyre_life: Array of tire ages (laps)
            lap_times: Array of corrected lap times (seconds)
            degree: Polynomial degree (default: 2 for quadratic)

        Returns:
            Dictionary with model parameters and metrics
        """
        X = tyre_life.reshape(-1, 1)
        y = lap_times

        poly_features = PolynomialFeatures(degree=degree)
        X_poly = poly_features.fit_transform(X)

        model = LinearRegression()
        model.fit(X_poly, y)

        predictions = model.predict(X_poly)
        r2 = r2_score(y, predictions)

        # Find inflection point for degree=2
        inflection_point = None
        if degree == 2 and len(model.coef_) >= 3:
            # For ax^2 + bx + c, inflection at x = -b/(2a)
            a, b = model.coef_[2], model.coef_[1]
            if a != 0:
                inflection_point = -b / (2 * a)

        return {
            'base_pace': model.intercept_,
            'coefficients': model.coef_,
            'degree': degree,
            'r2_score': r2,
            'inflection_point': inflection_point,
            'predictions': predictions,
            'model': model,
            'poly_features': poly_features
        }

    def analyze_stint(
        self,
        stint_data: pd.DataFrame,
        use_polynomial: bool = True
    ) -> Dict:
        """
        Analyze a single stint (one driver, one compound, continuous tire usage).

        Args:
            stint_data: DataFrame with TyreLife and LapTimeCorrected columns
            use_polynomial: Whether to fit polynomial in addition to linear

        Returns:
            Dictionary with analysis results
        """
        if len(stint_data) < 5:
            return None  # Not enough data for meaningful regression

        tyre_life = stint_data['TyreLife'].values
        lap_times = stint_data['LapTimeCorrected'].values

        # Linear model (always fit)
        linear_result = self.fit_linear_model(tyre_life, lap_times)

        result = {
            'n_laps': len(stint_data),
            'tyre_life_range': (int(tyre_life.min()), int(tyre_life.max())),
            'linear': linear_result
        }

        # Polynomial model (optional, captures "cliff")
        if use_polynomial and len(stint_data) >= 8:
            poly_result = self.fit_polynomial_model(tyre_life, lap_times, degree=2)
            result['polynomial'] = poly_result

            # Use polynomial if it fits significantly better
            if poly_result['r2_score'] - linear_result['r2_score'] > 0.05:
                result['best_model'] = 'polynomial'
            else:
                result['best_model'] = 'linear'
        else:
            result['best_model'] = 'linear'

        return result

    def analyze_by_compound(
        self,
        df: pd.DataFrame,
        team: str,
        compound: str
    ) -> Optional[Dict]:
        """
        Analyze degradation for a specific team and compound across all stints.

        Args:
            df: Processed lap data
            team: Team name
            compound: Tire compound (SOFT, MEDIUM, HARD)

        Returns:
            Aggregated degradation metrics
        """
        # Filter data
        mask = (df['Team'] == team) & (df['Compound'] == compound)
        compound_data = df[mask].copy()

        if len(compound_data) < 10:
            return None  # Insufficient data

        # Group by stint and analyze each
        stints = compound_data.groupby(['Driver', 'Stint'])
        stint_results = []

        for (driver, stint), stint_df in stints:
            result = self.analyze_stint(stint_df)
            if result:
                result['driver'] = driver
                result['stint'] = stint
                stint_results.append(result)

        if not stint_results:
            return None

        # Aggregate metrics across stints
        degradations = [s['linear']['degradation_per_lap'] for s in stint_results]
        base_paces = [s['linear']['base_pace'] for s in stint_results]

        return {
            'team': team,
            'compound': compound,
            'n_stints': len(stint_results),
            'total_laps': sum(s['n_laps'] for s in stint_results),
            'avg_degradation': np.mean(degradations),
            'std_degradation': np.std(degradations),
            'avg_base_pace': np.mean(base_paces),
            'std_base_pace': np.std(base_paces),
            'stint_details': stint_results,
            'raw_data': compound_data
        }

    def analyze_all_teams(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run degradation analysis for all team-compound combinations.

        Args:
            df: Processed lap data

        Returns:
            DataFrame with degradation metrics per team and compound
        """
        print("\n" + "="*60)
        print("[ANALYSIS] DEGRADATION ANALYSIS")
        print("="*60)

        results = []
        teams = sorted(df['Team'].unique())
        compounds = sorted(df['Compound'].unique())

        for team in teams:
            print(f"\n[PREP] Analyzing {team}...")
            for compound in compounds:
                result = self.analyze_by_compound(df, team, compound)
                if result:
                    results.append(result)
                    print(f"  {compound:7s}: {result['avg_degradation']:+.4f} s/lap "
                          f"(base: {result['avg_base_pace']:.3f}s, "
                          f"stints: {result['n_stints']}, "
                          f"laps: {result['total_laps']})")

        # Store results
        self.results = results

        # Create summary DataFrame
        summary_df = pd.DataFrame([
            {
                'Team': r['team'],
                'Compound': r['compound'],
                'BasePace_s': r['avg_base_pace'],
                'Degradation_s_per_lap': r['avg_degradation'],
                'Degradation_std': r['std_degradation'],
                'Stints': r['n_stints'],
                'TotalLaps': r['total_laps']
            }
            for r in results
        ])

        print("\n[OK] Analysis complete!")
        print(f"  Analyzed {len(results)} team-compound combinations")
        print("="*60 + "\n")

        return summary_df

    def get_efficiency_ranking(self, summary_df: pd.DataFrame, compound: str) -> pd.DataFrame:
        """
        Rank teams by tire efficiency for a specific compound.

        Lower degradation = better tire management.

        Args:
            summary_df: Summary DataFrame from analyze_all_teams
            compound: Compound to rank

        Returns:
            Ranked DataFrame for that compound
        """
        compound_df = summary_df[summary_df['Compound'] == compound].copy()
        compound_df = compound_df.sort_values('Degradation_s_per_lap')
        compound_df['Rank'] = range(1, len(compound_df) + 1)
        return compound_df
